#!/bin/sh
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/logs"
/bin/date '+script file fired %Y-%m-%d %H:%M:%S' >> "$ROOT/logs/script_file_test.log"
exit 0
