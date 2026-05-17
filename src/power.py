from __future__ import annotations

import ctypes
import os
import subprocess
import time

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    import win32api

    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_AWAYMODE_REQUIRED = 0x00000040

CAFFEINATE_PROCESS: subprocess.Popen | None = None


def keep_system_awake() -> None:
    """Ask the current OS to keep system and display awake while this script runs."""
    global CAFFEINATE_PROCESS
    if not IS_WINDOWS:
        if os.name == "posix" and CAFFEINATE_PROCESS is None:
            CAFFEINATE_PROCESS = subprocess.Popen(
                ["caffeinate", "-dims"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return

    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
    )


def restore_sleep() -> None:
    global CAFFEINATE_PROCESS
    if not IS_WINDOWS:
        if CAFFEINATE_PROCESS and CAFFEINATE_PROCESS.poll() is None:
            CAFFEINATE_PROCESS.terminate()
        CAFFEINATE_PROCESS = None
        return

    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def wake_display() -> None:
    """Nudge display awake without changing final cursor position where supported."""
    if not IS_WINDOWS:
        return

    try:
        x, y = win32api.GetCursorPos()
        win32api.SetCursorPos((x + 1, y))
        time.sleep(0.05)
        win32api.SetCursorPos((x, y))
    except Exception:
        pass
