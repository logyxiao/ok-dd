const state = { currentTab: "dashboard", poll: null, lastProcessRunning: false, uploadingTemplate: false, testSteps: {} };

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
  if (!res.ok) {
    const text = await res.text();
    try {
      const data = JSON.parse(text);
      throw new Error(data.message || text);
    } catch (error) {
      if (error instanceof SyntaxError) throw new Error(text);
      throw error;
    }
  }
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

function renderTaskRows(task) {
  const tasks = task?.tasks || {};
  const order = ["morning", "evening"];
  const body = $("taskRows");
  body.innerHTML = order.map((key) => {
    const item = tasks[key] || {};
    return `
      <tr>
        <td>${escapeHtml(item.label || key)}</td>
        <td><span class="${statusClass(item.enabled === false ? "跳过" : "成功")}">${escapeHtml(zhTaskState(item))}</span></td>
        <td>${escapeHtml(item.next_run || "无")}</td>
        <td>${escapeHtml(item.last_run || "无")}</td>
        <td>${escapeHtml(zhTaskResult(item.last_result))}</td>
      </tr>
    `;
  }).join("");
}

function templateCard(item) {
  const image = item.exists
    ? `<img src="${item.url}" alt="${escapeHtml(item.label)}" />`
    : `<div class="template-empty">未上传模板</div>`;
  const actionLabel = item.action === "verify" ? "等待识别" : "等待并点击";
  const actionNote = item.action === "verify" ? "验证模板" : "点击模板";
  return `
    <article class="template-card" data-template-key="${item.key}">
      <div class="template-preview">${image}</div>
      <div class="template-info">
        <h3>${escapeHtml(item.label)}</h3>
        <p>${escapeHtml(item.file)} · ${actionNote} · ${item.exists ? "已配置" : "未配置"}</p>
      </div>
      <div class="template-actions">
        <label class="upload-button">
          上传模板
          <input type="file" accept="image/*" data-upload-template="${item.key}" />
        </label>
        <button class="secondary" data-test-template="${item.key}" ${item.exists ? "" : "disabled"}>测试识别</button>
        <button class="primary" data-click-template="${item.key}" ${item.exists ? "" : "disabled"}>${actionLabel}</button>
      </div>
      <div class="template-result" id="templateResult-${item.key}">等待操作</div>
    </article>
  `;
}

function renderTemplates(templates) {
  const grid = $("templateGrid");
  if (!grid) return;
  const groups = [
    ["morning", "上班打卡模板"],
    ["evening", "下班打卡模板"],
  ];
  grid.innerHTML = groups.map(([mode, title]) => {
    const items = (templates || []).filter((item) => item.mode === mode);
    return `
      <section class="template-group">
        <div class="template-group-head">
          <h3>${title}</h3>
          <span>${items.filter((item) => item.exists).length}/${items.length} 已配置</span>
        </div>
        <div class="template-group-grid">
          ${items.map(templateCard).join("")}
        </div>
      </section>
    `;
  }).join("");
}

