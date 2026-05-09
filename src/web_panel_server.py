from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.run_state import LOG_DIR, completed_today, load_state, read_recent_actions
from src.paths import app_root, resource_path
from src.workday import describe_china_workday, is_china_workday

ROOT = app_root()
WEB_DIR = resource_path("web")
TASK_NAME = "DingTalk Offwork Clock"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def automation_command(workday_only: bool = False, dry_run: bool = False, keep_scrcpy: bool = False) -> list[str]:
    if is_frozen():
        exe = Path(sys.executable)
        if exe.name.lower() == "ok-dingtalk-panel.exe":
            auto_exe = exe.parent.parent / "auto" / "OK-DingTalk-Auto.exe"
        else:
            auto_exe = exe.parent / "auto" / "OK-DingTalk-Auto.exe"
        command = [str(auto_exe)]
    else:
        command = [sys.executable, str(ROOT / "scripts" / "dingtalk_offwork_sequence.py")]

    if workday_only:
        command.append("--workday-only")
    if dry_run:
        command.append("--dry-run")
    if keep_scrcpy:
        command.append("--keep-scrcpy")
    return command


def automation_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def powershell(command: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def get_task_info() -> dict:
    command = (
        f"$t=Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue; "
        f"$i=Get-ScheduledTaskInfo -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue; "
        "if ($t -and $i) { "
        "[pscustomobject]@{installed=$true;state=$t.State.ToString();nextRun=$i.NextRunTime.ToString('yyyy-MM-dd HH:mm:ss');"
        "lastRun=$i.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss');lastResult=$i.LastTaskResult} | ConvertTo-Json -Compress "
        "} else { [pscustomobject]@{installed=$false;state='Missing'} | ConvertTo-Json -Compress }"
    )
    try:
        result = powershell(command)
        if result.returncode != 0:
            return {"installed": False}
        data = json.loads(result.stdout.strip() or "{}")
        return {
                "installed": bool(data.get("installed")),
                "state": data.get("state", ""),
                "enabled": data.get("state", "") != "Disabled",
                "next_run": data.get("nextRun", ""),
                "last_run": data.get("lastRun", ""),
                "last_result": data.get("lastResult", ""),
        }
    except Exception as exc:
        return {"installed": False, "error": str(exc)}


class ProcessState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process: subprocess.Popen | None = None
        self.output: list[str] = []
        self.started_at = ""
        self.last_exit_code: int | None = None

    def is_running(self) -> bool:
        with self.lock:
            return self.process is not None and self.process.poll() is None

    def append(self, text: str) -> None:
        with self.lock:
            self.output.append(text)
            if len(self.output) > 500:
                self.output = self.output[-500:]

    def snapshot(self) -> dict:
        with self.lock:
            running = self.process is not None and self.process.poll() is None
            return {
                "running": running,
                "started_at": self.started_at,
                "last_exit_code": self.last_exit_code,
                "output": "".join(self.output[-200:]),
            }

    def start(self, command: list[str]) -> tuple[bool, str]:
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return False, "已有任务正在运行"
            self.output = [f"执行命令：{subprocess.list2cmdline(command)}\n"]
            self.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.last_exit_code = None
            self.process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=automation_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW,
            )
            process = self.process

        def reader() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                self.append(line)
            exit_code = process.wait()
            self.append(f"\n[退出码 {exit_code}]\n")
            with self.lock:
                self.last_exit_code = exit_code

        threading.Thread(target=reader, daemon=True).start()
        return True, "已启动"

    def stop(self) -> tuple[bool, str]:
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                return False, "当前没有正在执行的脚本"
            process = self.process
        process.terminate()
        self.append("\n已请求停止当前执行\n")
        return True, "已请求停止"


PROCESS_STATE = ProcessState()


class WebPanelHandler(BaseHTTPRequestHandler):
    server_version = "OKDingTalkWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_json(self.status_payload())
            return
        if parsed.path == "/api/process":
            self.send_json(PROCESS_STATE.snapshot())
            return
        if parsed.path == "/api/open":
            target = parse_qs(parsed.query).get("target", [""])[0]
            self.open_target(target)
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            payload = {}

        if parsed.path == "/api/run":
            self.start_run(payload)
            return
        if parsed.path == "/api/install-task":
            self.install_task(payload)
            return
        if parsed.path == "/api/delete-task":
            self.delete_task()
            return
        if parsed.path == "/api/pause-task":
            self.set_task_enabled(False)
            return
        if parsed.path == "/api/resume-task":
            self.set_task_enabled(True)
            return
        if parsed.path == "/api/stop-run":
            ok, message = PROCESS_STATE.stop()
            self.send_json({"ok": ok, "message": message, "process": PROCESS_STATE.snapshot()})
            return
        if parsed.path == "/api/shutdown":
            self.send_json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def status_payload(self) -> dict:
        state = load_state()
        logs = read_recent_actions(200)
        return {
            "completed_today": completed_today(),
            "state": state,
            "workday": {
                "description": describe_china_workday(),
                "will_run": is_china_workday(),
            },
            "task": get_task_info(),
            "logs": logs,
            "process": PROCESS_STATE.snapshot(),
        }

    def start_run(self, payload: dict) -> None:
        command = automation_command(
            workday_only=bool(payload.get("workday_only")),
            dry_run=bool(payload.get("dry_run")),
            keep_scrcpy=bool(payload.get("keep_scrcpy")),
        )
        ok, message = PROCESS_STATE.start(command)
        self.send_json({"ok": ok, "message": message, "process": PROCESS_STATE.snapshot()})

    def install_task(self, payload: dict) -> None:
        time_text = str(payload.get("time") or "18:05").strip()
        workday_only = bool(payload.get("workday_only", True))
        command_text = subprocess.list2cmdline(automation_command(workday_only=workday_only))
        command = [
            "schtasks",
            "/Create",
            "/TN",
            TASK_NAME,
            "/TR",
            command_text,
            "/SC",
            "DAILY",
            "/ST",
            time_text,
            "/F",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
        self.send_json(
            {
                "ok": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "task": get_task_info(),
            }
        )

    def delete_task(self) -> None:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
        self.send_json({"ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})

    def set_task_enabled(self, enabled: bool) -> None:
        action = "/Enable" if enabled else "/Disable"
        result = subprocess.run(
            ["schtasks", "/Change", "/TN", TASK_NAME, action],
            cwd=ROOT,
            text=True,
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
        self.send_json(
            {
                "ok": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "task": get_task_info(),
            }
        )

    def open_target(self, target: str) -> None:
        if target == "logs":
            path = LOG_DIR
        elif target == "screenshots":
            path = ROOT / "screenshots"
        else:
            self.send_json({"ok": False, "message": "未知目标目录"}, status=HTTPStatus.BAD_REQUEST)
            return
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)
        self.send_json({"ok": True})

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        relative = path.lstrip("/")
        file_path = (WEB_DIR / relative).resolve()
        if not str(file_path).startswith(str(WEB_DIR.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_types.get(file_path.suffix, "application/octet-stream"))
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args) -> None:
        return


def find_free_port(start: int = 8765) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("没有找到可用的本地端口")


def start_web_panel(open_browser: bool = True) -> tuple[ThreadingHTTPServer, str]:
    port = find_free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), WebPanelHandler)
    url = f"http://127.0.0.1:{port}/"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(url)
    return server, url


def main() -> int:
    server, url = start_web_panel(open_browser=True)
    print(f"OK-DingTalk Web 面板：{url}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
