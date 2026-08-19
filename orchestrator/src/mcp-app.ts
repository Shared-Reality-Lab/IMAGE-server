const IMAGE_LOGO_DATA_URL = "data:image/png;base64,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";

// The canonical IMAGE-browser icon is embedded so sandboxed hosts do not fetch it.
export const AUDIO_EXPERIENCE_HTML = `<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMAGE audio experience</title>
<style>
:root { color-scheme: light dark; font: 16px/1.5 system-ui, sans-serif; }
body { margin: 0; background: Canvas; color: CanvasText; }
main { box-sizing: border-box; max-width: 44rem; margin: auto; padding: max(1rem, env(safe-area-inset-top)) max(1rem, env(safe-area-inset-right)) max(1rem, env(safe-area-inset-bottom)) max(1rem, env(safe-area-inset-left)); }
h1 { font-size: 1.25rem; margin: 0 0 .75rem; }
audio { display: block; width: 100%; margin: .75rem 0; }
button, a { box-sizing: border-box; min-height: 44px; min-width: 44px; }
button { margin: .25rem .5rem .25rem 0; padding: .5rem .75rem; }
a { display: inline-flex; align-items: center; }
button:focus-visible, a:focus-visible { outline: 3px solid Highlight; outline-offset: 3px; }
.brand { display: flex; gap: .75rem; align-items: center; }
.logo { flex: none; width: 7.5rem; height: 3rem; object-fit: contain; }
.muted { color: GrayText; }
.error { font-weight: 600; }
.interpretation { white-space: pre-wrap; }
.visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (forced-colors: active) { button, a { forced-color-adjust: auto; } }
</style>
</head>
<body>
<main>
<div class="brand">
<img class="logo" src="${IMAGE_LOGO_DATA_URL}" alt="McGill IMAGE logo">
<h1>IMAGE interpretation</h1>
</div>
<p id="status" role="status" aria-live="polite">Waiting for an IMAGE interpretation.</p>
<p id="error" class="error" role="alert" hidden></p>
<div id="text-section" hidden>
<div id="text"></div>
</div>
<div id="experiences"></div>
<p class="muted">Brought to you by the <a id="project-link" href="https://image.a11y.mcgill.ca" target="_blank" rel="noopener">McGill IMAGE project</a>.</p>
</main>
<script>
(() => {
  const status = document.getElementById("status");
  const error = document.getElementById("error");
  const textSection = document.getElementById("text-section");
  const text = document.getElementById("text");
  const experiences = document.getElementById("experiences");
  const players = [];
  let nextRequestId = 1;

  function send(method, params) {
    window.parent.postMessage({ jsonrpc: "2.0", id: nextRequestId++, method, params }, "*");
  }

  function announceError(message) {
    error.textContent = message;
    error.hidden = false;
  }

  function release() {
    for (const player of players.splice(0)) {
      if (player.timer) window.clearTimeout(player.timer);
      player.audio.pause();
      player.audio.removeAttribute("src");
      player.audio.load();
    }
  }

  function clear() {
    release();
    experiences.replaceChildren();
    text.replaceChildren();
    textSection.hidden = true;
    error.hidden = true;
    error.textContent = "";
    status.classList.remove("visually-hidden");
  }

  function renderText(values) {
    const items = Array.isArray(values) ? values.filter(value => typeof value === "string" && value.length) : [];
    textSection.hidden = !items.length;
    for (const value of items) {
      const paragraph = document.createElement("p");
      paragraph.className = "interpretation";
      paragraph.textContent = value;
      text.appendChild(paragraph);
    }
    return items.length;
  }

  function renderAudio(item, index) {
    if (!item || typeof item.artifactUrl !== "string") return false;
    const section = document.createElement("div");
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    audio.src = item.artifactUrl;
    audio.setAttribute("aria-label", "Audio interpretation " + (index + 1));
    const download = document.createElement("a");
    download.href = item.artifactUrl;
    download.download = "";
    download.textContent = "Download audio";
    download.setAttribute("aria-label", "Download audio interpretation " + (index + 1));
    const segments = document.createElement("div");
    segments.setAttribute("aria-label", "Audio interpretation " + (index + 1) + " segments");
    const player = { audio, timer: undefined };
    players.push(player);

    function stop(message) {
      if (player.timer) window.clearTimeout(player.timer);
      player.timer = undefined;
      audio.pause();
      audio.currentTime = 0;
      if (message) status.textContent = message;
    }

    audio.addEventListener("error", () => announceError("This audio artifact is missing, expired, or unavailable."));
    for (const point of Array.isArray(item.timepoints) ? item.timepoints : []) {
      if (typeof point?.name !== "string" || !Number.isFinite(point.offset) || point.offset < 0 || !Number.isFinite(point.duration) || point.duration < 0) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = point.name;
      button.addEventListener("click", () => {
        if (player.timer) window.clearTimeout(player.timer);
        audio.currentTime = point.offset;
        audio.play().catch(() => announceError("Playback could not start. Use the audio controls."));
        player.timer = window.setTimeout(() => stop("Segment finished."), point.duration * 1000);
        status.textContent = "Playing " + point.name + ".";
      });
      segments.appendChild(button);
    }
    section.append(audio, segments, download);
    experiences.appendChild(section);
    return true;
  }

  function render(payload) {
    clear();
    if (payload?.isError) {
      const message = Array.isArray(payload.content) ? payload.content.find(item => item?.type === "text")?.text : undefined;
      announceError(typeof message === "string" ? message : "IMAGE could not produce an interpretation.");
      status.textContent = "The IMAGE request failed.";
      return;
    }
    const structured = payload?.structuredContent ?? payload ?? {};
    const hasText = renderText(structured.text);
    const audioItems = Array.isArray(structured.audio) ? structured.audio : [];
    const hasAudio = audioItems.map(renderAudio).some(Boolean);
    if (hasAudio || hasText) {
      status.textContent = "IMAGE experiences ready above";
      status.classList.add("visually-hidden");
    } else status.textContent = "IMAGE did not produce a usable interpretation.";
  }

  function applyHostContext(context) {
    const locale = context?.locale;
    if (typeof locale === "string" && locale) {
      document.documentElement.lang = locale;
      try { document.documentElement.dir = new Intl.Locale(locale).textInfo?.direction || "ltr"; } catch { document.documentElement.dir = "ltr"; }
    }
  }

  function renderChatGptOutput() {
    const openai = window.openai;
    const value = openai?.toolOutput
      ?? openai?.toolResponseMetadata?.mcp_tool_result
      ?? openai?.toolResponseMetadata?.call_tool_result;
    if (value !== undefined && value !== null) render(value);
  }

  window.addEventListener("message", event => {
    if (event.source !== window.parent || !event.data || event.data.jsonrpc !== "2.0") return;
    const message = event.data;
    if (message.id === 1 && message.result) {
      applyHostContext(message.result.hostContext);
      window.parent.postMessage({ jsonrpc: "2.0", method: "ui/notifications/initialized", params: {} }, "*");
      renderChatGptOutput();
      return;
    }
    if (message.method === "ui/notifications/tool-result") render(message.params);
    if (message.method === "ui/notifications/host-context-changed") applyHostContext(message.params);
    if (message.method === "ui/notifications/tool-cancelled") {
      release();
      status.classList.remove("visually-hidden");
      status.textContent = "The IMAGE request was cancelled.";
    }
    if (message.method === "ui/resource-teardown") release();
  });
  window.addEventListener("openai:set_globals", renderChatGptOutput);
  renderChatGptOutput();
  send("ui/initialize", {
    protocolVersion: "2026-01-26",
    appCapabilities: { availableDisplayModes: ["inline"] },
    clientInfo: { name: "image-audio-experience", version: "1.2.0" }
  });
})();
</script>
</body>
</html>`;
