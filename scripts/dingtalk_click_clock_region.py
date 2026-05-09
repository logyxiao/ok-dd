import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adb import back_until_focus_contains, launch_package
from src.scrcpy import capture_crop_and_click

DEFAULT_CLOCK_BOX = "0.05,0.50,0.92,0.11"


def parse_box(value: str) -> tuple[float, float, float, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("区域必须是 x,y,width,height")
    if any(part < 0 for part in parts):
        raise argparse.ArgumentTypeError("区域数值必须是非负数")
    if parts[0] + parts[2] > 1 or parts[1] + parts[3] > 1:
        raise argparse.ArgumentTypeError("区域必须位于 0..1 的相对画面范围内")
    return parts[0], parts[1], parts[2], parts[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用 ADB 打开钉钉，从 scrcpy 裁剪打卡区域并点击。"
    )
    parser.add_argument("--package", default="com.alibaba.android.rimet", help="钉钉包名")
    parser.add_argument("--title", default="OK Scrcpy Daily", help="scrcpy 窗口标题")
    parser.add_argument(
        "--clock-box",
        type=parse_box,
        default=parse_box(DEFAULT_CLOCK_BOX),
        help="相对裁剪/点击区域：x,y,width,height",
    )
    parser.add_argument("--launch-wait", type=float, default=3, help="打开钉钉后的等待秒数")
    parser.add_argument(
        "--home-activity",
        default="LaunchHomeActivity",
        help="截图前期望处于前台的 Activity 文本",
    )
    parser.add_argument("--timeout", type=float, default=20, help="等待 scrcpy 窗口的秒数")
    parser.add_argument(
        "--no-start-scrcpy",
        action="store_true",
        help="不启动 scrcpy，只连接已有窗口",
    )
    parser.add_argument(
        "--screenshot",
        default=str(ROOT / "screenshots" / "dingtalk_full.png"),
        help="完整截图输出路径",
    )
    parser.add_argument(
        "--crop",
        default=str(ROOT / "screenshots" / "dingtalk_clock_region.png"),
        help="打卡区域裁剪输出路径",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    launch_package(args.package, wait_seconds=args.launch_wait)
    focus = back_until_focus_contains(args.home_activity)
    screenshot, crop, clicked_at = capture_crop_and_click(
        title=args.title,
        crop_box=args.clock_box,
        screenshot_path=Path(args.screenshot),
        crop_path=Path(args.crop),
        start=not args.no_start_scrcpy,
        timeout=args.timeout,
    )
    print(f"当前前台页面：{focus}")
    print(f"已保存截图：{screenshot}")
    print(f"已保存裁剪图片：{crop}")
    print(f"已点击屏幕坐标：{clicked_at[0]},{clicked_at[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
