import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scrcpy import capture_window, crop_relative_box, ensure_scrcpy_window, wait_for_window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 scrcpy 窗口裁剪一个相对区域。")
    parser.add_argument("x", type=float, help="相对横坐标，范围 0.0 到 1.0")
    parser.add_argument("y", type=float, help="相对纵坐标，范围 0.0 到 1.0")
    parser.add_argument("width", type=float, help="相对宽度，范围 0.0 到 1.0")
    parser.add_argument("height", type=float, help="相对高度，范围 0.0 到 1.0")
    parser.add_argument("--title", default="OK Scrcpy Daily", help="scrcpy 窗口标题")
    parser.add_argument("--timeout", type=float, default=20, help="等待 scrcpy 窗口的秒数")
    parser.add_argument("--start", action="store_true", help="找不到窗口时启动 scrcpy")
    parser.add_argument(
        "--output",
        default=str(ROOT / "screenshots" / "region.png"),
        help="裁剪图片输出路径",
    )
    return parser.parse_args()


def validate_box(x: float, y: float, width: float, height: float) -> None:
    if min(x, y, width, height) < 0:
        raise ValueError("x、y、width、height 必须是非负数")
    if x + width > 1 or y + height > 1:
        raise ValueError("相对区域必须位于 0.0 到 1.0 范围内")


def main() -> int:
    args = parse_args()
    validate_box(args.x, args.y, args.width, args.height)

    hwnd = (
        ensure_scrcpy_window(args.title, timeout=args.timeout)
        if args.start
        else wait_for_window(args.title, timeout=args.timeout)
    )
    frame = capture_window(hwnd)
    crop = crop_relative_box(frame, (args.x, args.y, args.width, args.height))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), crop):
        raise RuntimeError(f"保存裁剪图片失败：{output}")
    print(f"已保存裁剪图片：{output}")
    print(f"裁剪图片尺寸：{crop.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
