from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.scrcpy import capture_window, click_scrcpy_relative


@dataclass(frozen=True)
class TemplateMatch:
    score: float
    x: int
    y: int
    width: int
    height: int
    frame_width: int
    frame_height: int

    @property
    def center_relative(self) -> tuple[float, float]:
        return (
            (self.x + self.width / 2) / self.frame_width,
            (self.y + self.height / 2) / self.frame_height,
        )


def load_template(path: Path) -> np.ndarray:
    template = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if template is None:
        raise FileNotFoundError(f"无法读取模板图片：{path}")
    return template


def best_template_match(frame: np.ndarray, template: np.ndarray) -> TemplateMatch | None:
    if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
        return None

    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
    height, width = template_gray.shape[:2]
    frame_height, frame_width = frame_gray.shape[:2]
    return TemplateMatch(
        score=float(max_val),
        x=int(max_loc[0]),
        y=int(max_loc[1]),
        width=width,
        height=height,
        frame_width=frame_width,
        frame_height=frame_height,
    )


def find_template(frame: np.ndarray, template: np.ndarray, threshold: float = 0.86) -> TemplateMatch | None:
    match = best_template_match(frame, template)
    if not match or match.score < threshold:
        return None
    return match


def wait_template(
    hwnd: int,
    template_path: Path,
    threshold: float = 0.86,
    timeout: float = 20,
    interval: float = 0.5,
) -> TemplateMatch:
    template = load_template(template_path)
    deadline = time.monotonic() + timeout
    best_score = 0.0
    while time.monotonic() < deadline:
        frame = capture_window(hwnd)
        match = find_template(frame, template, threshold=threshold)
        if match:
            return match
        raw = cv2.matchTemplate(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(template, cv2.COLOR_BGR2GRAY),
            cv2.TM_CCOEFF_NORMED,
        )
        best_score = max(best_score, float(cv2.minMaxLoc(raw)[1]))
        time.sleep(interval)
    raise TimeoutError(f"等待模板出现超时：{template_path}，最佳相似度：{best_score:.3f}")


def wait_click_template(
    hwnd: int,
    template_path: Path,
    threshold: float = 0.86,
    timeout: float = 20,
    interval: float = 0.5,
) -> tuple[TemplateMatch, tuple[int, int]]:
    match = wait_template(hwnd, template_path, threshold=threshold, timeout=timeout, interval=interval)
    relative_x, relative_y = match.center_relative
    clicked_at = click_scrcpy_relative(hwnd, relative_x, relative_y)
    return match, clicked_at
