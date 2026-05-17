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
    scale: float = 1.0

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


def template_scales() -> tuple[float, ...]:
    return (
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
        0.95,
        1.00,
        1.05,
        1.10,
        1.15,
        1.20,
        1.25,
        1.30,
        1.35,
        1.40,
        1.50,
        1.60,
        1.70,
        1.80,
        1.90,
        2.00,
    )


def resize_template(template: np.ndarray, scale: float) -> np.ndarray | None:
    if scale == 1.0:
        return template
    height, width = template.shape[:2]
    resized_width = max(1, int(width * scale))
    resized_height = max(1, int(height * scale))
    if resized_width < 4 or resized_height < 4:
        return None
    return cv2.resize(template, (resized_width, resized_height), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)


def best_template_match(frame: np.ndarray, template: np.ndarray) -> TemplateMatch | None:
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_height, frame_width = frame_gray.shape[:2]
    best: TemplateMatch | None = None
    for scale in template_scales():
        scaled_template = resize_template(template, scale)
        if scaled_template is None:
            continue
        template_height, template_width = scaled_template.shape[:2]
        if frame_height < template_height or frame_width < template_width:
            continue
        template_gray = cv2.cvtColor(scaled_template, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
        match = TemplateMatch(
            score=float(max_val),
            x=int(max_loc[0]),
            y=int(max_loc[1]),
            width=template_width,
            height=template_height,
            frame_width=frame_width,
            frame_height=frame_height,
            scale=scale,
        )
        if best is None or match.score > best.score:
            best = match
    return best


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
        match = best_template_match(frame, template)
        if match:
            best_score = max(best_score, match.score)
        if match and match.score >= threshold:
            return match
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
