#!/bin/sh
export HOME=/Users/to
export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
cd /Users/to/Documents/logyxiao/ok-dd || exit 70
exec /opt/homebrew/Cellar/python@3.12/3.12.13_2/Frameworks/Python.framework/Versions/3.12/bin/python3.12 scripts/schedule_runner.py --mode "$1"
