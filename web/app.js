const state = { currentTab: "dashboard", poll: null };

const $ = (id) => document.getElementById(id);

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2400);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value ?? "--";
}

function setDisabled(id, disabled) {
  const el = $(id);
  if (el) el.disabled = Boolean(disabled);
}

async function copyOutput(targetId) {
  const text = $(targetId)?.textContent || "";
  if (!text || text === "暂无输出") {
    toast("暂无可复制的输出");
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    toast("输出已复制");
  } catch (_error) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
    toast("输出已复制");
  }
}

function statusClass(status) {
  return `status-pill status-${statusKey(status)}`;
}

function statusKey(status) {
  const map = {
    "成功": "success",
    "失败": "failed",
    "跳过": "skipped",
    "检查": "dry-run",
    "开始": "started",
    success: "success",
    failed: "failed",
    skipped: "skipped",
    "dry-run": "dry-run",
    started: "started",
    unknown: "unknown",
  };
  return map[status] || String(status || "").replaceAll("_", "-");
}

function zhStatus(status) {
  const map = {
    success: "成功",
    failed: "失败",
    skipped: "跳过",
    "dry-run": "检查",
    started: "开始",
    unknown: "未知",
  };
  return map[status] || status || "";
}

function zhEvent(event) {
  const map = {
    offwork_sequence: "下班打卡序列",
    click_step: "点击步骤",
    raw: "原始日志",
  };
  return map[event] || event || "";
}

function zhMessage(message) {
  const map = {
    "click sequence would run": "今天会执行点击序列",
    "not a China workday": "今天不是中国工作日",
    "click sequence started": "点击序列已开始",
    "offwork sequence completed": "下班打卡序列已完成",
    completed: "已完成",
  };
  return map[message] || message || "";
}

function zhTaskState(task) {
  if (!task?.installed) return "未安装";
  if (task.enabled === false || task.state === "Disabled") return "已暂停";
  const map = {
    Ready: "已启用",
    Running: "正在运行",
    Queued: "已排队",
    Unknown: "未知",
  };
  return map[task.state] || "已启用";
}

function zhTaskResult(result) {
  if (result === "" || result === undefined || result === null) return "无";
  if (String(result) === "0") return "成功";
  return `结果码 ${result}`;
}

