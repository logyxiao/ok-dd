#!/bin/zsh
cd "$(dirname "$0")"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 1 http://127.0.0.1:8765/api/ping | grep -q '"app": "OK-DingTalk"'; then
    open http://127.0.0.1:8765/
    exit 0
  fi
fi

if [ ! -x ".venv/bin/python" ] || ! .venv/bin/python -c "import cv2, numpy, psutil" >/dev/null 2>&1; then
  ./scripts/bootstrap_macos.sh || exit 1
fi

.venv/bin/python scripts/dingtalk_gui.py
