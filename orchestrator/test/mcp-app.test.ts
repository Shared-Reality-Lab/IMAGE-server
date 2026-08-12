import { describe, expect, it } from "vitest";
import { AUDIO_EXPERIENCE_HTML } from "../src/mcp-app";

describe("IMAGE audio MCP App", () => {
    it("uses semantic controls and the standard tool-result bridge", () => {
        expect(AUDIO_EXPERIENCE_HTML).toContain("<audio id=\"audio\" controls");
        expect(AUDIO_EXPERIENCE_HTML).toContain("ui/notifications/tool-result");
        expect(AUDIO_EXPERIENCE_HTML).toContain("ui/initialize");
        expect(AUDIO_EXPERIENCE_HTML).toContain("ui/notifications/initialized");
        expect(AUDIO_EXPERIENCE_HTML).toContain("window.openai?.toolOutput");
        expect(AUDIO_EXPERIENCE_HTML).toContain("openai:set_globals");
        expect(AUDIO_EXPERIENCE_HTML).toContain("ui/resource-teardown");
        expect(AUDIO_EXPERIENCE_HTML).toContain("aria-live=\"polite\"");
        expect(AUDIO_EXPERIENCE_HTML).toContain("https://image.a11y.mcgill.ca");
    });
});