function renderRows(targetId, logs, limit) {
  const rows = (logs || []).slice(-(limit || logs.length)).reverse();
  const body = $(targetId);
  body.innerHTML = rows.map((item) => `
    <tr>
      <td>${escapeHtml(item.time || "")}</td>
      <td><span class="${statusClass(item.status)}">${escapeHtml(zhStatus(item.status))}</span></td>
      <td>${escapeHtml(zhEvent(item.event))}</td>
      <td>${escapeHtml(zhMessage(item.message))}</td>
    </tr>
  `).join("") || `<tr><td colspan="4" class="empty">暂无日志</td></tr>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function refresh() {
  const data = await api("/api/status");
  const s = data.state || {};
  const task = data.task || {};
  const process = data.process || {};

  setText("todayDone", data.completed_today ? "是" : "否");
  setText("lastCompleted", `上次完成：${s.last_completed_at || "无"}`);
  setText("workdayWillRun", data.workday?.will_run ? "会执行" : "会跳过");
  setText("workdayDesc", data.workday?.description || "--");
  setText("taskInstalled", `自动计划：${zhTaskState(task)}`);
  setText("nextRun", task.next_run || "无");
  setText("lastStatus", zhStatus(s.last_status) || "无");
  setText("lastMessage", zhMessage(s.last_message) || "暂无状态");
  setText("sidebarStatus", data.completed_today ? "今日已完成" : "今日未完成");
  setText("detailInstalled", task.installed ? "已安装" : "未安装");
  setText("detailEnabled", zhTaskState(task));
  setText("detailNext", task.next_run || "无");
  setText("detailLast", task.last_run || "无");
  setText("detailResult", zhTaskResult(task.last_result));
  setText("detailRunning", process.running ? `正在执行，开始时间：${process.started_at || "未知"}` : "未在执行");
  setText("scheduleStatus", `${zhTaskState(task)} · ${process.running ? "脚本正在执行" : "脚本空闲"}`);
  setText("runState", process.running ? "运行中" : "空闲");
  setDisabled("pauseTask", !task.installed || task.enabled === false);
  setDisabled("resumeTask", !task.installed || task.enabled !== false);
  setDisabled("deleteTask", !task.installed);
  setDisabled("stopRun", !process.running);

  const output = process.output || "暂无输出";
  $("dashboardOutput").textContent = output;
  $("runOutput").textContent = output;
  setText("logCount", (data.logs || []).length);
  renderRows("recentLogRows", data.logs || [], 8);
  renderRows("allLogRows", data.logs || [], 200);
}

async function refreshProcess() {
  const process = await api("/api/process");
  $("dashboardOutput").textContent = process.output || "暂无输出";
  $("runOutput").textContent = process.output || "暂无输出";
  setText("runState", process.running ? "运行中" : "空闲");
  setText("detailRunning", process.running ? `正在执行，开始时间：${process.started_at || "未知"}` : "未在执行");
  setDisabled("stopRun", !process.running);
  if (!process.running) refresh();
}

async function runAction(dryRun = false) {
  const payload = {
    workday_only: dryRun,
    keep_scrcpy: $("runKeepScrcpy").checked,
    dry_run: dryRun,
  };
  const data = await api("/api/run", { method: "POST", body: JSON.stringify(payload) });
  toast(data.message || "已启动");
  refreshProcess();
}

async function installTask() {
  const payload = {
    time: $("scheduleTime").value || "18:05",
    workday_only: $("scheduleWorkdayOnly").checked,
  };
  const data = await api("/api/install-task", { method: "POST", body: JSON.stringify(payload) });
  toast(data.ok ? "自动执行已安装/更新" : (data.stderr || "安装失败"));
  refresh();
}

async function deleteTask() {
  if (!confirm("确认删除自动执行计划任务？")) return;
  const data = await api("/api/delete-task", { method: "POST", body: "{}" });
  toast(data.ok ? "自动执行已删除" : (data.stderr || "删除失败"));
  refresh();
}

async function setTaskPaused(paused) {
  const path = paused ? "/api/pause-task" : "/api/resume-task";
  const data = await api(path, { method: "POST", body: "{}" });
  toast(data.ok ? (paused ? "自动计划已暂停" : "自动计划已恢复") : (data.stderr || "操作失败"));
  refresh();
}

async function stopRun() {
  const data = await api("/api/stop-run", { method: "POST", body: "{}" });
  toast(data.message || (data.ok ? "已请求停止" : "停止失败"));
  refreshProcess();
}

async function shutdownPanel() {
  if (!confirm("确认退出 Web 面板服务？")) return;
  await api("/api/shutdown", { method: "POST", body: "{}" });
  document.body.innerHTML = '<div class="shutdown"><h1>面板已退出</h1><p>可以关闭这个浏览器标签页。</p></div>';
}

function switchTab(tab) {
  state.currentTab = tab;
  document.querySelectorAll(".tab-page").forEach((el) => el.classList.toggle("active", el.id === tab));
  document.querySelectorAll(".nav-item[data-tab]").forEach((el) => el.classList.toggle("active", el.dataset.tab === tab));
  const titles = {
    dashboard: ["用量仪表盘", "查看打卡状态、计划任务和最近执行记录"],
    run: ["执行控制", "手动运行、检查工作日和查看实时输出"],
    schedule: ["自动计划", "安装、更新或删除 Windows 计划任务"],
    logs: ["操作日志", "查看脚本运行、跳过、失败和点击步骤"],
  };
  setText("pageTitle", titles[tab][0]);
  setText("pageSubtitle", titles[tab][1]);
}

async function openFolder(target) {
  await api(`/api/open?target=${target}`);
  toast("已打开目录");
}

function bind() {
  document.querySelectorAll(".nav-item[data-tab]").forEach((el) => el.addEventListener("click", () => switchTab(el.dataset.tab)));
  document.querySelectorAll("[data-open]").forEach((el) => el.addEventListener("click", () => openFolder(el.dataset.open)));
  document.querySelectorAll("[data-copy-output]").forEach((el) => el.addEventListener("click", () => copyOutput(el.dataset.copyOutput)));
  $("openLogs").addEventListener("click", () => openFolder("logs"));
  $("openShots").addEventListener("click", () => openFolder("screenshots"));
  $("shutdownPanel").addEventListener("click", shutdownPanel);
  $("refreshBtn").addEventListener("click", refresh);
  $("refreshLogs").addEventListener("click", refresh);
  $("quickRunBtn").addEventListener("click", () => runAction(false));
  $("dashRun").addEventListener("click", () => runAction(false));
  $("dashDry").addEventListener("click", () => runAction(true));
  $("runNow").addEventListener("click", () => runAction(false));
  $("dryRun").addEventListener("click", () => runAction(true));
  $("stopRun").addEventListener("click", stopRun);
  $("installTask").addEventListener("click", installTask);
  $("pauseTask").addEventListener("click", () => setTaskPaused(true));
  $("resumeTask").addEventListener("click", () => setTaskPaused(false));
  $("runFromSchedule").addEventListener("click", () => runAction(false));
  $("deleteTask").addEventListener("click", deleteTask);
}

bind();
refresh();
setInterval(refreshProcess, 1500);
setInterval(refresh, 30000);
