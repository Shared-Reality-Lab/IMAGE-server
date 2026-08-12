import { JSDOM } from "jsdom";
import axe from "axe-core";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AUDIO_EXPERIENCE_HTML } from "../src/mcp-app";

function loadApp() {
    const pause = vi.fn();
    const load = vi.fn();
    const play = vi.fn().mockResolvedValue(undefined);
    const dom = new JSDOM(AUDIO_EXPERIENCE_HTML, {
        runScripts: "dangerously",
        url: "https://image.example/app",
        beforeParse(window) {
            Object.defineProperties(window.HTMLMediaElement.prototype, {
                pause: { configurable: true, value: pause },
                load: { configurable: true, value: load },
                play: { configurable: true, value: play }
            });
            window.parent.postMessage = vi.fn();
        }
    });
    return { dom, window: dom.window, document: dom.window.document, pause, load, play };
}

function notify(window: JSDOM["window"], method: string, params: unknown) {
    window.dispatchEvent(new window.MessageEvent("message", {
        source: window,
        data: { jsonrpc: "2.0", method, params }
    }));
}

afterEach(() => vi.restoreAllMocks());

describe("IMAGE audio MCP App", () => {
    it("renders text-only, no-rendering, and tool-error states as untrusted text", () => {
        const { dom, window, document } = loadApp();

        notify(window, "ui/notifications/tool-result", { structuredContent: { text: ["A chart <script>alert(1)</script>"], audio: [] } });
        expect(document.getElementById("text-section")?.hidden).toBe(false);
        expect(document.getElementById("text")?.textContent).toContain("A chart <script>alert(1)</script>");
        expect(document.querySelector("#text script")).toBeNull();
        expect(document.getElementById("status")?.textContent).toContain("No audio rendering");

        notify(window, "ui/notifications/tool-result", { structuredContent: { text: [], audio: [] } });
        expect(document.getElementById("status")?.textContent).toContain("did not produce");

        notify(window, "ui/notifications/tool-result", { isError: true, content: [{ type: "text", text: "Decoder failed" }] });
        expect(document.getElementById("error")?.textContent).toBe("Decoder failed");
        expect(document.getElementById("error")?.hidden).toBe(false);
        dom.window.close();
    });

    it("renders mixed and multiple audio experiences with segment and Stop controls", async () => {
        const { dom, window, document, play, pause } = loadApp();
        notify(window, "ui/notifications/tool-result", { structuredContent: {
            text: ["Visible description"],
            audio: [
                { description: "Overview", artifactUrl: "https://image.example/one.mp3", timepoints: [] },
                { description: "Details", artifactUrl: "https://image.example/two.mp3", timepoints: [{ name: "First bar", offset: 2, duration: 1 }] }
            ]
        } });

        expect(document.querySelectorAll("audio")).toHaveLength(2);
        expect(document.querySelectorAll("button")).toHaveLength(5);
        expect(document.querySelectorAll("a[download]")).toHaveLength(2);
        expect(document.getElementById("status")?.textContent).toContain("Text and audio");
        const segment = [...document.querySelectorAll("button")].find(button => button.textContent === "First bar")!;
        segment.click();
        await Promise.resolve();
        expect(play).toHaveBeenCalled();
        expect(document.getElementById("status")?.textContent).toBe("Playing First bar.");
        const stop = [...document.querySelectorAll("button")].find(button => button.textContent === "Stop audio")!;
        stop.click();
        expect(pause).toHaveBeenCalled();
        expect(stop.hasAttribute("aria-pressed")).toBe(false);
        const playToggle = [...document.querySelectorAll("button")].find(button => button.textContent === "Play audio")!;
        expect(playToggle.getAttribute("aria-pressed")).toBe("false");
        dom.window.close();
    });

    it("announces expired audio and releases media on cancellation and teardown", () => {
        const { dom, window, document, pause, load } = loadApp();
        notify(window, "ui/notifications/tool-result", { structuredContent: {
            text: [],
            audio: [{ description: "Audio", artifactUrl: "https://image.example/audio.mp3", timepoints: [] }]
        } });
        const audio = document.querySelector("audio")!;
        audio.dispatchEvent(new window.Event("error"));
        expect(document.getElementById("error")?.textContent).toContain("missing, expired, or unavailable");

        notify(window, "ui/notifications/tool-cancelled", {});
        expect(document.getElementById("status")?.textContent).toContain("cancelled");
        expect(audio.hasAttribute("src")).toBe(false);
        expect(pause).toHaveBeenCalled();
        expect(load).toHaveBeenCalled();

        notify(window, "ui/resource-teardown", {});
        dom.window.close();
    });

    it("initializes the portable bridge and applies host locale direction", () => {
        const { dom, window, document } = loadApp();
        const postMessage = vi.mocked(window.parent.postMessage);
        expect(postMessage).toHaveBeenCalledWith(expect.objectContaining({ method: "ui/initialize" }), "*");

        window.dispatchEvent(new window.MessageEvent("message", {
            source: window,
            data: { jsonrpc: "2.0", id: 1, result: { hostContext: { locale: "ar" } } }
        }));
        expect(document.documentElement.lang).toBe("ar");
        expect(document.documentElement.dir).toBe("rtl");
        expect(postMessage).toHaveBeenCalledWith(expect.objectContaining({ method: "ui/notifications/initialized" }), "*");
        dom.window.close();
    });

    it("has no automated accessibility violations in a mixed rendering", async () => {
        const { dom, window, document } = loadApp();
        notify(window, "ui/notifications/tool-result", { structuredContent: {
            text: ["A concise interpretation."],
            audio: [{ description: "Audio interpretation", artifactUrl: "https://image.example/audio.mp3", timepoints: [{ name: "Introduction", offset: 0, duration: 1 }] }]
        } });

        const result = await axe.run(document.documentElement, { rules: { "color-contrast": { enabled: false } } });
        expect(result.violations).toEqual([]);
        dom.window.close();
    });
});
