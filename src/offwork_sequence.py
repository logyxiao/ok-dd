from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from src.adb import force_stop_package, launch_package, lock_screen
from src.run_state import append_action, mark_completed
from src.scrcpy import click_scrcpy_relative, close_window, ensure_any_scrcpy_window


@dataclass(frozen=True)
class ClickStep:
    name: str
    x: float
    y: float


DEFAULT_STEPS = [
    ClickStep("打开打卡入口", 0.650, 0.150),
    ClickStep("点击打卡下班", 0.500, 0.600),
    ClickStep("点击外勤打卡下班", 0.500, 0.600),
    ClickStep("点击外勤打卡", 0.500, 0.940),
]


def run_offwork_sequence(
    package: str = "com.alibaba.android.rimet",
    title: str = "OK Scrcpy Daily",
    timeout: float = 20,
    launch_wait: float = 4,
    delay: float = 4,
    fresh: bool = True,
    keep_scrcpy: bool = False,
    open_dingtalk: bool = True,
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
            append_action("下班打卡序列", "成功", "已关闭钉钉")
        except Exception as exception:
            message = f"关闭钉钉失败：{exception}"
            emit(message)
            append_action("下班打卡序列", "失败", message)
        try:
            emit("锁定手机屏幕")
            lock_screen()
            append_action("下班打卡序列", "成功", "已锁定手机屏幕")
        except Exception as exception:
            message = f"锁定手机屏幕失败：{exception}"
            emit(message)
            append_action("下班打卡序列", "失败", message)

    if open_dingtalk:
        emit("打开钉钉")
        launch_package(package, wait_seconds=launch_wait, fresh=fresh)

    hwnd, started_scrcpy = ensure_any_scrcpy_window(title, timeout=timeout)
    emit(f"scrcpy 窗口：句柄={hwnd}，本次启动={'是' if started_scrcpy else '否'}")

    try:
        append_action("下班打卡序列", "开始", "点击序列已开始")
        for index, step in enumerate(DEFAULT_STEPS, start=1):
            screen_x, screen_y = click_scrcpy_relative(hwnd, step.x, step.y)
            message = f"{index}. {step.name}：相对坐标={step.x:.3f},{step.y:.3f} 屏幕坐标={screen_x},{screen_y}"
            emit(message)
            append_action(
                "点击步骤",
                "成功",
                step.name,
                {"index": index, "relative": [step.x, step.y], "screen": [screen_x, screen_y]},
            )
            if index < len(DEFAULT_STEPS):
                time.sleep(delay)
    finally:
        if started_scrcpy and not keep_scrcpy:
            close_window(hwnd)
            emit("已关闭本次脚本启动的 scrcpy 窗口")

    finish_device()
    mark_completed("下班打卡序列已完成")
