#!/bin/zsh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

log() {
  printf '%s\n' "$1"
}

need_command() {
  command -v "$1" >/dev/null 2>&1
}

ensure_brew_packages() {
  local missing=()
  need_command python3.12 || missing+=("python@3.12")
  need_command adb || missing+=("android-platform-tools")
  need_command scrcpy || missing+=("scrcpy")

  if [ ${#missing[@]} -eq 0 ]; then
    return
  fi

  if ! need_command brew; then
    log "未检测到 Homebrew，无法自动安装：${missing[*]}"
    log "请先安装 Homebrew：https://brew.sh/"
    exit 1
  fi

  log "正在安装缺少的 macOS 依赖：${missing[*]}"
  brew install "${missing[@]}"
}

find_python312() {
  if need_command python3.12; then
    command -v python3.12
    return
  fi
  if [ -x "/opt/homebrew/bin/python3.12" ]; then
    printf '%s\n' "/opt/homebrew/bin/python3.12"
    return
  fi
  if [ -x "/usr/local/bin/python3.12" ]; then
    printf '%s\n' "/usr/local/bin/python3.12"
    return
  fi
  return 1
}

ensure_brew_packages

PYTHON312="$(find_python312)"
if [ -z "$PYTHON312" ]; then
  log "未找到 Python 3.12。请运行：brew install python@3.12"
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  log "正在创建虚拟环境：.venv"
  "$PYTHON312" -m venv .venv
fi

log "正在安装/更新 Python 依赖"
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

chmod +x start-panel.command start-panel.sh 启动钉钉打卡面板.command scripts/bootstrap_macos.sh scripts/doctor_macos.py scripts/launchd_schedule_runner.sh 2>/dev/null || true

mkdir -p logs screenshots assets/templates

log "正在运行环境诊断"
.venv/bin/python scripts/doctor_macos.py || log "诊断发现问题，请根据上面的提示处理。"

log "初始化完成。可以运行：./start-panel.command"
