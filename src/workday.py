from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from src.paths import app_root, resource_path

ROOT = app_root()
DEFAULT_CALENDAR = ROOT / "data" / "china_workdays_2026.json"


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_calendar(path: Path = DEFAULT_CALENDAR) -> dict:
    if not path.exists() and path == DEFAULT_CALENDAR:
        path = resource_path("data/china_workdays_2026.json")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def is_china_workday(day: date | None = None, calendar_path: Path = DEFAULT_CALENDAR) -> bool:
    day = day or date.today()
    calendar = load_calendar(calendar_path)
    day_text = day.isoformat()
    if day_text in calendar.get("workdays", []):
        return True
    if day_text in calendar.get("holidays", []):
        return False
    return day.weekday() < 5


def describe_china_workday(day: date | None = None, calendar_path: Path = DEFAULT_CALENDAR) -> str:
    day = day or date.today()
    calendar = load_calendar(calendar_path)
    day_text = day.isoformat()
    if day_text in calendar.get("workdays", []):
        return f"{day_text} 是法定调休上班日"
    if day_text in calendar.get("holidays", []):
        return f"{day_text} 是法定节假日"
    if day.weekday() < 5:
        return f"{day_text} 是普通工作日"
    return f"{day_text} 是普通周末"
