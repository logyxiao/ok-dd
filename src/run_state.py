from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.paths import app_root

ROOT = app_root()
LOG_DIR = ROOT / "logs"
ACTION_LOG = LOG_DIR / "dingtalk_actions.jsonl"
STATE_FILE = LOG_DIR / "dingtalk_state.json"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_action(event: str, status: str, message: str = "", details: dict[str, Any] | None = None) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "time": now_text(),
        "event": event,
        "status": status,
        "message": message,
        "details": details or {},
    }
    with ACTION_LOG.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    with STATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def mark_completed(message: str = "已完成", event: str = "下班打卡序列") -> None:
    completed_at = now_text()
    state = load_state()
    state["last_completed_at"] = completed_at
    state["last_completed_date"] = completed_at[:10]
    state["last_status"] = "成功"
    state["last_message"] = message
    save_state(state)
    append_action(event, "成功", message)


def mark_failed(message: str, event: str = "下班打卡序列") -> None:
    state = load_state()
    state["last_failed_at"] = now_text()
    state["last_status"] = "失败"
    state["last_message"] = message
    save_state(state)
    append_action(event, "失败", message)


def completed_today() -> bool:
    return load_state().get("last_completed_date") == datetime.now().strftime("%Y-%m-%d")


def read_recent_actions(limit: int = 80) -> list[dict[str, Any]]:
    if not ACTION_LOG.exists():
        return []
    lines = ACTION_LOG.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append({"time": "", "event": "原始日志", "status": "未知", "message": line, "details": {}})
    return records
