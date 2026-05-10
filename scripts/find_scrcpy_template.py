import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scrcpy import capture_window, ensure_any_scrcpy_window
from src.vision import find_template, load_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="在当前 scrcpy 画面中查找模板图片。")
    parser.add_argument("template", help="模板图片路径")
    parser.add_argument("--title", default="OK Scrcpy Daily", help="scrcpy 窗口标题")
    parser.add_argument("--threshold", type=float, default=0.86, help="相似度阈值")
    parser.add_argument("--timeout", type=float, default=20, help="等待 scrcpy 窗口的秒数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hwnd, _started = ensure_any_scrcpy_window(args.title, timeout=args.timeout)
    frame = capture_window(hwnd)
    template = load_template(Path(args.template))
    match = find_template(frame, template, threshold=args.threshold)
    if not match:
        print("未找到模板")
        return 1
    relative_x, relative_y = match.center_relative
    print(f"找到模板：相似度={match.score:.3f}")
    print(f"模板区域：x={match.x}, y={match.y}, width={match.width}, height={match.height}")
    print(f"中心相对坐标：{relative_x:.4f},{relative_y:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
