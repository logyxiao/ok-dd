import ok

from config import config


if __name__ == "__main__":
    app = ok.OK(config)
    app.start()
