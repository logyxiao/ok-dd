import argparse
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date, datetime

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
    parser.add_argument("--random-delay-minutes", type=float, default=0, help="执行前随机等待的最大分钟数")
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
    parser.add_argument("--no-template", action="store_true", help="不使用模板识别，直接使用坐标点击")
    parser.add_argument("--template-threshold", type=float, default=0.86, help="模板识别相似度阈值")
    parser.add_argument("--step-timeout", type=float, default=25, help="每一步等待模板出现的最长秒数")
    parser.add_argument("--step-retries", type=int, default=2, help="当前步骤超时后检查并重试上一步的次数")
    parser.add_argument("--retry-timeout", type=float, default=5, help="每次容错检查上一页模板的最长秒数")
    parser.add_argument(
        "--mode",
        choices=["auto", "morning", "evening"],
        default="auto",
        help="打卡模式：auto 按当前时间自动选择，morning 使用上班模板，evening 使用下班模板",
    )
    parser.add_argument(
        "--no-open-dingtalk",
        action="store_true",
        help="点击前不通过 ADB 打开钉钉",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_date = parse_date(args.date) if args.date else date.today()
    mode = args.mode
    if mode == "auto":
        mode = "morning" if datetime.now().hour < 12 else "evening"
    action_name = "上班打卡序列" if mode == "morning" else "下班打卡序列"

    if args.workday_only:
        description = describe_china_workday(run_date)
        print(description)
        if not is_china_workday(run_date):
            print("跳过：今天不是中国工作日")
            append_action(action_name, "跳过", "今天不是中国工作日", {"date": run_date.isoformat(), "mode": mode})
            return 0
    if args.dry_run:
        print("检查完成：今天会执行点击序列")
        append_action(action_name, "检查", "今天会执行点击序列", {"date": run_date.isoformat(), "mode": mode})
        return 0

    try:
        if args.random_delay_minutes > 0:
            max_seconds = int(args.random_delay_minutes * 60)
            wait_seconds = random.randint(0, max_seconds)
            print(f"随机等待：{wait_seconds} 秒后开始执行")
            append_action(
                "下班打卡序列",
                "等待",
                f"随机等待 {wait_seconds} 秒后开始执行",
                {"seconds": wait_seconds, "max_seconds": max_seconds},
            )
            time.sleep(wait_seconds)
        print(f"打卡模式：{'上班打卡' if mode == 'morning' else '下班打卡'}")
        run_offwork_sequence(
            package=args.package,
            title=args.title,
            timeout=args.timeout,
            launch_wait=args.launch_wait,
            delay=args.delay,
            fresh=not args.no_fresh,
            keep_scrcpy=args.keep_scrcpy,
            open_dingtalk=not args.no_open_dingtalk,
            use_templates=not args.no_template,
            template_threshold=args.template_threshold,
            step_timeout=args.step_timeout,
            step_retries=args.step_retries,
            retry_timeout=args.retry_timeout,
            mode=mode,
        )
    except Exception as exception:
        mark_failed(str(exception))
        raise

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
