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
h2 { font-size: 1rem; margin: 1rem 0 .5rem; }
audio { display: block; width: 100%; margin: .75rem 0; }
button, a { box-sizing: border-box; min-height: 44px; min-width: 44px; }
button { margin: .25rem .5rem .25rem 0; padding: .5rem .75rem; }
a { display: inline-flex; align-items: center; }
button:focus-visible, a:focus-visible { outline: 3px solid Highlight; outline-offset: 3px; }
.brand { display: flex; gap: .75rem; align-items: center; }
.logo { flex: none; width: 7.5rem; height: 3rem; }
.muted { color: GrayText; }
.error { font-weight: 600; }
.interpretation { white-space: pre-wrap; }
@media (forced-colors: active) { button, a { forced-color-adjust: auto; } }
</style>
</head>
<body>
<main>
<div class="brand">
<svg class="logo" role="img" aria-label="McGill IMAGE logo" viewBox="0 0 120 48" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="2" width="116" height="44" rx="8" fill="none" stroke="currentColor" stroke-width="4"/><text x="60" y="31" text-anchor="middle" fill="currentColor" font-family="system-ui, sans-serif" font-size="22" font-weight="700">IMAGE</text></svg>
<h1>IMAGE accessible interpretation</h1>
</div>
<p id="status" role="status" aria-live="polite">Waiting for an IMAGE interpretation.</p>
<p id="error" class="error" role="alert" hidden></p>
<section id="text-section" hidden>
<h2>Text interpretation</h2>
<div id="text"></div>
</section>
<div id="experiences"></div>
<p class="muted">Brought to you by the McGill IMAGE project. <a id="project-link" href="https://image.a11y.mcgill.ca" target="_blank" rel="noopener">Click here for more information.</a></p>
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
    const section = document.createElement("section");
    const heading = document.createElement("h2");
    heading.textContent = typeof item.description === "string" ? item.description : "Audio interpretation " + (index + 1);
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    audio.src = item.artifactUrl;
    const playButton = document.createElement("button");
    playButton.type = "button";
    playButton.textContent = "Play audio";
    playButton.setAttribute("aria-pressed", "false");
    const stopButton = document.createElement("button");
    stopButton.type = "button";
    stopButton.textContent = "Stop audio";
    const download = document.createElement("a");
    download.href = item.artifactUrl;
    download.download = "";
    download.textContent = "Download audio";
    const segments = document.createElement("div");
    segments.setAttribute("aria-label", "Audio segments");
    const player = { audio, timer: undefined };
    players.push(player);

    function stop(message) {
      if (player.timer) window.clearTimeout(player.timer);
      player.timer = undefined;
      audio.pause();
      audio.currentTime = 0;
      if (message) status.textContent = message;
    }

    playButton.addEventListener("click", () => {
      if (audio.paused) audio.play().catch(() => announceError("Playback could not start. Use the audio controls."));
      else audio.pause();
    });
    stopButton.addEventListener("click", () => stop("Audio stopped."));
    audio.addEventListener("play", () => {
      playButton.textContent = "Pause audio";
      playButton.setAttribute("aria-pressed", "true");
    });
    audio.addEventListener("pause", () => {
      playButton.textContent = "Play audio";
      playButton.setAttribute("aria-pressed", "false");
    });
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
    section.append(heading, audio, playButton, stopButton, document.createElement("br"), download, segments);
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
    if (hasAudio && hasText) status.textContent = "Text and audio interpretations are ready.";
    else if (hasAudio) status.textContent = "Audio interpretation ready.";
    else if (hasText) status.textContent = "No audio rendering was produced. The text interpretation is shown here and in the conversation.";
    else status.textContent = "IMAGE did not produce a usable interpretation.";
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
      status.textContent = "The IMAGE request was cancelled.";
    }
    if (message.method === "ui/resource-teardown") release();
  });
  window.addEventListener("openai:set_globals", renderChatGptOutput);
  renderChatGptOutput();
  send("ui/initialize", {
    protocolVersion: "2026-01-26",
    appCapabilities: { availableDisplayModes: ["inline"] },
    clientInfo: { name: "image-audio-experience", version: "1.1.0" }
  });
})();
</script>
</body>
</html>`;
