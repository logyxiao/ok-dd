from qfluentwidgets import FluentIcon

from ok import BaseTask
from src.config import config
from src.offwork_sequence import run_offwork_sequence


class OffworkSequenceTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "下班打卡序列"
        self.description = "打开钉钉，复用或启动 scrcpy，并按已标定坐标完成下班打卡"
        self.icon = FluentIcon.PLAY

    def run(self):
        scrcpy_config = config["scrcpy"]
        dingtalk_config = config["dingtalk"]
        run_offwork_sequence(
            package=dingtalk_config["package"],
            title=scrcpy_config["window_title"],
            timeout=scrcpy_config.get("startup_timeout", 20),
            launch_wait=dingtalk_config.get("launch_wait", 4),
            delay=dingtalk_config.get("step_delay", 4),
            fresh=dingtalk_config.get("fresh_start", True),
            keep_scrcpy=dingtalk_config.get("keep_scrcpy", False),
            open_dingtalk=True,
            mode=dingtalk_config.get("mode", "evening"),
            progress=lambda message: self.log_info(message),
        )
