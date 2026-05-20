#!/bin/zsh
cd "$(dirname "$0")"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

fail() {
  echo "$1"
  echo
  echo "你也可以手动运行：./scripts/bootstrap_macos.sh"
  if [ -t 0 ]; then
    read "unused?按回车退出..."
  fi
  exit 1
}

if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 1 http://127.0.0.1:8765/api/ping | grep -q '"app": "OK-DingTalk"'; then
    open http://127.0.0.1:8765/
    exit 0
  fi
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "首次运行：正在初始化 macOS 环境..."
  ./scripts/bootstrap_macos.sh || fail "初始化失败。"
fi

if ! .venv/bin/python -c "import cv2, numpy, psutil" >/dev/null 2>&1; then
  echo "检测到 Python 依赖缺失，正在修复..."
  ./scripts/bootstrap_macos.sh || fail "依赖修复失败。"
fi

if ! command -v adb >/dev/null 2>&1; then
  fail "未检测到 adb。请先安装 Android platform tools。"
fi

.venv/bin/python scripts/dingtalk_gui.py
