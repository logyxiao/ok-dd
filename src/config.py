import os

from ok import ConfigOption

version = "dev"

scrcpy_option = ConfigOption(
    "Scrcpy",
    {
        "Window Title": "OK Scrcpy Daily",
        "Startup Timeout": 20,
        "DingTalk Package": "com.alibaba.android.rimet",
        "Clock Region": [0.05, 0.50, 0.92, 0.11],
    },
    description="scrcpy window startup and capture settings",
)

schedule_option = ConfigOption(
    "Schedule",
    {
        "Offwork Time": "18:05",
        "Workday Only": True,
    },
    description="Windows scheduled task settings",
)

config = {
    "debug": False,
    "use_gui": True,
    "config_folder": "configs",
    "global_configs": [scrcpy_option, schedule_option],
    "gui_title": "OK-DingTalk",
    "gui_icon": "icon.png",
    "log_file": "logs/ok-dingtalk.log",
    "error_log_file": "logs/ok-dingtalk_error.log",
    "launcher_log_file": "logs/launcher.log",
    "launcher_error_log_file": "logs/launcher_error.log",
    "screenshots_folder": "screenshots",
    "window_size": {
        "width": 1200,
        "height": 800,
        "min_width": 1100,
        "min_height": 720,
    },
    "links": {
        "default": {
            "github": "https://github.com/ok-oldking/ok-script",
            "faq": "https://github.com/ok-oldking/ok-script",
            "share": "OK-DingTalk DingTalk offwork automation",
        },
        "zh_CN": {
            "github": "https://github.com/ok-oldking/ok-script",
            "faq": "https://github.com/ok-oldking/ok-script",
            "share": "OK-DingTalk 钉钉下班打卡自动化",
        },
    },
    "about": """
OK-DingTalk 是一个基于 ok-script 的个人自动化工具，用于在本机通过 ADB、scrcpy 和常规鼠标点击完成重复操作。

请确保你了解并遵守所在组织关于考勤、自动化工具和设备使用的规则。使用本工具产生的后果由使用者自行承担。
""",
    "wait_until_before_delay": 0,
    "wait_until_check_delay": 0,
    "wait_until_settle_time": 0,
    "scrcpy": {
        "window_title": "OK Scrcpy Daily",
        "startup_timeout": 20,
        "args": [],
    },
    "dingtalk": {
        "package": "com.alibaba.android.rimet",
        "launch_wait": 4,
        "step_delay": 4,
        "fresh_start": True,
        "keep_scrcpy": False,
        "clock_region": [0.05, 0.50, 0.92, 0.11],
    },
    "windows": {
        "exe": ["scrcpy.exe"],
        "interaction": ["Pynput", "ForegroundPostMessage", "PostMessage"],
        "capture_method": ["WGC", "BitBlt_RenderFull", "BitBlt"],
        "check_hdr": False,
        "force_no_hdr": False,
        "require_bg": False,
    },
    "supported_resolution": {
        "ratio": "9:16",
        "min_size": (360, 640),
        "resize_to": [(720, 1280), (1080, 1920)],
    },
    "template_matching": {
        "coco_feature_json": os.path.join("assets", "coco_annotations.json"),
        "default_horizontal_variance": 0.002,
        "default_vertical_variance": 0.002,
        "default_threshold": 0.8,
    },
    "onetime_tasks": [
        ["src.tasks.OffworkSequenceTask", "OffworkSequenceTask"],
        ["src.tasks.CaptureScrcpyTask", "CaptureScrcpyTask"],
        ["src.tasks.DingTalkClockRegionTask", "DingTalkClockRegionTask"],
        ["ok", "DiagnosisTask"],
    ],
    "trigger_tasks": [],
    "version": version,
}
