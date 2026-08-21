import { createRenderGuard } from "./render-guard.js?v=1";

const nodesElement = document.querySelector("#nodes");
const toastElement = document.querySelector("#toast");
const keyDialog = document.querySelector("#key-dialog");
const keyInput = document.querySelector("#api-key");
const pinDialog = document.querySelector("#pin-dialog");
let nodes = [];
let authMode = "api_key";
let selectedPin = null;
let pinConfigDirty = false;
let currentLanguage = localStorage.getItem("hoa-language") === "zh" ? "zh" : "en";
const IDLE_REFRESH_MS = 2000;
const ACTIVE_PULSE_REFRESH_MS = 500;

const TRANSLATIONS = {
  en: {
    controlAuthorization: "CONTROL AUTHORIZATION",
    refreshNow: "Refresh Now",
    authSettings: "Auth Settings",
    systemSummary: "System summary",
    totalNodes: "Total Nodes",
    onlineNodes: "Online Nodes",
    activeOutputs: "Active Outputs",
    lastRefresh: "Last Refresh",
    noNodes: "No nodes found. Waiting for a Client connection.",
    setApiKey: "Set Agent API Key",
    apiKeyHelp: "No key is needed in LAN mode. When HOA_AUTH_MODE=api_key is enabled, the key is stored only in this browser and sent in request headers.",
    apiKey: "API Key",
    apiKeyPlaceholder: "Enter HOA_API_KEY",
    cancel: "Cancel",
    save: "Save",
    close: "Close",
    pinMode: "Pin Mode",
    unconfiguredRecommended: "Unconfigured (recommended)",
    input: "Input",
    output: "Output",
    inputPull: "Input Pull",
    floating: "Floating",
    pullUp: "Pull-up",
    pullDown: "Pull-down",
    pulseFrequency: "PULSE Frequency",
    outputLevel: "Output Level (applied on confirmation)",
    continuousPulse: "Continuous PULSE",
    pinWarning: "Changes in this dialog are staged locally and submitted only after confirmation. Before switching to output, verify that the external circuit permits the selected level.",
    confirm: "Confirm",
    connecting: "CONNECTING",
    lanOnline: "LAN MODE · ONLINE",
    secureOnline: "SECURE MODE · ONLINE",
    serverOffline: "SERVER OFFLINE",
    switchLanguage: "Switch to Chinese",
    languageButton: "ZH",
    direction: "Direction",
    level: "Level",
    inShort: "IN",
    outShort: "OUT",
    high: "HIGH",
    low: "LOW",
    pulse: "PULSE",
    release: "Release",
    advanced: "Advanced",
    reserved: "RESERVED",
    boardHeader: "RASPBERRY PI 40-PIN HEADER",
    inLow: "IN LOW",
    inHigh: "IN HIGH",
    outLow: "OUT LOW",
    outHigh: "OUT HIGH",
    online: "ONLINE",
    offline: "OFFLINE",
    name: "Name",
    ip: "IP",
    id: "ID",
    model: "Model",
    temperature: "Temperature",
    load: "Load",
    memory: "Memory",
    waitingHardware: "Waiting for hardware information",
    waitingPins: "Waiting for GPIO list…",
    free: "FREE",
    pinAdvancedTitle: "{pin} Advanced Settings",
    physicalPin: "PHYSICAL PIN {physical} · BCM {bcm}",
    currentFunction: "{function} · Current {state}",
    serverReadFailed: "Unable to read server: {error}",
    apiKeyRequired: "The server requires an API key",
    pulseRange: "PULSE frequency must be between 0.1 and 10 Hz",
    directionChanged: "{pin} switched to {direction}",
    directionFailed: "Direction update failed: {error}",
    levelSucceeded: "{pin} {level} succeeded",
    levelFailed: "Level update failed: {error}",
    released: "{pin} released",
    releaseFailed: "Release failed: {error}",
    renameTitle: "Node Name",
    renameHint: "Click to rename",
    nameLength: "Name must contain 1–64 characters",
    renamed: "Node renamed to {name}",
    renameFailed: "Rename failed: {error}",
    apiKeySaved: "API key saved",
    configApplied: "{pin} configuration applied",
    configFailed: "Configuration failed: {error}",
  },
  zh: {
    controlAuthorization: "控制授权",
    refreshNow: "立即刷新",
    authSettings: "认证设置",
    systemSummary: "系统摘要",
    totalNodes: "节点总数",
    onlineNodes: "在线节点",
    activeOutputs: "在线输出",
    lastRefresh: "最后刷新",
    noNodes: "尚未发现节点，等待 Client 建立连接。",
    setApiKey: "设置 Agent API 密钥",
    apiKeyHelp: "当前局域网模式无需填写。启用 HOA_AUTH_MODE=api_key 后，密钥仅保存在本浏览器并通过请求头发送。",
    apiKey: "API 密钥",
    apiKeyPlaceholder: "输入 HOA_API_KEY",
    cancel: "取消",
    save: "保存",
    close: "关闭",
    pinMode: "引脚模式",
    unconfiguredRecommended: "未占用（推荐）",
    input: "输入",
    output: "输出",
    inputPull: "输入上下拉",
    floating: "浮空",
    pullUp: "上拉",
    pullDown: "下拉",
    pulseFrequency: "PULSE 频率",
    outputLevel: "输出电平（确认后生效）",
    continuousPulse: "连续 PULSE",
    pinWarning: "弹窗内的修改仅暂存；点击“确认”后才会提交。切换为输出时，请先确认外部电路允许所选电平。",
    confirm: "确认",
    connecting: "正在连接",
    lanOnline: "局域网模式 · 在线",
    secureOnline: "安全模式 · 在线",
    serverOffline: "服务器离线",
    switchLanguage: "切换到英文",
    languageButton: "EN",
    direction: "方向",
    level: "电平",
    inShort: "输入",
    outShort: "输出",
    high: "高",
    low: "低",
    pulse: "脉冲",
    release: "释放",
    advanced: "高级",
    reserved: "保留",
    boardHeader: "树莓派 40 针排针",
    inLow: "输入低",
    inHigh: "输入高",
    outLow: "输出低",
    outHigh: "输出高",
    online: "在线",
    offline: "离线",
    name: "名称",
    ip: "IP",
    id: "ID",
    model: "型号",
    temperature: "温度",
    load: "负载",
    memory: "内存",
    waitingHardware: "等待硬件信息",
    waitingPins: "等待 GPIO 清单…",
    free: "空闲",
    pinAdvancedTitle: "{pin} 高级设置",
    physicalPin: "物理引脚 {physical} · BCM {bcm}",
    currentFunction: "{function} · 当前 {state}",
    serverReadFailed: "无法读取服务器：{error}",
    apiKeyRequired: "服务器要求 API 密钥",
    pulseRange: "PULSE 频率必须在 0.1 到 10 Hz 之间",
    directionChanged: "{pin} 已切换为{direction}",
    directionFailed: "方向设置失败：{error}",
    levelSucceeded: "{pin} {level} 设置成功",
    levelFailed: "电平设置失败：{error}",
    released: "{pin} 已释放",
    releaseFailed: "释放失败：{error}",
    renameTitle: "节点名称",
    renameHint: "点击重命名",
    nameLength: "名称必须为 1–64 个字符",
    renamed: "节点已重命名为 {name}",
    renameFailed: "重命名失败：{error}",
    apiKeySaved: "API 密钥已保存",
    configApplied: "{pin} 设置已生效",
    configFailed: "配置失败：{error}",
  },
};

