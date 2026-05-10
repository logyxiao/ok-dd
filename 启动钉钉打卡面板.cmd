@echo off
cd /d "%~dp0"
for /f "usebackq delims=" %%u in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-RestMethod 'http://127.0.0.1:8765/api/ping' -TimeoutSec 1; if ($r.app -eq 'OK-DingTalk') { 'http://127.0.0.1:8765/' } } catch {}"`) do (
  start "" "%%u"
  exit /b 0
)
pythonw "%~dp0dingtalk_gui.pyw"
