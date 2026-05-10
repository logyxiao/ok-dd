from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import cv2

from src.run_state import LOG_DIR, completed_today, load_state, read_recent_actions
from src.paths import app_root, resource_path
from src.scrcpy import capture_window, close_window, ensure_any_scrcpy_window
from src.vision import find_template, load_template, wait_click_template, wait_template
from src.workday import describe_china_workday, is_china_workday

ROOT = app_root()
WEB_DIR = resource_path("web")
TASK_NAME = "DingTalk Clock"
LEGACY_TASK_NAMES = ["DingTalk Offwork Clock"]
TASKS = {
    "morning": {"name": "DingTalk Morning Clock", "label": "早上打卡"},
    "evening": {"name": "DingTalk Evening Clock", "label": "晚上打卡"},
}
TEMPLATE_DIR = ROOT / "assets" / "templates"
SCREENSHOT_DIR = ROOT / "screenshots"
CURRENT_SCREENSHOT = SCREENSHOT_DIR / "current_screen.png"
TEMPLATE_STEPS = {
    "morning.work_notice": {"mode": "morning", "mode_label": "上班打卡", "label": "打开上班打卡入口", "file": "morning_work_notice.png", "action": "click"},
    "morning.clock_button": {"mode": "morning", "mode_label": "上班打卡", "label": "点击打卡上班", "file": "morning_clock_button.png", "action": "click"},
    "morning.field_clock_button": {
        "mode": "morning",
        "mode_label": "上班打卡",
        "label": "点击外勤打卡上班",
        "file": "morning_field_clock_button.png",
        "action": "click",
    },
    "morning.success_text": {
        "mode": "morning",
        "mode_label": "上班打卡",
        "label": "确认上班打卡成功",
        "file": "morning_success_text.png",
        "action": "verify",
    },
    "evening.work_notice": {"mode": "evening", "mode_label": "下班打卡", "label": "打开下班打卡入口", "file": "work_notice.png", "action": "click"},
    "evening.offwork_button": {"mode": "evening", "mode_label": "下班打卡", "label": "点击打卡下班", "file": "offwork_button.png", "action": "click"},
    "evening.field_offwork_button": {
        "mode": "evening",
        "mode_label": "下班打卡",
        "label": "点击外勤打卡下班",
        "file": "field_offwork_button.png",
        "action": "click",
    },
    "evening.success_text": {
        "mode": "evening",
        "mode_label": "下班打卡",
        "label": "确认下班打卡成功",
        "file": "offwork_success_text.png",
        "action": "verify",
    },
}
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
DEFAULT_PORT = 8765


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def automation_command(
    workday_only: bool = False,
    dry_run: bool = False,
    keep_scrcpy: bool = False,
    random_delay_minutes: float = 0,
    mode: str = "auto",
) -> list[str]:
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
    if random_delay_minutes > 0:
        command.extend(["--random-delay-minutes", str(random_delay_minutes)])
    if mode:
        command.extend(["--mode", mode])
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