function t(key, values = {}) {
  const template = TRANSLATIONS[currentLanguage][key] ?? TRANSLATIONS.en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? `{${name}}`));
}

const FIXED_PINS = {
  1: ["3V3", "power-3v3"], 2: ["5V", "power-5v"], 4: ["5V", "power-5v"],
  6: ["GND", "ground"], 9: ["GND", "ground"], 14: ["GND", "ground"],
  17: ["3V3", "power-3v3"], 20: ["GND", "ground"], 25: ["GND", "ground"],
  27: ["ID_SD", "reserved"], 28: ["ID_SC", "reserved"], 30: ["GND", "ground"],
  34: ["GND", "ground"], 39: ["GND", "ground"],
};

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
})[character]);

function applyLanguage(rerender = true) {
  document.documentElement.lang = currentLanguage === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
  const languageButton = document.querySelector("#language-button");
  languageButton.textContent = t("languageButton");
  languageButton.setAttribute("aria-label", t("switchLanguage"));
  const status = document.querySelector("#server-status");
  if (status.classList.contains("status-online")) {
    status.textContent = authMode === "none" ? t("lanOnline") : t("secureOnline");
  } else if (status.classList.contains("status-offline")) {
    status.textContent = t("serverOffline");
  } else {
    status.textContent = t("connecting");
  }
  if (rerender) renderGuard.requestRender();
  if (pinDialog.open && selectedPin) updatePinDialogText();
}

