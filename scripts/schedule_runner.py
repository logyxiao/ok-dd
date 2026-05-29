import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.run_state import LOG_DIR, append_action
from src.workday import describe_china_workday, is_china_workday

SCHEDULE_FILE = LOG_DIR / "schedule_config.json"
RUNNER_STATE_FILE = LOG_DIR / "schedule_runner_state.json"
RUN_GRACE_MINUTES = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 macOS 间隔触发的自动计划是否到执行时间。")
    parser.add_argument("--mode", choices=["morning", "evening"], required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_target_datetime(now: datetime, target: str) -> datetime:
    parsed = datetime.strptime(target, "%H:%M")
    return now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)


def is_due(now: datetime, target: str, grace_minutes: int = RUN_GRACE_MINUTES) -> tuple[bool, str, int]:
    target_at = parse_target_datetime(now, target)
    late_seconds = int((now - target_at).total_seconds())
    if late_seconds < 0:
        return False, "未到计划时间", late_seconds
    if late_seconds > grace_minutes * 60:
        return False, f"已超过 {grace_minutes} 分钟容忍窗口", late_seconds
    return True, "计划到点", late_seconds


def main() -> int:
    args = parse_args()
    schedule = load_json(SCHEDULE_FILE)
    target = str(schedule.get(f"{args.mode}_time") or "").strip()
    if not target:
        append_action("自动计划", "跳过", "未配置目标时间", {"mode": args.mode})
        return 0

    now = datetime.now()
    try:
        due, reason, late_seconds = is_due(now, target)
    except ValueError:
        append_action("自动计划", "跳过", "目标时间格式无效", {"mode": args.mode, "target": target})
        return 0

    if not due:
        append_action(
            "自动计划",
            "跳过",
            reason,
            {
                "mode": args.mode,
                "target": target,
                "now": now.strftime("%H:%M:%S"),
                "late_seconds": late_seconds,
                "grace_minutes": RUN_GRACE_MINUTES,
            },
        )
        return 0

    run_date = now.date()
    if not is_china_workday(run_date):
        description = describe_china_workday(run_date)
        append_action(
            "自动计划",
            "跳过",
            f"{description}，不执行自动打卡",
            {
                "mode": args.mode,
                "target": target,
                "date": run_date.isoformat(),
                "workday_only": True,
            },
        )
        return 0

    state = load_json(RUNNER_STATE_FILE)
    run_key = f"{now.date().isoformat()}:{args.mode}:{target}"
    if state.get(run_key):
        append_action(
            "自动计划",
            "跳过",
            "今天该计划已触发过",
            {"mode": args.mode, "target": target, "previous": state.get(run_key)},
        )
        return 0

    state[run_key] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_json(RUNNER_STATE_FILE, state)

    random_delay_minutes = int(schedule.get("random_window_minutes") or 0) * 2
    command = [
        sys.executable,
        str(ROOT / "scripts" / "dingtalk_offwork_sequence.py"),
        "--mode",
        args.mode,
    ]
    command.append("--workday-only")
    if random_delay_minutes > 0:
        command.extend(["--random-delay-minutes", str(random_delay_minutes)])

    append_action(
        "自动计划",
        "触发",
        f"{'早上' if args.mode == 'morning' else '晚上'}计划到点，启动脚本",
        {
            "mode": args.mode,
            "target": target,
            "late_seconds": late_seconds,
            "grace_minutes": RUN_GRACE_MINUTES,
            "command": command,
        },
    )
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
