from pathlib import Path

import win32com.client

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path.home() / "Desktop"
TARGET = ROOT / "启动钉钉打卡面板.cmd"
SHORTCUT = DESKTOP / "钉钉打卡面板.lnk"


def main() -> int:
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(SHORTCUT))
    shortcut.TargetPath = str(TARGET)
    shortcut.WorkingDirectory = str(ROOT)
    shortcut.Description = "打开钉钉下班打卡面板"
    shortcut.Save()
    print(f"已创建桌面快捷方式：{SHORTCUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