function showToast(message, isError = false) {
  toastElement.textContent = message;
  toastElement.classList.toggle("toast-error", isError);
  toastElement.classList.add("toast-visible");
  window.setTimeout(() => toastElement.classList.remove("toast-visible"), 2800);
}

function formatBytes(value) {
  if (!Number.isFinite(value)) return "—";
  return `${(value / (1024 ** 3)).toFixed(1)} GB`;
}

function modeFor(node, pin) {
  return node.state?.pin_modes?.[pin.name] ?? pin.direction ?? "unconfigured";
}

function pinByPhysical(node, physical) {
  return (node.pins ?? []).find((pin) => pin.physical === physical);
}

function gpioStateLabel(node, pin) {
  const mode = modeFor(node, pin);
  const value = node.state?.pins?.[pin.name];
  if (mode === "unconfigured") return t("free");
  const level = value ? t("high") : t("low");
  if (mode === "input") return `${t("inShort")} · ${level}`;
  return `${t("outShort")} · ${level}`;
}

function headerPinMarkup(node, physical) {
  const pin = pinByPhysical(node, physical);
  if (pin) {
    const mode = modeFor(node, pin);
    const value = node.state?.pins?.[pin.name];
    const behavior = node.state?.pin_behaviors?.[pin.name];
    const levelClass = mode === "unconfigured" ? "" : value ? "level-high" : "level-low";
    return `
      <div class="header-pin gpio-header-pin mode-${mode} ${levelClass}">
        <span class="pin-number">${physical}</span>
        <span class="pin-socket"></span>
        <span class="header-pin-copy">
          <strong>${escapeHtml(pin.name)}</strong>
          <small>${gpioStateLabel(node, pin)}</small>
        </span>
        <span class="pin-inline-actions">
          <select class="pin-inline-select pin-direction-select" data-node="${escapeHtml(node.node_id)}"
            data-pin="${escapeHtml(pin.name)}" aria-label="${escapeHtml(pin.name)} ${t("direction")}"
            ${node.connected ? "" : "disabled"}>
            <option value="" ${mode === "unconfigured" ? "selected" : ""}>${t("direction")}</option>
            <option value="input" ${mode === "input" ? "selected" : ""}>${t("inShort")}</option>
            <option value="output" ${mode === "output" ? "selected" : ""}>${t("outShort")}</option>
          </select>
          <select class="pin-inline-select pin-level-select" data-node="${escapeHtml(node.node_id)}"
            data-pin="${escapeHtml(pin.name)}" aria-label="${escapeHtml(pin.name)} ${t("level")}"
            ${node.connected && mode === "output" ? "" : "disabled"}>
            <option value="" ${mode !== "output" ? "selected" : ""}>${t("level")}</option>
            <option value="high" ${mode === "output" && behavior !== "pulse" && value ? "selected" : ""}>${t("high")}</option>
            <option value="low" ${mode === "output" && behavior !== "pulse" && !value ? "selected" : ""}>${t("low")}</option>
            <option value="pulse" ${behavior === "pulse" ? "selected" : ""}>${t("pulse")}</option>
          </select>
          <button class="pin-release-button" data-node="${escapeHtml(node.node_id)}"
            data-pin="${escapeHtml(pin.name)}" type="button"
            ${node.connected && mode !== "unconfigured" ? "" : "disabled"}>${t("release")}</button>
          <button class="pin-advanced-button" data-node="${escapeHtml(node.node_id)}"
            data-pin="${escapeHtml(pin.name)}" type="button" ${node.connected ? "" : "disabled"}>${t("advanced")}</button>
        </span>
      </div>`;
  }
  const [label, kind] = FIXED_PINS[physical] ?? ["NC", "reserved"];
  return `
    <div class="header-pin fixed-header-pin ${kind}">
      <span class="pin-number">${physical}</span>
      <span class="pin-socket"></span>
      <span class="header-pin-copy"><strong>${label}</strong><small>${kind === "reserved" ? t("reserved") : ""}</small></span>
    </div>`;
}

