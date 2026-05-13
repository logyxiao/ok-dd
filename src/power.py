from __future__ import annotations

import ctypes
import time

import win32api

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040


def keep_system_awake() -> None:
    """Ask Windows to keep system and display awake while current thread runs."""
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
    )


def restore_sleep() -> None:
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def wake_display() -> None:
    """Nudge display awake without changing final cursor position."""
    try:
        x, y = win32api.GetCursorPos()
        win32api.SetCursorPos((x + 1, y))
        time.sleep(0.05)
        win32api.SetCursorPos((x, y))
    except Exception:
        pass
