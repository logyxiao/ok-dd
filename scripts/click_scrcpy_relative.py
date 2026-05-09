import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scrcpy import click_scrcpy_relative, close_window, ensure_any_scrcpy_window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="点击 scrcpy 窗口中的相对坐标。")
    parser.add_argument("x", type=float, help="相对横坐标，范围 0.0 到 1.0")
    parser.add_argument("y", type=float, help="相对纵坐标，范围 0.0 到 1.0")
    parser.add_argument("--title", default="OK Scrcpy Daily", help="scrcpy 窗口标题")
    parser.add_argument("--timeout", type=float, default=20, help="等待 scrcpy 窗口的秒数")
    parser.add_argument("--keep-scrcpy", action="store_true", help="如果本脚本启动了 scrcpy，执行后保留窗口")
    return parser.parse_args()


def validate_relative(value: float, name: str) -> None:
    if value < 0 or value > 1:
        raise ValueError(f"{name} 必须在 0.0 到 1.0 之间，当前值：{value}")


def main() -> int:
    args = parse_args()
    validate_relative(args.x, "x")
    validate_relative(args.y, "y")

    hwnd, started_scrcpy = ensure_any_scrcpy_window(args.title, timeout=args.timeout)
    try:
        screen_x, screen_y = click_scrcpy_relative(hwnd, args.x, args.y)
        print(f"已点击相对坐标：{args.x:.4f},{args.y:.4f}")
        print(f"已点击屏幕坐标：{screen_x},{screen_y}")
        print(f"scrcpy 窗口：句柄={hwnd}，本次启动={'是' if started_scrcpy else '否'}")
    finally:
        if started_scrcpy and not args.keep_scrcpy:
            close_window(hwnd)
            print("已关闭本次脚本启动的 scrcpy 窗口")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
