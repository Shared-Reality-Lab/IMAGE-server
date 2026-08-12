export const AUDIO_EXPERIENCE_HTML = `<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMAGE audio experience</title>
<style>
:root { color-scheme: light dark; font: 16px/1.5 system-ui, sans-serif; }
body { margin: 0; background: Canvas; color: CanvasText; }
main { box-sizing: border-box; max-width: 44rem; margin: auto; padding: 1rem; }
h1 { font-size: 1.25rem; margin: 0 0 .75rem; }
h2 { font-size: 1rem; margin: 1rem 0 .5rem; }
audio { display: block; width: 100%; margin: .75rem 0; }
button, a { min-height: 44px; min-width: 44px; }
button { margin: .25rem .5rem .25rem 0; padding: .5rem .75rem; }
button:focus-visible, a:focus-visible { outline: 3px solid Highlight; outline-offset: 3px; }
.muted { color: GrayText; }
.error { color: Mark; font-weight: 600; }
</style>
</head>
<body>
<main>
<h1>IMAGE audio experience</h1>
<p id="status" role="status" aria-live="polite">Waiting for an IMAGE interpretation.</p>
<section id="experience" hidden>
<h2 id="title">Audio interpretation</h2>
<audio id="audio" controls preload="metadata"></audio>
<p><a id="download" download>Download audio</a></p>
<div id="segments" aria-label="Audio segments"></div>
</section>
<p class="muted">Brought to you by the McGill IMAGE project. <a href="https://image.a11y.mcgill.ca" target="_blank" rel="noopener">Click here for more information.</a></p>
</main>
<script>
(() => {
  const status = document.getElementById("status");
  const experience = document.getElementById("experience");
  const title = document.getElementById("title");
  const audio = document.getElementById("audio");
  const download = document.getElementById("download");
  const segments = document.getElementById("segments");
  let stopTimer;

  function stop() {
    if (stopTimer) window.clearTimeout(stopTimer);
    stopTimer = undefined;
    audio.pause();
  }

  function render(payload) {
    const items = Array.isArray(payload?.audio) ? payload.audio : [];
    if (!items.length) {
      experience.hidden = true;
      status.textContent = payload?.text ? "No audio rendering was produced. Text appears in the conversation." : "No usable audio rendering was produced.";
      return;
    }
    const item = items[0];
    if (typeof item.artifactUrl !== "string") {
      experience.hidden = true;
      status.textContent = "The audio artifact is unavailable.";
      return;
    }
    experience.hidden = false;
    title.textContent = typeof item.description === "string" ? item.description : "Audio interpretation";
    audio.src = item.artifactUrl;
    download.href = item.artifactUrl;
    download.textContent = "Download audio";
    segments.replaceChildren();
    for (const point of Array.isArray(item.timepoints) ? item.timepoints : []) {
      if (typeof point?.name !== "string" || !Number.isFinite(point.offset) || !Number.isFinite(point.duration)) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = point.name;
      button.addEventListener("click", () => {
        stop();
        audio.currentTime = point.offset;
        audio.play().catch(() => { status.textContent = "Playback could not start. Use the audio controls."; });
        stopTimer = window.setTimeout(stop, point.duration * 1000);
        status.textContent = "Playing " + point.name + ".";
      });
      segments.appendChild(button);
    }
    status.textContent = "Audio interpretation ready.";
  }

  window.addEventListener("message", event => {
    if (event.source !== window.parent || !event.data || event.data.jsonrpc !== "2.0") return;
    const message = event.data;
    if (message.method === "ui/notifications/tool-result") render(message.params?.structuredContent ?? message.params);
    if (message.method === "ui/resource-teardown" || message.method === "ui/notifications/tool-cancelled") stop();
  });
})();
</script>
</body>
</html>`;
