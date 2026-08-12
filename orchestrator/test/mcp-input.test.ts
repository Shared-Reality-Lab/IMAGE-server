import { afterEach, describe, expect, it, vi } from "vitest";
import sharp from "sharp";
import { prepareImageRequest } from "../src/mcp-input";

async function pixelPng() {
    const bytes = await sharp({ create: { width: 1, height: 1, channels: 3, background: "#ffffff" } }).png().toBuffer();
    return `data:image/png;base64,${bytes.toString("base64")}`;
}

describe("prepareImageRequest", () => {
    afterEach(() => vi.unstubAllGlobals());

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

    it.each(["jpeg", "webp"] as const)("accepts and normalizes a valid %s image", async format => {
        const image = sharp({ create: { width: 2, height: 3, channels: 3, background: "#ffffff" } });
        const bytes = await image[format]().toBuffer();
        const result = await prepareImageRequest({ graphic: `data:image/${format};base64,${bytes.toString("base64")}` });

        expect(result.dimensions).toEqual([2, 3]);
    });

    it("rejects a declared MIME type that does not match the decoded image", async () => {
        const jpeg = await sharp({ create: { width: 1, height: 1, channels: 3, background: "#fff" } }).jpeg().toBuffer();
        await expect(prepareImageRequest({ graphic: `data:image/png;base64,${jpeg.toString("base64")}` })).rejects.toThrow("MIME type");
    });

    it("downloads a ChatGPT file over HTTPS and rejects unsafe or failed downloads", async () => {
        const png = await sharp({ create: { width: 2, height: 1, channels: 3, background: "#fff" } }).png().toBuffer();
        const fetchMock = vi.fn().mockResolvedValue(new Response(png, { headers: { "content-length": String(png.length) } }));
        vi.stubGlobal("fetch", fetchMock);

        const result = await prepareImageRequest({ file: { download_url: "https://files.example/image.png", file_id: "file_test" } });
        expect(result.dimensions).toEqual([2, 1]);
        expect(fetchMock).toHaveBeenCalledWith(new URL("https://files.example/image.png"), expect.objectContaining({ signal: expect.any(AbortSignal) }));

        await expect(prepareImageRequest({ file: { download_url: "http://files.example/image.png", file_id: "file_test" } })).rejects.toThrow("HTTPS");
        fetchMock.mockResolvedValueOnce(new Response("missing", { status: 404 }));
        await expect(prepareImageRequest({ file: { download_url: "https://files.example/missing.png", file_id: "file_test" } })).rejects.toThrow("Unable to download");
    });

    it("rejects malformed, unsupported, and ambiguous sources", async () => {
        await expect(prepareImageRequest({ graphic: "data:image/png;base64,invalid" })).rejects.toThrow("base64");
        const graphic = await pixelPng();
        await expect(prepareImageRequest({ graphic, file: { download_url: "https://files.example/image.png", file_id: "file_test" } })).rejects.toThrow("exactly one");
        await expect(prepareImageRequest({ graphic, language: "eng" })).rejects.toThrow("two-letter");
    });
});
