import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date

from src.offwork_sequence import run_offwork_sequence
from src.run_state import append_action, mark_failed
from src.workday import describe_china_workday, is_china_workday, parse_date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行钉钉下班打卡点击序列。")
    parser.add_argument("--package", default="com.alibaba.android.rimet", help="钉钉包名")
    parser.add_argument("--title", default="OK Scrcpy Daily", help="scrcpy 窗口标题")
    parser.add_argument("--timeout", type=float, default=20, help="等待 scrcpy 窗口的秒数")
    parser.add_argument("--launch-wait", type=float, default=4, help="打开钉钉后的等待秒数")
    parser.add_argument("--delay", type=float, default=4, help="每次点击之间的等待秒数")
    parser.add_argument(
        "--no-fresh",
        action="store_true",
        help="打开钉钉前不强制停止钉钉",
    )
    parser.add_argument(
        "--workday-only",
        action="store_true",
        help="仅在中国工作日执行点击序列",
    )
    parser.add_argument(
        "--date",
        help="指定测试日期，格式 YYYY-MM-DD",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检查是否会执行，不打开钉钉也不点击",
    )
    parser.add_argument("--keep-scrcpy", action="store_true", help="执行后保留脚本新打开的 scrcpy")
    parser.add_argument(
        "--no-open-dingtalk",
        action="store_true",
        help="点击前不通过 ADB 打开钉钉",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_date = parse_date(args.date) if args.date else date.today()

    if args.workday_only:
        description = describe_china_workday(run_date)
        print(description)
        if not is_china_workday(run_date):
            print("跳过：今天不是中国工作日")
            append_action("下班打卡序列", "跳过", "今天不是中国工作日", {"date": run_date.isoformat()})
            return 0
    if args.dry_run:
        print("检查完成：今天会执行点击序列")
        append_action("下班打卡序列", "检查", "今天会执行点击序列", {"date": run_date.isoformat()})
        return 0

    try:
        run_offwork_sequence(
            package=args.package,
            title=args.title,
            timeout=args.timeout,
            launch_wait=args.launch_wait,
            delay=args.delay,
            fresh=not args.no_fresh,
            keep_scrcpy=args.keep_scrcpy,
            open_dingtalk=not args.no_open_dingtalk,
        )
    except Exception as exception:
        mark_failed(str(exception))
        raise

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
