from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


def run_adb(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    command = ["adb", *args]
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        details = [f"ADB 命令执行失败：{subprocess.list2cmdline(command)}", f"退出码：{result.returncode}"]
        if stdout:
            details.append(f"标准输出：{stdout}")
        if stderr:
            details.append(f"错误输出：{stderr}")
        details.append("请确认手机已连接、已开启 USB 调试，并在手机上允许当前电脑调试。")
        raise RuntimeError("\n".join(details))
    return result


def force_stop_package(package_name: str) -> None:
    run_adb(["shell", "am", "force-stop", package_name], timeout=10)


def lock_screen() -> None:
    send_keyevent(223)


def launch_package(package_name: str, wait_seconds: float = 3, fresh: bool = False) -> None:
    if fresh:
        force_stop_package(package_name)
        time.sleep(0.5)
    run_adb(
        [
            "shell",
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
    )
    time.sleep(wait_seconds)


def send_keyevent(key_code: str | int) -> None:
    run_adb(["shell", "input", "keyevent", str(key_code)], timeout=10)


@dataclass(frozen=True)
class DeviceLockState:
    screen_on: bool | None
    locked: bool | None
    raw_power: str
    raw_window: str

    @property
    def description(self) -> str:
        screen_text = "亮屏" if self.screen_on else ("息屏" if self.screen_on is False else "亮屏状态未知")
        lock_text = "锁屏" if self.locked else ("未锁屏" if self.locked is False else "锁屏状态未知")
        return f"{screen_text}，{lock_text}"


def _parse_bool_line(text: str, names: tuple[str, ...]) -> bool | None:
    lowered = text.lower()
    for name in names:
        marker = name.lower()
        for line in lowered.splitlines():
            if marker in line:
                if "true" in line:
                    return True
                if "false" in line:
                    return False
    return None


def get_device_lock_state() -> DeviceLockState:
    power = run_adb(["shell", "dumpsys", "power"], timeout=10).stdout
    window = run_adb(["shell", "dumpsys", "window"], timeout=10).stdout
    screen_on = _parse_bool_line(power, ("mWakefulness=Awake", "Display Power: state=ON"))
    if screen_on is None:
        screen_on = "mwakefulness=awake" in power.lower() or "display power: state=on" in power.lower()
    locked = _parse_bool_line(window, ("mDreamingLockscreen", "isStatusBarKeyguard", "mShowingLockscreen"))
    if locked is None:
        lowered = window.lower()
        locked = "keyguard" in lowered and ("mshowing=true" in lowered or "isshowing=true" in lowered)
    return DeviceLockState(screen_on=screen_on, locked=locked, raw_power=power, raw_window=window)


def wake_and_unlock_if_possible(wait_seconds: float = 1.0) -> DeviceLockState:
    state = get_device_lock_state()
    if state.screen_on is not True:
        send_keyevent("WAKEUP")
        time.sleep(wait_seconds)
    state = get_device_lock_state()
    if state.locked:
        run_adb(["shell", "input", "swipe", "500", "1800", "500", "500", "300"], timeout=10)
        time.sleep(wait_seconds)
        state = get_device_lock_state()
    return state


def get_current_focus() -> str:
    result = run_adb(["shell", "dumpsys", "activity", "activities"], timeout=10)
    for line in result.stdout.splitlines():
        if "mResumedActivity" in line or "topResumedActivity" in line or "ResumedActivity" in line:
            return line.strip()
    return ""


def back_until_focus_contains(
    expected: str,
    max_back: int = 4,
    wait_seconds: float = 0.8,
) -> str:
    focus = get_current_focus()
    for _ in range(max_back):
        if expected in focus:
            return focus
        send_keyevent("BACK")
        time.sleep(wait_seconds)
        focus = get_current_focus()
    return focus
