#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "assets" / "templates"
REQUIRED_TEMPLATES = [
    "morning_work_notice.png",
    "morning_clock_button.png",
    "morning_immediate_clock_button.png",
    "morning_field_clock_button.png",
    "morning_success_text.png",
    "work_notice.png",
    "offwork_button.png",
    "field_offwork_button.png",
    "offwork_success_text.png",
    "offwork_success_text_v2.png",
]


def run(command: list[str], timeout: int = 10) -> tuple[int | None, str]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None, "command not found"
    except subprocess.TimeoutExpired:
        return None, "timeout"
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode, output.strip()


def print_check(ok: bool, title: str, detail: str = "") -> bool:
    mark = "OK" if ok else "FAIL"
    print(f"[{mark}] {title}")
    if detail:
        for line in detail.splitlines():
            print(f"      {line}")
    return ok


def import_check(python: Path, module: str) -> tuple[bool, str]:
    code = f"import {module}; print(getattr({module}, '__version__', 'installed'))"
    returncode, output = run([str(python), "-c", code], timeout=20)
    return returncode == 0, output


def adb_devices() -> tuple[bool, str]:
    adb = shutil.which("adb")
    if not adb:
        return False, "未找到 adb。可运行：brew install android-platform-tools"
    returncode, output = run([adb, "devices"], timeout=10)
    if returncode != 0:
        return False, output or "adb devices 执行失败"
    lines = [line.strip() for line in output.splitlines()[1:] if line.strip()]
    if not lines:
        return False, "未检测到设备。请连接手机，开启 USB 调试，并在手机上允许当前电脑。"
    unauthorized = [line for line in lines if "unauthorized" in line]
    if unauthorized:
        return False, "设备未授权：\n" + "\n".join(unauthorized)
    online = [line for line in lines if line.endswith("\tdevice")]
    if not online:
        return False, "未检测到 online 设备：\n" + "\n".join(lines)
    return True, "\n".join(online)


def main() -> int:
    print("OK-DingTalk macOS 环境诊断")
    print(f"项目目录：{ROOT}")
    print(f"系统：{platform.platform()}")
    print()

    failures = 0
    is_macos = sys.platform == "darwin"
    failures += not print_check(is_macos, "当前系统是 macOS", sys.platform)

    python = ROOT / ".venv" / "bin" / "python"
    failures += not print_check(python.exists(), "项目虚拟环境存在", str(python))

    if python.exists():
        returncode, output = run([str(python), "--version"])
        failures += not print_check(returncode == 0, "虚拟环境 Python 可运行", output)
        for module in ("cv2", "numpy", "psutil"):
            ok, detail = import_check(python, module)
            failures += not print_check(ok, f"Python 依赖可导入：{module}", detail)
    else:
        print("      修复建议：运行 ./scripts/bootstrap_macos.sh")

    for command, hint in (
        ("brew", "未找到 Homebrew。请先安装：https://brew.sh/"),
        ("adb", "未找到 adb。可运行：brew install android-platform-tools"),
        ("scrcpy", "未找到 scrcpy。可运行：brew install scrcpy"),
    ):
        path = shutil.which(command)
        failures += not print_check(bool(path), f"命令可用：{command}", path or hint)

    ok, detail = adb_devices()
    failures += not print_check(ok, "ADB 已连接并授权设备", detail)

    for directory in (ROOT / "logs", ROOT / "screenshots", TEMPLATE_DIR):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            writable = True
            detail = str(directory)
        except OSError as exc:
            writable = False
            detail = str(exc)
        failures += not print_check(writable, f"目录可写：{directory.name}", detail)

    missing_templates = [name for name in REQUIRED_TEMPLATES if not (TEMPLATE_DIR / name).exists()]
    failures += not print_check(
        not missing_templates,
        "模板文件齐全",
        "缺少：\n" + "\n".join(missing_templates) if missing_templates else str(TEMPLATE_DIR),
    )

    workday_file = ROOT / "data" / "china_workdays_2026.json"
    try:
        json.loads(workday_file.read_text(encoding="utf-8"))
        workday_ok = True
        workday_detail = str(workday_file)
    except Exception as exc:
        workday_ok = False
        workday_detail = str(exc)
    failures += not print_check(workday_ok, "工作日数据可读取", workday_detail)

    print()
    if failures:
        print(f"诊断完成：发现 {failures} 个问题。")
        return 1
    print("诊断完成：环境看起来可以运行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
