from __future__ import annotations

import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2

from src.adb import force_stop_package, launch_package, lock_screen, wake_and_unlock_if_possible
from src.power import keep_system_awake, restore_sleep, wake_display
from src.run_state import append_action, mark_completed
from src.paths import app_root, resource_path
from src.scrcpy import capture_window, click_scrcpy_relative, close_window, ensure_any_scrcpy_window
from src.vision import best_template_match, load_template, wait_click_template


@dataclass(frozen=True)
class ClickStep:
    name: str
    x: float
    y: float
    template: str = ""
    alternate_templates: tuple[str, ...] = ()
    action: str = "click"


DEFAULT_STEPS = [
    ClickStep("打开打卡入口", 0.650, 0.150, template="work_notice.png"),
    ClickStep("点击打卡下班", 0.500, 0.600, template="offwork_button.png"),
    ClickStep("点击外勤打卡下班", 0.500, 0.600, template="field_offwork_button.png"),
    ClickStep(
        "确认下班打卡成功",
        0.500,
        0.940,
        template="offwork_success_text.png",
        alternate_templates=("offwork_success_text_v2.png",),
        action="verify",
    ),
]

CLOCK_STEPS = {
    "morning": {
        "name": "上班打卡序列",
        "completed": "上班打卡序列已完成",
        "steps": [
            ClickStep("打开上班打卡入口", 0.650, 0.150, template="morning_work_notice.png"),
            ClickStep(
                "点击打卡上班",
                0.500,
                0.600,
                template="morning_clock_button.png",
                alternate_templates=("morning_immediate_clock_button.png",),
            ),
            ClickStep("点击外勤打卡上班", 0.500, 0.600, template="morning_field_clock_button.png"),
            ClickStep("确认上班打卡成功", 0.500, 0.940, template="morning_success_text.png", action="verify"),
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

    def ensure_device_ready(context: str, reopen_app: bool = False) -> None:
        emit(f"{context}：检查设备状态")
        state = wake_and_unlock_if_possible()
        emit(f"{context}：手机屏幕状态：{state.description}")
        if state.locked:
            raise RuntimeError(f"{context}后手机仍处于锁屏状态，请先手动解锁后再执行")
        if reopen_app and open_dingtalk:
            emit(f"{context}：重新打开钉钉")
            launch_package(package, wait_seconds=launch_wait, fresh=fresh)

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
    keep_system_awake()
    wake_display()
    emit("已请求系统保持唤醒")
    ensure_device_ready("启动前")

    if open_dingtalk:
        emit("打开钉钉")
        launch_package(package, wait_seconds=launch_wait, fresh=fresh)

    hwnd, started_scrcpy = ensure_any_scrcpy_window(title, timeout=timeout)
    emit(f"scrcpy 窗口：句柄={hwnd}，本次启动={'是' if started_scrcpy else '否'}")
    template_dir = template_dir or resource_path("assets/templates")

    def paired_templates(index: int, step: ClickStep) -> list[tuple[str, ClickStep, Path]]:
        candidates = []
        step_index = index - 1
        for candidate_mode, candidate_sequence in CLOCK_STEPS.items():
            candidate_steps = candidate_sequence["steps"]
            if step_index >= len(candidate_steps):
                continue
            candidate_step = candidate_steps[step_index]
            if candidate_step.action != step.action:
                continue
            template_names = tuple(name for name in (candidate_step.template, *candidate_step.alternate_templates) if name)
            for template_name in template_names:
                candidate_path = template_dir / template_name
                if candidate_path.exists():
                    candidates.append((candidate_mode, candidate_step, candidate_path))
        return candidates

    def save_diagnostic_frame(frame, reason: str) -> Path | None:
        path = app_root() / "screenshots" / f"diagnostic_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{reason}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path if cv2.imwrite(str(path), frame) else None

    def frame_is_blank(frame) -> bool:
        return float(frame.std()) < 2.0 or float(frame.mean()) < 3.0

    def restart_scrcpy(reason: str) -> None:
        nonlocal hwnd, started_scrcpy
        emit(f"scrcpy 画面异常，重启 scrcpy：{reason}")
        append_action(sequence_name, "重试", f"scrcpy 画面异常，重启：{reason}")
        close_window(hwnd)
        time.sleep(1.5)
        ensure_device_ready("scrcpy 重启前", reopen_app=True)
        hwnd, restarted = ensure_any_scrcpy_window(title, timeout=timeout)
        started_scrcpy = started_scrcpy or restarted
        wake_display()
        emit(f"scrcpy 已恢复：句柄={hwnd}")

    def wait_best_template(
        candidates: list[tuple[str, ClickStep, Path]],
        timeout_seconds: float,
        threshold: float = template_threshold,
    ):
        loaded = [(candidate_mode, candidate_step, candidate_path, load_template(candidate_path)) for candidate_mode, candidate_step, candidate_path in candidates]
        deadline = time.monotonic() + timeout_seconds
        best_seen = None
        blank_frames = 0
        restarted_for_blank = False
        while time.monotonic() < deadline:
            frame = capture_window(hwnd)
            if frame_is_blank(frame):
                blank_frames += 1
                if blank_frames == 1:
                    saved = save_diagnostic_frame(frame, "blank")
                    emit(f"检测到疑似黑屏/空画面，均值={frame.mean():.1f}，方差={frame.std():.1f}，诊断截图={saved or '保存失败'}")
                if blank_frames >= 4 and not restarted_for_blank:
                    restarted_for_blank = True
                    restart_scrcpy("连续捕获到黑屏/空画面")
                    blank_frames = 0
                    continue
            else:
                blank_frames = 0
            matches = []
            for candidate_mode, candidate_step, candidate_path, template in loaded:
                match = best_template_match(frame, template)
                if match:
                    matches.append((match.score, candidate_mode, candidate_step, candidate_path, match))
                    if not best_seen or match.score > best_seen[0]:
                        best_seen = (match.score, candidate_mode, candidate_step, candidate_path, match)
            ready = [item for item in matches if item[0] >= threshold]
            if ready:
                _score, candidate_mode, candidate_step, candidate_path, match = max(ready, key=lambda item: item[0])
                return candidate_mode, candidate_step, candidate_path, match, best_seen
            time.sleep(0.5)
        best_text = "无"
        if best_seen:
            best_text = f"{best_seen[3]}={best_seen[0]:.3f}"
        try:
            final_frame = capture_window(hwnd)
            saved = save_diagnostic_frame(final_frame, "timeout")
        except Exception:
            saved = None
        candidate_text = "，".join(str(candidate_path) for _mode, _step, candidate_path in candidates)
        raise TimeoutError(f"等待模板出现超时：{candidate_text}，最佳相似度：{best_text}，诊断截图：{saved or '保存失败'}")

    def execute_step(index: int, step: ClickStep, timeout_seconds: float) -> tuple[str, dict]:
        template_path = template_dir / step.template if step.template else None
        candidates = paired_templates(index, step)
        if step.action == "verify":
            if not use_templates or not candidates:
                raise FileNotFoundError(f"{step.name}需要配置成功文字模板：{template_path}")
            verify_threshold = min(template_threshold, 0.80)
            emit(f"{index}. 等待确认：{step.name}（同步识别上班/下班成功模板，阈值={verify_threshold:.2f}）")
            matched_mode, matched_step, matched_path, match, _best_seen = wait_best_template(
                candidates,
                timeout_seconds,
                threshold=verify_threshold,
            )
            relative_x, relative_y = match.center_relative
            message = (
                f"{index}. {matched_step.name}：已识别成功文字，模式={matched_mode}，相似度={match.score:.3f} "
                f"缩放={match.scale:.2f} 相对坐标={relative_x:.3f},{relative_y:.3f}"
            )
            details = {
                "index": index,
                "mode": mode,
                "matched_mode": matched_mode,
                "action": step.action,
                "template": str(matched_path),
                "score": match.score,
                "scale": match.scale,
                "relative": [relative_x, relative_y],
            }
            return message, details

        if use_templates and candidates:
            emit(f"{index}. 等待识别：{step.name}（同步识别上班/下班模板）")
            matched_mode, matched_step, matched_path, match, _best_seen = wait_best_template(candidates, timeout_seconds)
            relative_x, relative_y = match.center_relative
            screen_x, screen_y = click_scrcpy_relative(hwnd, relative_x, relative_y)
            message = (
                f"{index}. {matched_step.name}：模式={matched_mode}，识别相似度={match.score:.3f} "
                f"缩放={match.scale:.2f} 相对坐标={relative_x:.3f},{relative_y:.3f} 屏幕坐标={screen_x},{screen_y}"
            )
            details = {
                "index": index,
                "mode": mode,
                "matched_mode": matched_mode,
                "action": step.action,
                "template": str(matched_path),
                "score": match.score,
                "scale": match.scale,
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
            f"缩放={match.scale:.2f} 相对坐标={relative_x:.3f},{relative_y:.3f} 屏幕坐标={screen_x},{screen_y}"
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
                "scale": match.scale,
                "relative": [relative_x, relative_y],
                "screen": [screen_x, screen_y],
            },
        )
        time.sleep(delay)
        return True

    sequence_succeeded = False
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
        sequence_succeeded = True
    finally:
        if started_scrcpy and not keep_scrcpy:
            close_window(hwnd)
            emit("已关闭本次脚本启动的 scrcpy 窗口")
        restore_sleep()
        emit("已恢复系统睡眠策略")
        finish_device()

    if sequence_succeeded:
        mark_completed(sequence["completed"], event=sequence_name)
