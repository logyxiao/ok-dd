import ok

from config import config
from src.scrcpy import ensure_scrcpy_window


if __name__ == "__main__":
    ensure_scrcpy_window(
        title=config["scrcpy"]["window_title"],
        extra_args=config["scrcpy"].get("args", []),
        timeout=config["scrcpy"].get("startup_timeout", 20),
    )
    debug_config = dict(config)
    debug_config["debug"] = True
    app = ok.OK(debug_config)
    app.start()
