import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scrcpy import close_window, ensure_any_scrcpy_window
from src.vision import wait_click_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="等待 scrcpy 画面出现模板后点击模板中心。")
    parser.add_argument("template", help="模板图片路径")
    parser.add_argument("--title", default="OK Scrcpy Daily", help="scrcpy 窗口标题")
    parser.add_argument("--threshold", type=float, default=0.86, help="相似度阈值")
    parser.add_argument("--timeout", type=float, default=25, help="等待模板出现的最长秒数")
    parser.add_argument("--interval", type=float, default=0.5, help="识别轮询间隔秒数")
    parser.add_argument("--keep-scrcpy", action="store_true", help="如果本脚本启动了 scrcpy，执行后保留窗口")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hwnd, started = ensure_any_scrcpy_window(args.title, timeout=20)
    try:
        match, clicked_at = wait_click_template(
            hwnd,
            Path(args.template),
            threshold=args.threshold,
            timeout=args.timeout,
            interval=args.interval,
        )
        relative_x, relative_y = match.center_relative
        print(f"已识别并点击模板：相似度={match.score:.3f}")
        print(f"点击相对坐标：{relative_x:.4f},{relative_y:.4f}")
        print(f"点击屏幕坐标：{clicked_at[0]},{clicked_at[1]}")
        return 0
    finally:
        if started and not args.keep_scrcpy:
            close_window(hwnd)
            print("已关闭本次脚本启动的 scrcpy 窗口")


if __name__ == "__main__":
    raise SystemExit(main())
