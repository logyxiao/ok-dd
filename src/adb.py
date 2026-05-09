from __future__ import annotations

import subprocess
import time


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
