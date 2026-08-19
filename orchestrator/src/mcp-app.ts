const IMAGE_LOGO_DATA_URL = "data:image/png;base64,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";

// The bundled IMAGE logo is embedded so sandboxed hosts do not fetch it.
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
