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

SCHEDULE_FILE = LOG_DIR / "schedule_config.json"
RUNNER_STATE_FILE = LOG_DIR / "schedule_runner_state.json"


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


def main() -> int:
    args = parse_args()
    schedule = load_json(SCHEDULE_FILE)
    target = str(schedule.get(f"{args.mode}_time") or "").strip()
    if not target:
        return 0

    now = datetime.now()
    if now.strftime("%H:%M") != target:
        return 0

    state = load_json(RUNNER_STATE_FILE)
    run_key = f"{now.date().isoformat()}:{args.mode}:{target}"
    if state.get(run_key):
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
    if schedule.get("workday_only", True):
        command.append("--workday-only")
    if random_delay_minutes > 0:
        command.extend(["--random-delay-minutes", str(random_delay_minutes)])

    append_action(
        "自动计划",
        "触发",
        f"{'早上' if args.mode == 'morning' else '晚上'}计划到点，启动脚本",
        {"mode": args.mode, "target": target, "command": command},
    )
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
