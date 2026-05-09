from pathlib import Path

import cv2
from qfluentwidgets import FluentIcon

from ok import BaseTask
from src.config import config
from src.scrcpy import ensure_scrcpy_window


class CaptureScrcpyTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "抓取 scrcpy 画面"
        self.description = "启动或连接 scrcpy 窗口，并保存当前画面"
        self.icon = FluentIcon.CAMERA

    def run(self):
        scrcpy_config = config["scrcpy"]
        ensure_scrcpy_window(
            title=scrcpy_config["window_title"],
            extra_args=scrcpy_config.get("args", []),
            timeout=scrcpy_config.get("startup_timeout", 20),
        )
        frame = self.next_frame()
        output = Path(config["screenshots_folder"]) / "ok_script_scrcpy_capture.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output), frame)
        self.screenshot("ok_script_scrcpy_capture", frame=frame)
        self.log_info(f"已保存 scrcpy 画面: {output}", notify=True)
