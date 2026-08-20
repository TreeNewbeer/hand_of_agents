const nodesElement = document.querySelector("#nodes");
const toastElement = document.querySelector("#toast");
const keyDialog = document.querySelector("#key-dialog");
const keyInput = document.querySelector("#api-key");
const pinDialog = document.querySelector("#pin-dialog");
let nodes = [];
let authMode = "api_key";
let selectedPin = null;
let pinConfigDirty = false;
const IDLE_REFRESH_MS = 2000;
const ACTIVE_PULSE_REFRESH_MS = 500;

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
  if (mode === "unconfigured") return "FREE";
  if (mode === "input") return `IN · ${value ? "HIGH" : "LOW"}`;
  return `OUT · ${value ? "HIGH" : "LOW"}`;
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
            data-pin="${escapeHtml(pin.name)}" aria-label="${escapeHtml(pin.name)} Direction"
            ${node.connected ? "" : "disabled"}>
            <option value="" ${mode === "unconfigured" ? "selected" : ""}>Direction</option>
            <option value="input" ${mode === "input" ? "selected" : ""}>IN</option>
            <option value="output" ${mode === "output" ? "selected" : ""}>OUT</option>
          </select>
          <select class="pin-inline-select pin-level-select" data-node="${escapeHtml(node.node_id)}"
            data-pin="${escapeHtml(pin.name)}" aria-label="${escapeHtml(pin.name)} Level"
            ${node.connected && mode === "output" ? "" : "disabled"}>
            <option value="" ${mode !== "output" ? "selected" : ""}>Level</option>
            <option value="high" ${mode === "output" && behavior !== "pulse" && value ? "selected" : ""}>HIGH</option>
            <option value="low" ${mode === "output" && behavior !== "pulse" && !value ? "selected" : ""}>LOW</option>
            <option value="pulse" ${behavior === "pulse" ? "selected" : ""}>PULSE</option>
          </select>
          <button class="pin-release-button" data-node="${escapeHtml(node.node_id)}"
            data-pin="${escapeHtml(pin.name)}" type="button"
            ${node.connected && mode !== "unconfigured" ? "" : "disabled"}>释放</button>
          <button class="pin-advanced-button" data-node="${escapeHtml(node.node_id)}"
            data-pin="${escapeHtml(pin.name)}" type="button" ${node.connected ? "" : "disabled"}>高级</button>
        </span>
      </div>`;
  }
  const [label, kind] = FIXED_PINS[physical] ?? ["NC", "reserved"];
  return `
    <div class="header-pin fixed-header-pin ${kind}">
      <span class="pin-number">${physical}</span>
      <span class="pin-socket"></span>
      <span class="header-pin-copy"><strong>${label}</strong><small>${kind === "reserved" ? "RESERVED" : ""}</small></span>
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
        <span>RASPBERRY PI 40-PIN HEADER</span>
        <span class="pinout-legend">
          <i class="legend-in-low"></i>IN LOW
          <i class="legend-in-high"></i>IN HIGH
          <i class="legend-out-low"></i>OUT LOW
          <i class="legend-out-high"></i>OUT HIGH
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
        <div>
          <span class="connection-dot"></span>
          <span class="node-state">${node.connected ? "ONLINE" : "OFFLINE"}</span>
          <div class="node-identity-line">
            <h3>${escapeHtml(node.node_id)}</h3>
            <span class="node-ip">IP ${escapeHtml(node.metadata?.ip_address || "—")}</span>
          </div>
          <p>${escapeHtml(node.metadata?.model || "等待硬件信息")}</p>
        </div>
        <dl class="telemetry">
          <div><dt>温度</dt><dd>${system.temperature_c ?? "—"}°C</dd></div>
          <div><dt>负载</dt><dd>${system.load?.[0] ?? "—"}</dd></div>
          <div><dt>内存</dt><dd>${formatBytes(memoryUsed)}</dd></div>
        </dl>
      </header>
      ${node.pins?.length ? pinoutMarkup(node) : '<p class="empty-inline">等待 GPIO 清单…</p>'}
      <footer>最后状态：${escapeHtml(node.last_seen ? new Date(node.last_seen).toLocaleString() : "—")}</footer>
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
  document.querySelector("#last-refresh").textContent = new Date().toLocaleTimeString();
  nodesElement.innerHTML = nodes.length
    ? nodes.map(nodeMarkup).join("")
    : '<div class="empty-state">尚未发现节点，等待 Client 建立连接。</div>';
}

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
  const quickMenuActive = document.activeElement?.classList.contains("pin-inline-select");
  try {
    const response = await fetch("/api/v1/nodes", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    nodes = (await response.json()).nodes;
    status.textContent = authMode === "none" ? "LAN MODE · ONLINE" : "SECURE MODE · ONLINE";
    status.className = "status status-online";
    if (!quickMenuActive) render();
    if (pinDialog.open && selectedPin) updatePinDialog();
  } catch (error) {
    status.textContent = "SERVER OFFLINE";
    status.className = "status status-offline";
    showToast(`无法读取服务器：${error.message}`, true);
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
    throw new Error("服务器要求 API 密钥");
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
    throw new Error("PULSE 频率必须在 0.1 到 10 Hz 之间");
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

function updatePinDialog() {
  if (pinConfigDirty) return;
  const selected = findSelected();
  if (!selected) return;
  const { node, pin } = selected;
  const mode = modeFor(node, pin);
  const pull = node.state?.pin_pulls?.[pin.name] ?? pin.pull ?? "floating";
  const pulseHz = node.state?.pin_pulse_hz?.[pin.name] ?? 1;
  const behavior = node.state?.pin_behaviors?.[pin.name];
  const value = Boolean(node.state?.pins?.[pin.name]);
  const level = mode === "output" ? behavior === "pulse" ? "pulse" : value ? "high" : "low" : null;
  selectedPin.original = { mode, pull, level };
  selectedPin.pendingLevel = level;
  document.querySelector("#pin-dialog-title").textContent = `${pin.name} 高级设置`;
  document.querySelector("#pin-physical").textContent = `PHYSICAL PIN ${pin.physical} · BCM ${pin.bcm}`;
  document.querySelector("#pin-function").textContent = `${pin.default_function} · 当前 ${gpioStateLabel(node, pin)}`;
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
    showToast(`${pinName} 已切换为 ${direction === "input" ? "IN" : "OUT"}`);
  } catch (error) {
    showToast(`Direction 设置失败：${error.message}`, true);
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
    showToast(`${pinName} ${level.toUpperCase()} 成功`);
  } catch (error) {
    showToast(`Level 设置失败：${error.message}`, true);
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
    showToast(`${pinName} 已释放`);
  } catch (error) {
    showToast(`释放失败：${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

document.querySelector("#refresh-button").addEventListener("click", refresh);
document.querySelector("#settings-button").addEventListener("click", () => {
  keyInput.value = localStorage.getItem("hoa-api-key") ?? "";
  keyDialog.showModal();
});
document.querySelector("#key-form").addEventListener("submit", (event) => {
  if (event.submitter?.id !== "save-key") return;
  event.preventDefault();
  localStorage.setItem("hoa-api-key", keyInput.value);
  keyDialog.close();
  showToast("API 密钥已保存");
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
    showToast(`${pinName} 设置已生效`);
  } catch (error) {
    showToast(`配置失败：${error.message}`, true);
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
nodesElement.addEventListener("click", (event) => {
  const releaseButton = event.target.closest(".pin-release-button");
  const button = event.target.closest(".pin-advanced-button");
  if (releaseButton) releasePin(releaseButton);
  if (button) openPinDialog(button);
});

await loadSettings();
await refresh();
async function refreshLoop() {
  await refresh();
  window.setTimeout(refreshLoop, refreshDelayMs());
}
window.setTimeout(refreshLoop, refreshDelayMs());
