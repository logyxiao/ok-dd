from __future__ import annotations

import ctypes
import subprocess
import time
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np
import psutil
import win32con
import win32api
import win32gui
import win32process
import win32ui


def _enable_dpi_awareness() -> None:
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_enable_dpi_awareness()


def build_scrcpy_command(title: str, extra_args: Iterable[str] | None = None) -> list[str]:
    command = ["scrcpy", "--window-title", title]
    if extra_args:
        command.extend(extra_args)
    return command


def start_scrcpy(title: str, extra_args: Iterable[str] | None = None) -> subprocess.Popen:
    return subprocess.Popen(
        build_scrcpy_command(title, extra_args),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def find_window_by_title(title: str) -> int | None:
    title_lower = title.lower()
    matched: list[int] = []

    def callback(hwnd: int, _lparam: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        window_title = win32gui.GetWindowText(hwnd)
        if title_lower in window_title.lower():
            matched.append(hwnd)
        return True

    win32gui.EnumWindows(callback, None)
    return matched[0] if matched else None


def list_visible_windows() -> list[tuple[int, str]]:
    windows: list[tuple[int, str]] = []

    def callback(hwnd: int, _lparam: object) -> bool:
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, None)
    return windows


def get_window_pid(hwnd: int) -> int:
    _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
    return pid


def get_window_process_name(hwnd: int) -> str:
    pid = get_window_pid(hwnd)
    try:
        return psutil.Process(pid).name()
    except psutil.Error:
        return str(pid)


def find_scrcpy_window() -> int | None:
    for hwnd, _title in list_visible_windows():
        process_name = get_window_process_name(hwnd).lower()
        if process_name == "scrcpy.exe":
            return hwnd
    return None


def wait_for_window(title: str, timeout: float = 20) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hwnd = find_window_by_title(title)
        if hwnd:
            return hwnd
        time.sleep(0.25)
    visible = "\n".join(f"- {window_title}" for _hwnd, window_title in list_visible_windows())
    raise TimeoutError(
        f"等待窗口超时，未找到标题包含以下内容的窗口：{title}\n"
        f"当前可见窗口：\n{visible}"
    )


def ensure_scrcpy_window(
    title: str = "OK Scrcpy Daily",
    extra_args: Iterable[str] | None = None,
    timeout: float = 20,
) -> int:
    hwnd = find_window_by_title(title)
    if hwnd:
        return hwnd
    start_scrcpy(title, extra_args)
    return wait_for_window(title, timeout)


def ensure_any_scrcpy_window(
    title: str = "OK Scrcpy Daily",
    extra_args: Iterable[str] | None = None,
    timeout: float = 20,
) -> tuple[int, bool]:
    hwnd = find_scrcpy_window()
    if hwnd:
        return hwnd, False

    process = start_scrcpy(title, extra_args)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hwnd = find_window_by_title(title) or find_scrcpy_window()
        if hwnd:
            return hwnd, True
        if process.poll() is not None:
            raise RuntimeError(f"scrcpy 提前退出，退出码：{process.returncode}")
        time.sleep(0.25)

    visible = "\n".join(f"- {window_title}" for _hwnd, window_title in list_visible_windows())
    raise TimeoutError(
        f"等待 scrcpy 窗口超时\n"
        f"当前可见窗口：\n{visible}"
    )


def close_window(hwnd: int) -> None:
    if win32gui.IsWindow(hwnd):
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)


def _client_rect_size(hwnd: int) -> tuple[int, int]:
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Window client area is empty: hwnd={hwnd}")
    return width, height


def capture_window(hwnd: int) -> np.ndarray:
    width, height = _client_rect_size(hwnd)
    hwnd_dc = win32gui.GetDC(hwnd)
    src_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    mem_dc = src_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(src_dc, width, height)
    mem_dc.SelectObject(bitmap)

    try:
        mem_dc.BitBlt((0, 0), (width, height), src_dc, (0, 0), win32con.SRCCOPY)
        bitmap_info = bitmap.GetInfo()
        bitmap_bits = bitmap.GetBitmapBits(True)
        frame = np.frombuffer(bitmap_bits, dtype=np.uint8)
        frame.shape = (bitmap_info["bmHeight"], bitmap_info["bmWidth"], 4)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        mem_dc.DeleteDC()
        src_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


def relative_box_to_pixels(
    frame: np.ndarray,
    box: Sequence[float],
) -> tuple[int, int, int, int]:
    if len(box) != 4:
        raise ValueError("Relative box must be: x,y,width,height")
    height, width = frame.shape[:2]
    x = max(0, min(width - 1, int(width * box[0])))
    y = max(0, min(height - 1, int(height * box[1])))
    right = max(x + 1, min(width, int(width * (box[0] + box[2]))))
    bottom = max(y + 1, min(height, int(height * (box[1] + box[3]))))
    return x, y, right - x, bottom - y


def crop_relative_box(frame: np.ndarray, box: Sequence[float]) -> np.ndarray:
    x, y, width, height = relative_box_to_pixels(frame, box)
    return frame[y : y + height, x : x + width]


def click_scrcpy_relative(hwnd: int, x: float, y: float) -> tuple[int, int]:
    width, height = _client_rect_size(hwnd)
    client_x = max(0, min(width - 1, int(width * x)))
    client_y = max(0, min(height - 1, int(height * y)))
    screen_x, screen_y = win32gui.ClientToScreen(hwnd, (client_x, client_y))
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    win32api.SetCursorPos((screen_x, screen_y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, screen_x, screen_y, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, screen_x, screen_y, 0, 0)
    return screen_x, screen_y


def capture_scrcpy_once(
    title: str,
    output_path: Path,
    start: bool = True,
    timeout: float = 20,
    extra_args: Iterable[str] | None = None,
) -> Path:
    hwnd = ensure_scrcpy_window(title, extra_args, timeout) if start else wait_for_window(title, timeout)
    frame = capture_window(hwnd)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), frame):
        raise RuntimeError(f"保存截图失败：{output_path}")
    return output_path


def capture_crop_and_click(
    title: str,
    crop_box: Sequence[float],
    screenshot_path: Path,
    crop_path: Path,
    start: bool = True,
    timeout: float = 20,
    extra_args: Iterable[str] | None = None,
) -> tuple[Path, Path, tuple[int, int]]:
    hwnd = ensure_scrcpy_window(title, extra_args, timeout) if start else wait_for_window(title, timeout)
    frame = capture_window(hwnd)
    crop = crop_relative_box(frame, crop_box)

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    crop_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(screenshot_path), frame):
        raise RuntimeError(f"保存截图失败：{screenshot_path}")
    if not cv2.imwrite(str(crop_path), crop):
        raise RuntimeError(f"保存裁剪图片失败：{crop_path}")

    click_x = crop_box[0] + crop_box[2] / 2
    click_y = crop_box[1] + crop_box[3] / 2
    clicked_at = click_scrcpy_relative(hwnd, click_x, click_y)
    return screenshot_path, crop_path, clicked_at
