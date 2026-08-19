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
<img class="logo" src="https://image.a11y.mcgill.ca/images/logo.png" alt="McGill IMAGE logo">
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
