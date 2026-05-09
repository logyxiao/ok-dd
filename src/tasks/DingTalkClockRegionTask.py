from pathlib import Path

from qfluentwidgets import FluentIcon

from ok import BaseTask
from src.adb import back_until_focus_contains, launch_package
from src.config import config
from src.scrcpy import capture_crop_and_click


class DingTalkClockRegionTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "打开钉钉并点击打卡区域"
        self.description = "ADB 启动钉钉，截图保存打卡区域，并用鼠标点击区域中心"
        self.icon = FluentIcon.PLAY

    def run(self):
        scrcpy_config = config["scrcpy"]
        dingtalk_config = config["dingtalk"]
        launch_package(
            dingtalk_config["package"],
            wait_seconds=dingtalk_config.get("launch_wait", 3),
        )
        focus = back_until_focus_contains("LaunchHomeActivity")
        screenshot, crop, clicked_at = capture_crop_and_click(
            title=scrcpy_config["window_title"],
            crop_box=dingtalk_config["clock_region"],
            screenshot_path=Path(config["screenshots_folder"]) / "dingtalk_full.png",
            crop_path=Path(config["screenshots_folder"]) / "dingtalk_clock_region.png",
            start=True,
            timeout=scrcpy_config.get("startup_timeout", 20),
            extra_args=scrcpy_config.get("args", []),
        )
        self.log_info(f"当前焦点: {focus}")
        self.log_info(f"已保存钉钉截图: {screenshot}")
        self.log_info(f"已保存打卡区域: {crop}")
        self.log_info(f"已点击屏幕坐标: {clicked_at[0]},{clicked_at[1]}", notify=True)
