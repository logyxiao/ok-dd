#!/bin/zsh
cd "$(dirname "$0")"

if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 1 http://127.0.0.1:8765/api/ping | grep -q '"app": "OK-DingTalk"'; then
    open http://127.0.0.1:8765/
    exit 0
  fi
fi

if [ -x ".venv/bin/python" ]; then
  .venv/bin/python scripts/dingtalk_gui.py
else
  python3 scripts/dingtalk_gui.py
fi
