let statusEvents = null;
let pollTimer = null;
let lastStatusAt = 0;

async function fetchStatus() {
  try {
    const response = await fetch("/status", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`status ${response.status}`);
    }
    updateStatus(await response.json());
  } catch {
    updateStatus({ state: "offline", round: 0, sequence: [], gesture: null, confidence: 0 });
  }
}

let movesRendered = false;
let cameraRetryTimer = null;

function refreshCameraFeed() {
  const cameraFeed = document.getElementById("camera-feed");
  cameraFeed.src = `/video?refresh=${Date.now()}`;
}

function scheduleCameraReconnect() {
  window.clearTimeout(cameraRetryTimer);
  cameraRetryTimer = window.setTimeout(refreshCameraFeed, 1000);
}

function updateStatus(status) {
  lastStatusAt = Date.now();
  renderStatus(status);
}

function startStatusStream() {
  if (!window.EventSource) {
    return false;
  }

  statusEvents = new EventSource("/events");
  statusEvents.onmessage = (event) => {
    try {
      updateStatus(JSON.parse(event.data));
    } catch {
      // Ignore malformed event payloads; polling fallback will recover.
    }
  };
  statusEvents.onerror = () => {
    statusEvents?.close();
    statusEvents = null;
    startPolling(350);
  };
  return true;
}

function startPolling(intervalMs = 500) {
  window.clearInterval(pollTimer);
  fetchStatus();
  pollTimer = window.setInterval(fetchStatus, intervalMs);
}

function renderStatus(status) {
  const liveGesture =
    status.gesture === "thumbs_up" || status.gesture === "thumbs_down"
      ? status.gesture
      : null;
  document.body.dataset.gesture = liveGesture ?? "none";

  document.getElementById("round").textContent = status.round ?? 0;
  const stateLabel =
    status.state === "preparing" && status.countdown !== null && status.countdown !== undefined
      ? `${formatLabel(status.state)} ${status.countdown}`
      : formatLabel(status.state ?? "unknown");
  document.getElementById("state").textContent = stateLabel;

  const confidence = Math.round((status.confidence ?? 0) * 100);
  const gesture = status.gesture ? `${formatLabel(status.gesture)} ${confidence}%` : "none";
  document.getElementById("gesture").textContent = gesture;
  document.getElementById("camera-status").textContent = status.camera_ready ? "live" : "waiting";
  const cameraBadge = document.getElementById("camera-badge");
  cameraBadge.textContent = gesture;
  cameraBadge.dataset.gesture = status.gesture ?? "none";

  const sequence = document.getElementById("sequence");
  sequence.replaceChildren(
    ...(status.sequence ?? []).map((move) => {
      const item = document.createElement("li");
      const isActive = move === status.active_move;
      const repeatLabel = isActive
        ? ` ${status.current_repeat ?? 0} / ${status.repeat_count ?? 1}`
        : "";
      item.textContent = `${move}${repeatLabel}`;
      item.classList.toggle("active", move === status.active_move);
      return item;
    }),
  );

  if (!movesRendered && status.moves) {
    renderMoves(status.moves);
    movesRendered = true;
  }
  document.querySelectorAll(".move-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.move === status.active_move);
  });

  document.querySelectorAll(".verdict").forEach((el) => {
    el.classList.remove("active", "detected");
  });
  const verdict = liveGesture ?? status.verdict ?? (status.state === "neutral" ? "neutral" : null);
  if (verdict) {
    const verdictCard = document.getElementById(verdict);
    verdictCard?.classList.add("active");
    if (liveGesture) {
      verdictCard?.classList.add("detected");
    }
  }
}

function renderMoves(moves) {
  const list = document.getElementById("moves-list");
  list.replaceChildren(
    ...Object.entries(moves).map(([name, description]) => {
      const item = document.createElement("article");
      item.className = "move-item";
      item.dataset.move = name;

      const title = document.createElement("strong");
      title.textContent = name;

      const detail = document.createElement("span");
      detail.textContent = description;

      item.append(title, detail);
      return item;
    }),
  );
}

function formatLabel(value) {
  return String(value).replaceAll("_", " ");
}

if (!startStatusStream()) {
  startPolling(350);
} else {
  fetchStatus();
  window.setInterval(() => {
    if (Date.now() - lastStatusAt > 1500) {
      fetchStatus();
    }
  }, 750);
}

document.getElementById("camera-feed").addEventListener("error", scheduleCameraReconnect);
setInterval(refreshCameraFeed, 15000);
