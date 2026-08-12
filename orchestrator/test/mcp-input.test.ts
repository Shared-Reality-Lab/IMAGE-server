import { describe, expect, it } from "vitest";
import sharp from "sharp";
import { prepareImageRequest } from "../src/mcp-input";

async function pixelPng() {
    const bytes = await sharp({ create: { width: 1, height: 1, channels: 3, background: "#ffffff" } }).png().toBuffer();
    return `data:image/png;base64,${bytes.toString("base64")}`;
}

describe("prepareImageRequest", () => {
    it("normalizes a valid image and synthesizes an IMAGE request", async () => {
        const graphic = await pixelPng();
        const result = await prepareImageRequest({ graphic, context: "A test image." });

        expect(result).toMatchObject({
            graphic: expect.stringMatching(/^data:image\/jpeg;base64,/),
            dimensions: [1, 1],
            language: "en",
            context: "A test image."
        });
    });

    it("rejects malformed, unsupported, and ambiguous sources", async () => {
        await expect(prepareImageRequest({ graphic: "data:image/png;base64,invalid" })).rejects.toThrow("base64");
        const graphic = await pixelPng();
        await expect(prepareImageRequest({ graphic, file: { download_url: "https://files.example/image.png" } })).rejects.toThrow("exactly one");
        await expect(prepareImageRequest({ graphic, language: "eng" })).rejects.toThrow("two-letter");
    });
});
