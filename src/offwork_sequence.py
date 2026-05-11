from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.adb import force_stop_package, launch_package, lock_screen
from src.run_state import append_action, mark_completed
from src.paths import resource_path
from src.scrcpy import click_scrcpy_relative, close_window, ensure_any_scrcpy_window
from src.vision import wait_click_template, wait_template


@dataclass(frozen=True)
class ClickStep:
    name: str
    x: float
    y: float
    template: str = ""
    action: str = "click"


DEFAULT_STEPS = [
    ClickStep("打开打卡入口", 0.650, 0.150, "work_notice.png"),
    ClickStep("点击打卡下班", 0.500, 0.600, "offwork_button.png"),
    ClickStep("点击外勤打卡下班", 0.500, 0.600, "field_offwork_button.png"),
    ClickStep("确认下班打卡成功", 0.500, 0.940, "offwork_success_text.png", "verify"),
]

CLOCK_STEPS = {
    "morning": {
        "name": "上班打卡序列",
        "completed": "上班打卡序列已完成",
        "steps": [
            ClickStep("打开上班打卡入口", 0.650, 0.150, "morning_work_notice.png"),
            ClickStep("点击打卡上班", 0.500, 0.600, "morning_clock_button.png"),
            ClickStep("点击外勤打卡上班", 0.500, 0.600, "morning_field_clock_button.png"),
            ClickStep("确认上班打卡成功", 0.500, 0.940, "morning_success_text.png", "verify"),
        ],
    },
    "evening": {
        "name": "下班打卡序列",
        "completed": "下班打卡序列已完成",
        "steps": DEFAULT_STEPS,
    },
}