function pinoutMarkup(node) {
  const rows = [];
  for (let row = 0; row < 20; row += 1) {
    const odd = row * 2 + 1;
    rows.push(`<div class="header-row">${headerPinMarkup(node, odd)}${headerPinMarkup(node, odd + 1)}</div>`);
  }
  return `
    <div class="pinout-shell">
      <div class="board-caption">
        <span>${t("boardHeader")}</span>
        <span class="pinout-legend">
          <i class="legend-in-low"></i>${t("inLow")}
          <i class="legend-in-high"></i>${t("inHigh")}
          <i class="legend-out-low"></i>${t("outLow")}
          <i class="legend-out-high"></i>${t("outHigh")}
        </span>
      </div>
      <div class="pinout">${rows.join("")}</div>
    </div>`;
}

function nodeMarkup(node) {
  const system = node.state?.system ?? {};
  const memoryUsed = system.memory_total_bytes && system.memory_available_bytes
    ? system.memory_total_bytes - system.memory_available_bytes
    : null;
  return `
    <article class="node-card ${node.connected ? "" : "node-offline"}">
      <header class="node-header">
        <div class="node-primary-info">
          <span class="device-field">
            <span class="device-label">${t("name")}:</span>
            <button class="node-name-button" data-node="${escapeHtml(node.node_id)}"
              type="button" title="${t("renameHint")}">${escapeHtml(node.name || "Pi")}</button>
          </span>
          <span class="device-field">
            <span class="device-label">${t("id")}:</span>
            <strong>${escapeHtml(node.metadata?.serial || "—")}</strong>
          </span>
          <span class="device-field node-model">
            <span class="device-label">${t("model")}:</span>
            <strong>${escapeHtml(node.metadata?.model || t("waitingHardware"))}</strong>
          </span>
          <span class="node-connectivity">
            <span class="connection-dot"></span>
            <span class="node-state">${node.connected ? t("online") : t("offline")}</span>
          </span>
        </div>
        <div class="node-secondary-info">
          <span class="device-field">
            <span class="device-label">${t("ip")}:</span>
            <strong>${escapeHtml(node.metadata?.ip_address || "—")}</strong>
          </span>
          <dl class="telemetry">
            <div><dt>${t("temperature")}</dt><dd>${system.temperature_c ?? "—"}°C</dd></div>
            <div><dt>${t("load")}</dt><dd>${system.load?.[0] ?? "—"}</dd></div>
            <div><dt>${t("memory")}</dt><dd>${formatBytes(memoryUsed)}</dd></div>
          </dl>
        </div>
      </header>
      ${node.pins?.length ? pinoutMarkup(node) : `<p class="empty-inline">${t("waitingPins")}</p>`}
    </article>`;
}

function render() {
  const online = nodes.filter((node) => node.connected);
  const activeOutputs = online.flatMap((node) => (node.pins ?? []).filter(
    (pin) => modeFor(node, pin) === "output",
  ));
  document.querySelector("#node-count").textContent = nodes.length;
  document.querySelector("#online-count").textContent = online.length;
  document.querySelector("#output-count").textContent = activeOutputs.length;
  document.querySelector("#last-refresh").textContent = new Date().toLocaleTimeString(
    currentLanguage === "zh" ? "zh-CN" : "en-US",
  );
  nodesElement.innerHTML = nodes.length
    ? nodes.map(nodeMarkup).join("")
    : `<div class="empty-state">${t("noNodes")}</div>`;
}

const renderGuard = createRenderGuard(
  render,
  () => document.activeElement?.classList.contains("pin-inline-select"),
);

function refreshDelayMs() {
  const hasActivePulse = nodes.some((node) => Object.values(
    node.state?.pin_behaviors ?? {},
  ).includes("pulse"));
  return hasActivePulse ? ACTIVE_PULSE_REFRESH_MS : IDLE_REFRESH_MS;
}