def get_single_task_info(task_name: str) -> dict:
    command = (
        f"$t=Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
        f"$i=Get-ScheduledTaskInfo -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
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


def get_task_info() -> dict:
    tasks = {}
    for key, meta in TASKS.items():
        info = get_single_task_info(meta["name"])
        info["name"] = meta["name"]
        info["label"] = meta["label"]
        tasks[key] = info

    installed_tasks = [task for task in tasks.values() if task.get("installed")]
    enabled_tasks = [task for task in installed_tasks if task.get("enabled")]
    next_runs = [task.get("next_run", "") for task in enabled_tasks if task.get("next_run")]
    next_run = min(next_runs) if next_runs else ""
    return {
        "installed": bool(installed_tasks),
        "all_installed": len(installed_tasks) == len(TASKS),
        "enabled": bool(enabled_tasks),
        "state": "Ready" if enabled_tasks else ("Disabled" if installed_tasks else "Missing"),
        "next_run": next_run,
        "last_run": max([task.get("last_run", "") for task in installed_tasks if task.get("last_run")] or [""]),
        "last_result": "",
        "tasks": tasks,
    }


def parse_hhmm(value: str) -> datetime:
    return datetime.strptime(value, "%H:%M")


def trigger_time_for_target(target_time: str, random_window_minutes: int) -> str:
    target = parse_hhmm(target_time)
    trigger = target - timedelta(minutes=random_window_minutes)
    return trigger.strftime("%H:%M")


def task_missing_result(result: subprocess.CompletedProcess) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    return "cannot find" in text or "找不到" in text or "不存在" in text


def template_path(key: str) -> Path:
    return TEMPLATE_DIR / TEMPLATE_STEPS[key]["file"]


def template_payload(key: str) -> dict:
    meta = TEMPLATE_STEPS[key]
    path = template_path(key)
    return {
        "key": key,
        "mode": meta["mode"],
        "mode_label": meta["mode_label"],
        "label": meta["label"],
        "file": meta["file"],
        "action": meta["action"],
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
        "url": f"/api/template-file?key={key}&t={int(path.stat().st_mtime) if path.exists() else 0}",
    }


def get_template_info() -> list[dict]:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    return [template_payload(key) for key in TEMPLATE_STEPS]


def parse_multipart(raw: bytes, boundary: bytes) -> dict[str, bytes]:
    fields: dict[str, bytes] = {}
    for part in raw.split(boundary):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header, _, body = part.partition(b"\r\n\r\n")
        disposition = ""
        for line in header.decode("utf-8", errors="ignore").splitlines():
            if line.lower().startswith("content-disposition:"):
                disposition = line
                break
        name = ""
        for item in disposition.split(";"):
            item = item.strip()
            if item.startswith("name="):
                name = unquote(item.split("=", 1)[1].strip('"'))
        if name:
            fields[name] = body.rstrip(b"\r\n")
    return fields


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
        if parsed.path == "/api/ping":
            self.send_json({"ok": True, "app": "OK-DingTalk"})
            return
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
        if parsed.path == "/api/template-file":
            key = parse_qs(parsed.query).get("key", [""])[0]
            self.serve_template_file(key)
            return
        if parsed.path == "/api/screenshot-file":
            self.serve_screenshot_file()
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload-template":
            self.with_json_errors(self.upload_template)
            return
        if parsed.path == "/api/capture-current-screen":
            self.with_json_errors(self.capture_current_screen)
            return

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
        if parsed.path == "/api/test-template":
            self.with_json_errors(lambda: self.test_template(payload))
            return
        if parsed.path == "/api/click-template":
            self.with_json_errors(lambda: self.click_template(payload))
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
            "templates": get_template_info(),
            "logs": logs,
            "process": PROCESS_STATE.snapshot(),
        }

    def start_run(self, payload: dict) -> None:
        command = automation_command(
            workday_only=bool(payload.get("workday_only")),
            dry_run=bool(payload.get("dry_run")),
            keep_scrcpy=bool(payload.get("keep_scrcpy")),
            mode=str(payload.get("mode") or "auto"),
        )
        ok, message = PROCESS_STATE.start(command)
        self.send_json({"ok": ok, "message": message, "process": PROCESS_STATE.snapshot()})

    def install_task(self, payload: dict) -> None:
        morning_time = str(payload.get("morning_time") or "09:00").strip()
        evening_time = str(payload.get("evening_time") or "18:30").strip()
        workday_only = bool(payload.get("workday_only", True))
        random_window_minutes = int(payload.get("random_window_minutes") or 5)
        random_delay_minutes = random_window_minutes * 2
        outputs = []
        ok = True
        for key, target_time in {"morning": morning_time, "evening": evening_time}.items():
            task_name = TASKS[key]["name"]
            trigger_time = trigger_time_for_target(target_time, random_window_minutes)
            command_text = subprocess.list2cmdline(
                automation_command(workday_only=workday_only, random_delay_minutes=random_delay_minutes, mode=key)
            )
            command = [
                "schtasks",
                "/Create",
                "/TN",
                task_name,
                "/TR",
                command_text,
                "/SC",
                "DAILY",
                "/ST",
                trigger_time,
                "/F",
            ]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
            outputs.append({"task": task_name, "ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
            ok = ok and (result.returncode == 0 or task_missing_result(result))
        self.send_json(
            {
                "ok": ok,
                "stdout": "\n".join(item["stdout"] for item in outputs),
                "stderr": "\n".join(item["stderr"] for item in outputs),
                "outputs": outputs,
                "task": get_task_info(),
            }
        )

    def delete_task(self) -> None:
        outputs = []
        ok = True
        for task_name in [meta["name"] for meta in TASKS.values()] + LEGACY_TASK_NAMES:
            result = subprocess.run(
                ["schtasks", "/Delete", "/TN", task_name, "/F"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
            )
            outputs.append({"task": task_name, "ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
            ok = ok and result.returncode == 0
        self.send_json({"ok": ok, "outputs": outputs, "task": get_task_info()})

    def set_task_enabled(self, enabled: bool) -> None:
        action = "/Enable" if enabled else "/Disable"
        outputs = []
        ok = True
        for meta in TASKS.values():
            result = subprocess.run(
                ["schtasks", "/Change", "/TN", meta["name"], action],
                cwd=ROOT,
                text=True,
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
            )
            outputs.append({"task": meta["name"], "ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
            ok = ok and result.returncode == 0
        self.send_json(
            {
                "ok": ok,
                "outputs": outputs,
                "task": get_task_info(),
            }
        )

    def open_target(self, target: str) -> None:
        if target == "logs":
            path = LOG_DIR
        elif target == "screenshots":
            path = ROOT / "screenshots"
        elif target == "templates":
            path = TEMPLATE_DIR
        else:
            self.send_json({"ok": False, "message": "未知目标目录"}, status=HTTPStatus.BAD_REQUEST)
            return
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)
        self.send_json({"ok": True})

    def upload_template(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        boundary_token = "boundary="
        if boundary_token not in content_type:
            self.send_json({"ok": False, "message": "上传请求缺少 boundary"}, status=HTTPStatus.BAD_REQUEST)
            return
        boundary_value = content_type.split(boundary_token, 1)[1].split(";", 1)[0].strip().strip('"')
        boundary = ("--" + boundary_value).encode("utf-8")
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        fields = parse_multipart(raw, boundary)
        key = fields.get("key", b"").decode("utf-8", errors="ignore")
        image = fields.get("file")
        if key not in TEMPLATE_STEPS:
            self.send_json({"ok": False, "message": "未知模板步骤"}, status=HTTPStatus.BAD_REQUEST)
            return
        if not image:
            self.send_json({"ok": False, "message": "未收到模板图片"}, status=HTTPStatus.BAD_REQUEST)
            return
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        path = TEMPLATE_DIR / TEMPLATE_STEPS[key]["file"]
        path.write_bytes(image)
        try:
            load_template(path)
        except Exception as exc:
            path.unlink(missing_ok=True)
            self.send_json({"ok": False, "message": f"模板图片无法识别：{exc}"}, status=HTTPStatus.BAD_REQUEST)
            return
        self.send_json({"ok": True, "template": template_payload(key)})

    def capture_current_screen(self) -> None:
        hwnd, started = ensure_any_scrcpy_window(timeout=20)
        try:
            frame = capture_window(hwnd)
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(CURRENT_SCREENSHOT), frame):
                raise RuntimeError("保存截图失败")
            width = int(frame.shape[1])
            height = int(frame.shape[0])
            url = f"/api/screenshot-file?t={int(CURRENT_SCREENSHOT.stat().st_mtime)}"
            self.send_json(
                {
                    "ok": True,
                    "message": "已截图当前页面",
                    "url": url,
                    "width": width,
                    "height": height,
                    "scrcpy_started": started,
                }
            )
        finally:
            if started:
                close_window(hwnd)

    def test_template(self, payload: dict) -> None:
        key = str(payload.get("key") or "")
        threshold = float(payload.get("threshold") or 0.86)
        if key not in TEMPLATE_STEPS:
            self.send_json({"ok": False, "message": "未知模板步骤"}, status=HTTPStatus.BAD_REQUEST)
            return
        path = template_path(key)
        if not path.exists():
            self.send_json({"ok": False, "message": "模板图片不存在"}, status=HTTPStatus.BAD_REQUEST)
            return
        hwnd, started = ensure_any_scrcpy_window(timeout=20)
        try:
            frame = capture_window(hwnd)
            match = find_template(frame, load_template(path), threshold=threshold)
            if not match:
                self.send_json({"ok": False, "message": "未识别到模板", "template": template_payload(key)})
                return
            relative_x, relative_y = match.center_relative
            self.send_json(
                {
                    "ok": True,
                    "message": "已识别到模板",
                    "score": match.score,
                    "relative": [relative_x, relative_y],
                    "box": {"x": match.x, "y": match.y, "width": match.width, "height": match.height},
                    "template": template_payload(key),
                }
            )
        finally:
            if started:
                pass

    def click_template(self, payload: dict) -> None:
        key = str(payload.get("key") or "")
        threshold = float(payload.get("threshold") or 0.86)
        timeout = float(payload.get("timeout") or 25)
        if key not in TEMPLATE_STEPS:
            self.send_json({"ok": False, "message": "未知模板步骤"}, status=HTTPStatus.BAD_REQUEST)
            return
        path = template_path(key)
        if not path.exists():
            self.send_json({"ok": False, "message": "模板图片不存在"}, status=HTTPStatus.BAD_REQUEST)
            return
        hwnd, started = ensure_any_scrcpy_window(timeout=20)
        try:
            if TEMPLATE_STEPS[key].get("action") == "verify":
                match = wait_template(hwnd, path, threshold=threshold, timeout=timeout)
                relative_x, relative_y = match.center_relative
                self.send_json(
                    {
                        "ok": True,
                        "message": "已识别到确认模板",
                        "score": match.score,
                        "relative": [relative_x, relative_y],
                        "template": template_payload(key),
                    }
                )
                return
            match, clicked_at = wait_click_template(hwnd, path, threshold=threshold, timeout=timeout)
            relative_x, relative_y = match.center_relative
            self.send_json(
                {
                    "ok": True,
                    "message": "已识别并点击模板",
                    "score": match.score,
                    "relative": [relative_x, relative_y],
                    "screen": [clicked_at[0], clicked_at[1]],
                    "template": template_payload(key),
                }
            )
        finally:
            if started:
                pass

    def serve_template_file(self, key: str) -> None:
        if key not in TEMPLATE_STEPS:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = template_path(key)
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def serve_screenshot_file(self) -> None:
        if not CURRENT_SCREENSHOT.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(CURRENT_SCREENSHOT.read_bytes())

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
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def with_json_errors(self, action) -> None:
        try:
            action()
        except Exception as exc:
            self.send_json({"ok": False, "message": f"服务器处理失败：{exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args) -> None:
        return


def existing_panel_url(port: int = DEFAULT_PORT) -> str:
    url = f"http://127.0.0.1:{port}/api/ping"
    try:
        with urllib.request.urlopen(url, timeout=0.3) as response:
            body = response.read(4096).decode("utf-8", errors="ignore")
            if response.status == 200 and '"app": "OK-DingTalk"' in body:
                return f"http://127.0.0.1:{port}/"
    except (OSError, urllib.error.URLError):
        return ""
    return ""


def find_free_port(start: int = DEFAULT_PORT) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", start))
            return start
        except OSError as exc:
            raise RuntimeError(f"端口 {start} 已被占用，但没有检测到可复用的 OK-DingTalk 面板") from exc


def start_web_panel(open_browser: bool = True) -> tuple[ThreadingHTTPServer, str]:
    existing_url = existing_panel_url()
    if existing_url:
        if open_browser:
            webbrowser.open(existing_url)
        raise SystemExit(0)

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
