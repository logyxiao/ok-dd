import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scrcpy import capture_scrcpy_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="启动或连接 scrcpy 窗口并保存一张截图。"
    )
    parser.add_argument("--title", default="OK Scrcpy Daily", help="scrcpy 窗口标题")
    parser.add_argument(
        "--output",
        default=str(ROOT / "screenshots" / "scrcpy_capture.png"),
        help="截图输出路径",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="不启动 scrcpy，只连接已有窗口",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20,
        help="等待 scrcpy 窗口的秒数",
    )
    parser.add_argument(
        "--scrcpy-arg",
        action="append",
        default=[],
        help="传给 scrcpy 的额外参数；多个参数可重复传入",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = capture_scrcpy_once(
        title=args.title,
        output_path=Path(args.output),
        start=not args.no_start,
        timeout=args.timeout,
        extra_args=args.scrcpy_arg,
    )
    print(f"已保存截图：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