function renderTestSteps(stepsByMode) {
  state.testSteps = stepsByMode || {};
  const list = $("stepTestList");
  if (!list) return;
  const mode = $("stepTestMode")?.value || "evening";
  const steps = state.testSteps[mode] || [];
  list.innerHTML = steps.map((item) => {
    const clickLabel = item.action === "verify" ? "等待确认" : "识别并点击";
    const clickClass = item.action === "verify" ? "secondary" : "primary";
    const disabled = item.exists ? "" : "disabled";
    return `
      <article class="step-card" data-step-key="${item.key}">
        <div class="step-index">${item.index}</div>
        <div class="step-main">
          <h3>${escapeHtml(item.label)}</h3>
          <p>${escapeHtml(item.file)} · ${item.action === "verify" ? "只验证成功状态" : "点击步骤"} · ${item.exists ? "模板已配置" : "缺少模板"}</p>
        </div>
        <div class="step-actions">
          <button class="ghost" data-step-action="capture" data-step-key="${item.key}">截图</button>
          <button class="secondary" data-step-action="test" data-step-key="${item.key}" ${disabled}>只识别</button>
          <button class="${clickClass}" data-step-action="click" data-step-key="${item.key}" ${disabled}>${clickLabel}</button>
        </div>
        <div class="step-result" id="stepResult-${item.key}">等待测试</div>
      </article>
    `;
  }).join("") || `<section class="panel"><div class="screen-empty">暂无测试步骤</div></section>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function refresh(options = {}) {
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
  renderTaskRows(task);
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
  if (options.forceTemplates || state.currentTab !== "templates") {
    renderTemplates(data.templates || []);
  }
  if (options.forceSteps || state.currentTab !== "step-test") {
    renderTestSteps(data.test_steps || {});
  }
}

async function refreshProcess() {
  const process = await api("/api/process");
  $("dashboardOutput").textContent = process.output || "暂无输出";
  $("runOutput").textContent = process.output || "暂无输出";
  setText("runState", process.running ? "运行中" : "空闲");
  setText("detailRunning", process.running ? `正在执行，开始时间：${process.started_at || "未知"}` : "未在执行");
  setDisabled("stopRun", !process.running);
  if (state.lastProcessRunning && !process.running) {
    refresh();
  }
  state.lastProcessRunning = Boolean(process.running);
}

async function runAction(dryRun = false) {
  const payload = {
    workday_only: dryRun,
    keep_scrcpy: $("runKeepScrcpy").checked,
    dry_run: dryRun,
    mode: "auto",
  };
  const data = await api("/api/run", { method: "POST", body: JSON.stringify(payload) });
  toast(data.message || "已启动");
  refreshProcess();
}

async function runSelectedMode() {
  const payload = {
    workday_only: false,
    keep_scrcpy: $("runKeepScrcpy")?.checked || false,
    dry_run: false,
    mode: $("stepTestMode").value || "evening",
  };
  const data = await api("/api/run", { method: "POST", body: JSON.stringify(payload) });
  toast(data.message || "已启动");
  refreshProcess();
}

async function installTask() {
  const payload = {
    morning_time: $("morningTime").value || "09:00",
    evening_time: $("eveningTime").value || "18:30",
    random_window_minutes: Number($("randomWindowMinutes").value || 5),
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
    "step-test": ["测试步骤", "按正式流程逐步识别、截图和点击"],
    schedule: ["自动计划", "安装、更新或删除自动计划"],
    templates: ["模板识别", "上传小图、测试识别，并等待目标出现后点击"],
    logs: ["操作日志", "查看脚本运行、跳过、失败和点击步骤"],
  };
  setText("pageTitle", titles[tab][0]);
  setText("pageSubtitle", titles[tab][1]);
  if (tab === "templates") {
    refresh({ forceTemplates: true });
  }
  if (tab === "step-test") {
    refresh({ forceSteps: true });
  }
}

async function openFolder(target) {
  await api(`/api/open?target=${target}`);
  toast("已打开目录");
}

function templatePayload(key) {
  return {
    key,
    threshold: Number($("templateThreshold").value || 0.86),
    timeout: Number($("templateTimeout").value || 25),
  };
}

function stepPayload(key, action) {
  return {
    key,
    action,
    mode: $("stepTestMode").value || "evening",
    threshold: Number($("stepTemplateThreshold").value || 0.86),
    timeout: Number($("stepTemplateTimeout").value || 25),
    fresh: $("stepFreshStart").checked,
  };
}

function setTemplateResult(key, message) {
  const el = $(`templateResult-${key}`);
  if (el) el.textContent = message;
}

function setStepResult(key, message, status = "") {
  const el = $(`stepResult-${key}`);
  if (!el) return;
  el.textContent = message;
  el.classList.toggle("success", status === "success");
  el.classList.toggle("failed", status === "failed");
}

async function uploadTemplate(key, file) {
  state.uploadingTemplate = true;
  setTemplateResult(key, "正在上传模板...");
  const form = new FormData();
  form.append("key", key);
  form.append("file", file);
  try {
    const res = await fetch("/api/upload-template", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const message = data.message || "上传失败";
      setTemplateResult(key, message);
      toast(message);
      return;
    }
    setTemplateResult(key, "模板已上传，可以测试识别");
    toast("模板已上传");
    refresh({ forceTemplates: true });
  } catch (error) {
    const message = `上传失败：${error.message || error}`;
    setTemplateResult(key, message);
    toast(message);
  } finally {
    state.uploadingTemplate = false;
  }
}

async function testTemplate(key) {
  setTemplateResult(key, "正在识别...");
  const data = await api("/api/test-template", { method: "POST", body: JSON.stringify(templatePayload(key)) });
  if (!data.ok) {
    const best = typeof data.best_score === "number" ? `，最佳相似度 ${data.best_score.toFixed(3)}` : "";
    const scale = typeof data.scale === "number" ? `，缩放 ${data.scale.toFixed(2)}` : "";
    setTemplateResult(key, `${data.message || "未识别到模板"}${best}${scale}`);
    toast(data.message || "未识别到模板");
    return;
  }
  const relative = data.relative || [0, 0];
  const scale = typeof data.scale === "number" ? `，缩放 ${data.scale.toFixed(2)}` : "";
  setTemplateResult(key, `识别成功：相似度 ${data.score.toFixed(3)}${scale}，中心相对坐标 ${relative[0].toFixed(4)},${relative[1].toFixed(4)}`);
  toast("识别成功");
}

async function clickTemplate(key) {
  setTemplateResult(key, "等待模板出现...");
  const data = await api("/api/click-template", { method: "POST", body: JSON.stringify(templatePayload(key)) });
  if (!data.ok) {
    setTemplateResult(key, data.message || "操作失败");
    toast(data.message || "操作失败");
    return;
  }
  if (data.screen) {
    const scale = typeof data.scale === "number" ? `，缩放 ${data.scale.toFixed(2)}` : "";
    setTemplateResult(key, `已点击：相似度 ${data.score.toFixed(3)}${scale}，屏幕坐标 ${data.screen[0]},${data.screen[1]}`);
    toast("已识别并点击");
  } else {
    const relative = data.relative || [0, 0];
    const scale = typeof data.scale === "number" ? `，缩放 ${data.scale.toFixed(2)}` : "";
    setTemplateResult(key, `识别成功：相似度 ${data.score.toFixed(3)}${scale}，中心相对坐标 ${relative[0].toFixed(4)},${relative[1].toFixed(4)}`);
    toast("识别成功");
  }
}

async function captureCurrentScreen() {
  setText("screenCaptureStatus", "正在截图当前页面...");
  const preview = $("screenPreview");
  if (preview) {
    preview.innerHTML = `<div class="screen-empty">正在读取 scrcpy 画面...</div>`;
  }
  try {
    const data = await api("/api/capture-current-screen", { method: "POST", body: "{}" });
    if (!data.ok) {
      setText("screenCaptureStatus", data.message || "截图失败");
      toast(data.message || "截图失败");
      return;
    }
    if (preview) {
      preview.innerHTML = `<img src="${data.url}" alt="当前程序截图" />`;
    }
    const startedText = data.scrcpy_started ? "，已临时启动并关闭 scrcpy" : "";
    setText("screenCaptureStatus", `截图时间：${new Date().toLocaleString("zh-CN")}，尺寸：${data.width}×${data.height}${startedText}`);
    toast("已截图当前页面");
  } catch (error) {
    const message = `截图失败：${error.message || error}`;
    setText("screenCaptureStatus", message);
    if (preview) {
      preview.innerHTML = `<div class="screen-empty">${escapeHtml(message)}</div>`;
    }
    toast(message);
  }
}

async function captureStepScreen() {
  setText("stepScreenStatus", "正在截图当前页面...");
  const preview = $("stepScreenPreview");
  if (preview) {
    preview.innerHTML = `<div class="screen-empty">正在读取手机画面...</div>`;
  }
  try {
    const data = await api("/api/capture-current-screen", { method: "POST", body: "{}" });
    if (!data.ok) {
      setText("stepScreenStatus", data.message || "截图失败");
      toast(data.message || "截图失败");
      return;
    }
    renderStepScreenshot(data);
    toast("已截图当前页面");
  } catch (error) {
    const message = `截图失败：${error.message || error}`;
    setText("stepScreenStatus", message);
    if (preview) {
      preview.innerHTML = `<div class="screen-empty">${escapeHtml(message)}</div>`;
    }
    toast(message);
  }
}

function renderStepScreenshot(data) {
  const preview = $("stepScreenPreview");
  if (!preview || !data.url) return;
  preview.innerHTML = `<img src="${data.url}" alt="测试步骤截图" />`;
  const startedText = data.scrcpy_started ? "，已临时启动 scrcpy" : "";
  setText("stepScreenStatus", `截图时间：${new Date().toLocaleString("zh-CN")}，尺寸：${data.width}×${data.height}${startedText}`);
}

async function runStepAction(key, action) {
  setStepResult(key, action === "click" ? "等待模板出现..." : action === "test" ? "正在识别..." : "正在截图...");
  try {
    const data = await api("/api/test-step-action", { method: "POST", body: JSON.stringify(stepPayload(key, action)) });
    if (!data.ok) {
      const best = typeof data.best_score === "number" ? `，最佳相似度 ${data.best_score.toFixed(3)}` : "";
      const scale = typeof data.scale === "number" ? `，缩放 ${data.scale.toFixed(2)}` : "";
      setStepResult(key, `${data.message || "操作失败"}${best}${scale}`, "failed");
      toast(data.message || "操作失败");
      return;
    }
    if (action === "capture") {
      renderStepScreenshot(data);
      setStepResult(key, `${data.message}：${data.width}×${data.height}`, "success");
      toast("已截图");
      return;
    }
    const relative = data.relative || [0, 0];
    const score = typeof data.score === "number" ? data.score.toFixed(3) : "--";
    const scale = typeof data.scale === "number" ? `，缩放 ${data.scale.toFixed(2)}` : "";
    if (data.screen) {
      setStepResult(key, `已点击：相似度 ${score}${scale}，相对坐标 ${relative[0].toFixed(4)},${relative[1].toFixed(4)}，屏幕坐标 ${data.screen[0]},${data.screen[1]}`, "success");
      toast("已识别并点击");
      return;
    }
    setStepResult(key, `${data.message}：相似度 ${score}${scale}，相对坐标 ${relative[0].toFixed(4)},${relative[1].toFixed(4)}`, "success");
    toast(data.message || "步骤成功");
  } catch (error) {
    const message = error.message || String(error);
    setStepResult(key, message, "failed");
    toast(message);
  }
}

async function openDingTalkForStepTest() {
  setText("stepTestStatus", "正在打开钉钉...");
  try {
    const data = await api("/api/test-step-action", {
      method: "POST",
      body: JSON.stringify({
        action: "open-dingtalk",
        mode: $("stepTestMode").value || "evening",
        fresh: $("stepFreshStart").checked,
      }),
    });
    setText("stepTestStatus", data.message || "已打开钉钉");
    toast(data.message || "已打开钉钉");
  } catch (error) {
    const message = error.message || String(error);
    setText("stepTestStatus", message);
    toast(message);
  }
}

async function checkUnlockForStepTest() {
  setText("stepTestStatus", "正在检查屏幕锁定状态...");
  try {
    const data = await api("/api/test-step-action", {
      method: "POST",
      body: JSON.stringify({
        action: "check-unlock",
        mode: $("stepTestMode").value || "evening",
      }),
    });
    const manual = data.manual_required ? "，仍需手动解锁" : "";
    setText("stepTestStatus", `${data.message || "检查完成"}${manual}`);
    toast(data.manual_required ? "仍需手动解锁" : "屏幕状态正常");
  } catch (error) {
    const message = error.message || String(error);
    setText("stepTestStatus", message);
    toast(message);
  }
}

function bind() {
  document.querySelectorAll(".nav-item[data-tab]").forEach((el) => el.addEventListener("click", () => switchTab(el.dataset.tab)));
  document.querySelectorAll("[data-open]").forEach((el) => el.addEventListener("click", () => openFolder(el.dataset.open)));
  document.querySelectorAll("[data-copy-output]").forEach((el) => el.addEventListener("click", () => copyOutput(el.dataset.copyOutput)));
  $("openLogs").addEventListener("click", () => openFolder("logs"));
  $("openShots").addEventListener("click", () => openFolder("screenshots"));
  $("openTemplates").addEventListener("click", () => openFolder("templates"));
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
  $("captureScreen").addEventListener("click", captureCurrentScreen);
  $("stepCheckUnlock").addEventListener("click", checkUnlockForStepTest);
  $("stepOpenDingTalk").addEventListener("click", openDingTalkForStepTest);
  $("stepCaptureScreen").addEventListener("click", captureStepScreen);
  $("stepRunFull").addEventListener("click", runSelectedMode);
  $("stepTestMode").addEventListener("change", () => renderTestSteps(state.testSteps));

  document.addEventListener("change", (event) => {
    const key = event.target?.dataset?.uploadTemplate;
    if (!key || !event.target.files?.[0]) return;
    uploadTemplate(key, event.target.files[0]).finally(() => {
      event.target.value = "";
    });
  });
  document.addEventListener("click", (event) => {
    const testKey = event.target?.dataset?.testTemplate;
    const clickKey = event.target?.dataset?.clickTemplate;
    const stepKey = event.target?.dataset?.stepKey;
    const stepAction = event.target?.dataset?.stepAction;
    if (testKey) testTemplate(testKey);
    if (clickKey) clickTemplate(clickKey);
    if (stepKey && stepAction) runStepAction(stepKey, stepAction);
  });
}

bind();
refresh();
setInterval(refreshProcess, 1500);
setInterval(refresh, 30000);