async function loadSettings() {
  try {
    const response = await fetch("/api/v1/settings", { cache: "no-store" });
    if (response.ok) {
      authMode = (await response.json()).auth_mode;
      document.querySelector("#settings-button").hidden = authMode === "none";
    }
  } catch (_) {
    // The normal status refresh reports connectivity errors.
  }
}

async function refresh() {
  const status = document.querySelector("#server-status");
  try {
    const response = await fetch("/api/v1/nodes", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    nodes = (await response.json()).nodes;
    status.textContent = authMode === "none" ? t("lanOnline") : t("secureOnline");
    status.className = "status status-online";
    renderGuard.requestRender();
    if (pinDialog.open && selectedPin) updatePinDialog();
  } catch (error) {
    status.textContent = t("serverOffline");
    status.className = "status status-offline";
    showToast(t("serverReadFailed", { error: error.message }), true);
  }
}

async function apiCommand(nodeId, pinName, body, refreshAfter = true) {
  const headers = { "Content-Type": "application/json" };
  const apiKey = localStorage.getItem("hoa-api-key");
  if (apiKey) headers["X-API-Key"] = apiKey;
  const response = await fetch(
    `/api/v1/nodes/${encodeURIComponent(nodeId)}/pins/${encodeURIComponent(pinName)}`,
    { method: "POST", headers, body: JSON.stringify(body) },
  );
  const result = await response.json();
  if (response.status === 401) {
    keyDialog.showModal();
    throw new Error(t("apiKeyRequired"));
  }
  if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
  if (refreshAfter) {
    await refresh();
    pinConfigDirty = false;
    if (pinDialog.open) updatePinDialog();
  }
  return result;
}

function findSelected() {
  if (!selectedPin) return null;
  const node = nodes.find((item) => item.node_id === selectedPin.nodeId);
  const pin = node?.pins?.find((item) => item.name === selectedPin.pinName);
  return node && pin ? { node, pin } : null;
}

function pulseDurationMs(nodeId, pinName, frequencyOverride = null) {
  const node = nodes.find((item) => item.node_id === nodeId);
  const frequency = frequencyOverride ?? node?.state?.pin_pulse_hz?.[pinName] ?? 1;
  const numericFrequency = Number(frequency);
  if (!Number.isFinite(numericFrequency) || numericFrequency < 0.1 || numericFrequency > 10) {
    throw new Error(t("pulseRange"));
  }
  return Math.round(500 / numericFrequency);
}

function updateAdvancedLevelControls(mode, connected) {
  document.querySelectorAll(".pin-level-command").forEach((button) => {
    const selected = mode === "output" && button.dataset.level === selectedPin?.pendingLevel;
    button.classList.toggle("button-quiet", !selected);
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", String(selected));
    button.disabled = !connected || mode !== "output";
  });
}

function updatePinDialogText(selected = findSelected()) {
  if (!selected) return;
  const { node, pin } = selected;
  document.querySelector("#pin-dialog-title").textContent = t("pinAdvancedTitle", { pin: pin.name });
  document.querySelector("#pin-physical").textContent = t("physicalPin", {
    physical: pin.physical,
    bcm: pin.bcm,
  });
  document.querySelector("#pin-function").textContent = t("currentFunction", {
    function: pin.default_function,
    state: gpioStateLabel(node, pin),
  });
}

function updatePinDialog() {
  const selected = findSelected();
  if (!selected) return;
  updatePinDialogText(selected);
  if (pinConfigDirty) return;
  const { node, pin } = selected;
  const mode = modeFor(node, pin);
  const pull = node.state?.pin_pulls?.[pin.name] ?? pin.pull ?? "floating";
  const pulseHz = node.state?.pin_pulse_hz?.[pin.name] ?? 1;
  const behavior = node.state?.pin_behaviors?.[pin.name];
  const value = Boolean(node.state?.pins?.[pin.name]);
  const level = mode === "output" ? behavior === "pulse" ? "pulse" : value ? "high" : "low" : null;
  selectedPin.original = { mode, pull, level };
  selectedPin.pendingLevel = level;
  document.querySelector("#pin-mode").value = mode;
  document.querySelector("#pin-pull").value = pull;
  document.querySelector("#pin-pulse-hz").value = pulseHz;
  document.querySelector("#pin-pull").disabled = mode !== "input";
  document.querySelector("#apply-pin-config").disabled = !node.connected;
  updateAdvancedLevelControls(mode, node.connected);
}

function openPinDialog(button) {
  selectedPin = { nodeId: button.dataset.node, pinName: button.dataset.pin };
  pinConfigDirty = false;
  updatePinDialog();
  pinDialog.showModal();
}

async function runDirectionAction(select) {
  const { node: nodeId, pin: pinName } = select.dataset;
  const direction = select.value;
  if (!direction) return;
  select.blur();
  select.disabled = true;
  try {
    await apiCommand(nodeId, pinName, {
      action: "configure",
      direction,
      pull: "floating",
    });
    showToast(t("directionChanged", {
      pin: pinName,
      direction: direction === "input" ? t("input") : t("output"),
    }));
  } catch (error) {
    showToast(t("directionFailed", { error: error.message }), true);
  } finally {
    select.disabled = false;
  }
}

async function runLevelAction(select) {
  const { node: nodeId, pin: pinName } = select.dataset;
  const level = select.value;
  if (!level) return;
  select.blur();
  select.disabled = true;
  try {
    const body = level === "pulse"
      ? { action: "pulse", duration_ms: pulseDurationMs(nodeId, pinName), continuous: true }
      : { action: "set", value: level === "high" };
    await apiCommand(nodeId, pinName, body);
    showToast(t("levelSucceeded", { pin: pinName, level: t(level) }));
  } catch (error) {
    showToast(t("levelFailed", { error: error.message }), true);
  } finally {
    select.disabled = false;
  }
}

async function releasePin(button) {
  const { node: nodeId, pin: pinName } = button.dataset;
  button.disabled = true;
  try {
    await apiCommand(nodeId, pinName, {
      action: "configure",
      direction: "unconfigured",
    });
    showToast(t("released", { pin: pinName }));
  } catch (error) {
    showToast(t("releaseFailed", { error: error.message }), true);
  } finally {
    button.disabled = false;
  }
}

async function renameNode(button) {
  const nodeId = button.dataset.node;
  const currentName = nodes.find((node) => node.node_id === nodeId)?.name || "Pi";
  const requestedName = window.prompt(t("renameTitle"), currentName);
  if (requestedName === null) return;
  const name = requestedName.trim();
  if (!name || name.length > 64) {
    showToast(t("nameLength"), true);
    return;
  }
  const headers = { "Content-Type": "application/json" };
  const apiKey = localStorage.getItem("hoa-api-key");
  if (apiKey) headers["X-API-Key"] = apiKey;
  button.disabled = true;
  try {
    const response = await fetch(`/api/v1/nodes/${encodeURIComponent(nodeId)}/name`, {
      method: "POST",
      headers,
      body: JSON.stringify({ name }),
    });
    const result = await response.json();
    if (response.status === 401) {
      keyDialog.showModal();
      throw new Error(t("apiKeyRequired"));
    }
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    await refresh();
    showToast(t("renamed", { name }));
  } catch (error) {
    showToast(t("renameFailed", { error: error.message }), true);
  } finally {
    button.disabled = false;
  }
}

document.querySelector("#refresh-button").addEventListener("click", refresh);
document.querySelector("#language-button").addEventListener("click", () => {
  currentLanguage = currentLanguage === "en" ? "zh" : "en";
  localStorage.setItem("hoa-language", currentLanguage);
  applyLanguage();
});
document.querySelector("#settings-button").addEventListener("click", () => {
  keyInput.value = localStorage.getItem("hoa-api-key") ?? "";
  keyDialog.showModal();
});
document.querySelector("#key-form").addEventListener("submit", (event) => {
  if (event.submitter?.id !== "save-key") return;
  event.preventDefault();
  localStorage.setItem("hoa-api-key", keyInput.value);
  keyDialog.close();
  showToast(t("apiKeySaved"));
});
document.querySelector("#pin-mode").addEventListener("change", (event) => {
  pinConfigDirty = true;
  const mode = event.target.value;
  document.querySelector("#pin-pull").disabled = mode !== "input";
  if (mode === "output" && !selectedPin?.pendingLevel) selectedPin.pendingLevel = "low";
  updateAdvancedLevelControls(mode, findSelected()?.node.connected ?? false);
});
document.querySelector("#pin-pull").addEventListener("change", () => {
  pinConfigDirty = true;
});
document.querySelector("#pin-pulse-hz").addEventListener("input", () => {
  pinConfigDirty = true;
});
pinDialog.addEventListener("close", () => {
  selectedPin = null;
  pinConfigDirty = false;
});
document.querySelector("#apply-pin-config").addEventListener("click", async () => {
  if (!selectedPin) return;
  const { nodeId, pinName } = selectedPin;
  try {
    const pulseHz = Number(document.querySelector("#pin-pulse-hz").value);
    pulseDurationMs(nodeId, pinName, pulseHz);
    const direction = document.querySelector("#pin-mode").value;
    const level = selectedPin.pendingLevel ?? "low";
    const original = selectedPin.original ?? {};
    const needsLevelCommand = direction === "output" && (
      original.mode !== "output" || original.level !== level
    );
    const body = {
      action: "configure",
      direction,
      pull: document.querySelector("#pin-pull").value,
      pulse_hz: pulseHz,
    };
    await apiCommand(nodeId, pinName, body, !needsLevelCommand);
    if (needsLevelCommand) {
      const levelBody = level === "pulse"
        ? {
            action: "pulse",
            duration_ms: pulseDurationMs(nodeId, pinName, pulseHz),
            continuous: true,
          }
        : { action: "set", value: level === "high" };
      await apiCommand(nodeId, pinName, levelBody);
    }
    pinDialog.close();
    showToast(t("configApplied", { pin: pinName }));
  } catch (error) {
    showToast(t("configFailed", { error: error.message }), true);
  }
});
document.querySelectorAll(".pin-level-command").forEach((button) => {
  button.addEventListener("click", () => {
    if (!selectedPin) return;
    selectedPin.pendingLevel = button.dataset.level;
    pinConfigDirty = true;
    updateAdvancedLevelControls(
      document.querySelector("#pin-mode").value,
      findSelected()?.node.connected ?? false,
    );
  });
});
nodesElement.addEventListener("change", (event) => {
  const directionSelect = event.target.closest(".pin-direction-select");
  const levelSelect = event.target.closest(".pin-level-select");
  if (directionSelect) runDirectionAction(directionSelect);
  if (levelSelect) runLevelAction(levelSelect);
});
nodesElement.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || !event.target.closest?.("button, select")) return;
  renderGuard.beginInteraction(`pointer:${event.pointerId}`);
});
nodesElement.addEventListener("keydown", (event) => {
  if (event.repeat || !["Enter", " "].includes(event.key)) return;
  if (!event.target.closest?.("button, select")) return;
  renderGuard.beginInteraction(`key:${event.code}`);
});
nodesElement.addEventListener("focusout", (event) => {
  if (!event.target.classList?.contains("pin-inline-select")) return;
  window.setTimeout(() => renderGuard.flush(), 0);
});
nodesElement.addEventListener("click", (event) => {
  const nameButton = event.target.closest(".node-name-button");
  const releaseButton = event.target.closest(".pin-release-button");
  const button = event.target.closest(".pin-advanced-button");
  if (nameButton) renameNode(nameButton);
  if (releaseButton) releasePin(releaseButton);
  if (button) openPinDialog(button);
});
window.addEventListener("pointerup", (event) => {
  renderGuard.endInteraction(`pointer:${event.pointerId}`);
}, true);
window.addEventListener("pointercancel", (event) => {
  renderGuard.endInteraction(`pointer:${event.pointerId}`);
}, true);
window.addEventListener("keyup", (event) => {
  renderGuard.endInteraction(`key:${event.code}`);
}, true);
window.addEventListener("blur", () => renderGuard.cancelInteractions());

applyLanguage(false);
await loadSettings();
await refresh();
async function refreshLoop() {
  await refresh();
  window.setTimeout(refreshLoop, refreshDelayMs());
}
window.setTimeout(refreshLoop, refreshDelayMs());
