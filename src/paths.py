from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.lower() in {"panel", "auto"}:
            return exe_dir.parent
        return exe_dir
    return Path(__file__).resolve().parents[1]


def resource_path(relative: str) -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / relative
    return app_root() / relative
