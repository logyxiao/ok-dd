#!/bin/sh
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
cd "$ROOT" || exit 70
if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python scripts/schedule_runner.py --mode "$1"
fi
if command -v python3.12 >/dev/null 2>&1; then
  exec python3.12 scripts/schedule_runner.py --mode "$1"
fi
exec python3 scripts/schedule_runner.py --mode "$1"
