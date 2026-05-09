import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adb import back_until_focus_contains, get_current_focus, launch_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用 ADB 打开钉钉。")
    parser.add_argument("--package", default="com.alibaba.android.rimet", help="钉钉包名")
    parser.add_argument("--wait", type=float, default=3, help="打开钉钉后的等待秒数")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="打开钉钉前先强制停止钉钉",
    )
    parser.add_argument(
        "--home",
        action="store_true",
        help="按返回键直到回到钉钉首页",
    )
    parser.add_argument(
        "--home-activity",
        default="LaunchHomeActivity",
        help="钉钉首页 Activity 文本",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    launch_package(args.package, wait_seconds=args.wait, fresh=args.fresh)
    focus = back_until_focus_contains(args.home_activity) if args.home else get_current_focus()
    print(f"当前前台页面：{focus}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
