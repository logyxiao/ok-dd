$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
python (Join-Path $Root "scripts\create_desktop_shortcut.py")