def run_offwork_sequence(
    package: str = "com.alibaba.android.rimet",
    title: str = "OK Scrcpy Daily",
    timeout: float = 20,
    launch_wait: float = 4,
    delay: float = 4,
    fresh: bool = True,
    keep_scrcpy: bool = False,
    open_dingtalk: bool = True,
    use_templates: bool = True,
    template_dir: Path | None = None,
    template_threshold: float = 0.86,
    step_timeout: float = 25,
    step_retries: int = 2,
    retry_timeout: float = 5,
    mode: str = "evening",
    progress: Callable[[str], None] | None = None,
) -> None:
    def emit(message: str) -> None:
        print(message)
        if progress:
            progress(message)

    def finish_device() -> None:
        try:
            emit("关闭钉钉")
            force_stop_package(package)
            append_action(sequence_name, "成功", "已关闭钉钉")
        except Exception as exception:
            message = f"关闭钉钉失败：{exception}"
            emit(message)
            append_action(sequence_name, "失败", message)
        try:
            emit("锁定手机屏幕")
            lock_screen()
            append_action(sequence_name, "成功", "已锁定手机屏幕")
        except Exception as exception:
            message = f"锁定手机屏幕失败：{exception}"
            emit(message)
            append_action(sequence_name, "失败", message)

    if mode not in CLOCK_STEPS:
        raise ValueError(f"未知打卡模式：{mode}")
    sequence = CLOCK_STEPS[mode]
    sequence_name = sequence["name"]
    steps = sequence["steps"]

    if open_dingtalk:
        emit("打开钉钉")
        launch_package(package, wait_seconds=launch_wait, fresh=fresh)

    hwnd, started_scrcpy = ensure_any_scrcpy_window(title, timeout=timeout)
    emit(f"scrcpy 窗口：句柄={hwnd}，本次启动={'是' if started_scrcpy else '否'}")
    template_dir = template_dir or resource_path("assets/templates")

    def execute_step(index: int, step: ClickStep, timeout_seconds: float) -> tuple[str, dict]:
        template_path = template_dir / step.template if step.template else None
        if step.action == "verify":
            if not use_templates or not template_path or not template_path.exists():
                raise FileNotFoundError(f"{step.name}需要配置成功文字模板：{template_path}")
            emit(f"{index}. 等待确认：{step.name}（模板：{template_path.name}）")
            match = wait_template(hwnd, template_path, threshold=template_threshold, timeout=timeout_seconds)
            relative_x, relative_y = match.center_relative
            message = (
                f"{index}. {step.name}：已识别成功文字，相似度={match.score:.3f} "
                f"相对坐标={relative_x:.3f},{relative_y:.3f}"
            )
            details = {
                "index": index,
                "mode": mode,
                "action": step.action,
                "template": str(template_path),
                "score": match.score,
                "relative": [relative_x, relative_y],
            }
            return message, details

        if use_templates and template_path and template_path.exists():
            emit(f"{index}. 等待识别：{step.name}（模板：{template_path.name}）")
            match, (screen_x, screen_y) = wait_click_template(
                hwnd,
                template_path,
                threshold=template_threshold,
                timeout=timeout_seconds,
            )
            relative_x, relative_y = match.center_relative
            message = (
                f"{index}. {step.name}：识别相似度={match.score:.3f} "
                f"相对坐标={relative_x:.3f},{relative_y:.3f} 屏幕坐标={screen_x},{screen_y}"
            )
            details = {
                "index": index,
                "mode": mode,
                "action": step.action,
                "template": str(template_path),
                "score": match.score,
                "relative": [relative_x, relative_y],
                "screen": [screen_x, screen_y],
            }
            return message, details

        screen_x, screen_y = click_scrcpy_relative(hwnd, step.x, step.y)
        message = f"{index}. {step.name}：未配置模板，使用相对坐标={step.x:.3f},{step.y:.3f} 屏幕坐标={screen_x},{screen_y}"
        details = {"index": index, "mode": mode, "action": step.action, "relative": [step.x, step.y], "screen": [screen_x, screen_y]}
        return message, details

    def retry_previous_step(index: int, previous_step: ClickStep | None, attempt: int) -> bool:
        if not previous_step or previous_step.action != "click" or not previous_step.template:
            return False
        previous_template_path = template_dir / previous_step.template
        if not use_templates or not previous_template_path.exists():
            return False

        emit(
            f"{index}. 当前步骤等待超时，检查是否仍停留在上一步："
            f"{previous_step.name}（第 {attempt}/{step_retries} 次容错）"
        )
        try:
            match, (screen_x, screen_y) = wait_click_template(
                hwnd,
                previous_template_path,
                threshold=template_threshold,
                timeout=retry_timeout,
            )
        except Exception as exception:
            emit(f"{index}. 未确认仍在上一步页面：{exception}")
            return False

        relative_x, relative_y = match.center_relative
        message = (
            f"{index}. 容错重试：仍识别到上一步并已重新点击，"
            f"上一步={previous_step.name}，相似度={match.score:.3f}，"
            f"相对坐标={relative_x:.3f},{relative_y:.3f} 屏幕坐标={screen_x},{screen_y}"
        )
        emit(message)
        append_action(
            "点击步骤",
            "成功",
            "容错重试上一动作",
            {
                "index": index,
                "mode": mode,
                "retry_attempt": attempt,
                "previous_step": previous_step.name,
                "template": str(previous_template_path),
                "score": match.score,
                "relative": [relative_x, relative_y],
                "screen": [screen_x, screen_y],
            },
        )
        time.sleep(delay)
        return True

    try:
        append_action(sequence_name, "开始", "点击序列已开始", {"mode": mode})
        for index, step in enumerate(steps, start=1):
            previous_step = steps[index - 2] if index >= 2 else None
            for attempt in range(0, step_retries + 1):
                try:
                    message, details = execute_step(index, step, step_timeout)
                    break
                except TimeoutError:
                    if attempt >= step_retries or not retry_previous_step(index, previous_step, attempt + 1):
                        raise
            emit(message)
            append_action(
                "点击步骤",
                "成功",
                step.name,
                details,
            )
            if index < len(steps):
                time.sleep(delay)
    finally:
        if started_scrcpy and not keep_scrcpy:
            close_window(hwnd)
            emit("已关闭本次脚本启动的 scrcpy 窗口")

    finish_device()
    mark_completed(sequence["completed"])
