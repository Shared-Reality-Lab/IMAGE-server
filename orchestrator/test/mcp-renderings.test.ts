import fs from "fs/promises";
import path from "path";
import { afterEach, describe, expect, it } from "vitest";
import { convertRenderings } from "../src/mcp-renderings";

const requestUuid = "123e4567-e89b-42d3-a456-426614174001";
const audio = `data:audio/mpeg;base64,${Buffer.from("test mp3").toString("base64")}`;
const testPath = path.join("/tmp", "image-mcp-renderings-test");

afterEach(async () => {
    await fs.rm(testPath, { recursive: true, force: true });
});

describe("convertRenderings", () => {
    it("persists audio artifacts and preserves text and segment timepoints", async () => {
        const result = await convertRenderings(requestUuid, [
            { type_id: "ca.mcgill.a11y.image.renderer.Text", data: { text: "Description" } },
            {
                type_id: "ca.mcgill.a11y.image.renderer.SegmentAudio",
                description: "Segmented audio",
                data: { audioFile: audio, audioInfo: [{ name: "Elephant", offset: 1, duration: 2 }] }
            },
            { type_id: "ca.mcgill.a11y.image.renderer.TactileSVG", data: {} }
        ], testPath);

        expect(result.content).toHaveLength(2);
        expect(result.content[1].text).toContain("/mcp/audio/");
        expect(result.audio[0]).toMatchObject({ bytes: 8, timepoints: [{ name: "Elephant", offset: 1, duration: 2 }] });
        const artifactPath = String(result.audio[0].artifactPath).replace("/mcp/audio/", "");
        const filePath = path.join(testPath, requestUuid, "mcp-audio", artifactPath.split("/")[1]);
        await expect(fs.readFile(filePath)).resolves.toEqual(Buffer.from("test mp3"));
        expect((await fs.stat(filePath)).mode & 0o777).toBe(0o600);
        expect(JSON.stringify(result)).not.toContain("data:audio");
        expect(result.dropped).toEqual(["ca.mcgill.a11y.image.renderer.TactileSVG"]);
    });

    it("converts every supported rendering and drops invalid timepoints", async () => {
        const result = await convertRenderings(requestUuid, [
            { type_id: "ca.mcgill.a11y.image.renderer.Text", data: { text: "First" } },
            { type_id: "ca.mcgill.a11y.image.renderer.Text", data: { text: "Second" } },
            { type_id: "ca.mcgill.a11y.image.renderer.SimpleAudio", description: "Simple", data: { audio } },
            {
                type_id: "ca.mcgill.a11y.image.renderer.SegmentAudio",
                description: "Segments",
                data: { audioFile: audio, audioInfo: [
                    { name: "Valid", offset: 0, duration: 1 },
                    { name: "Infinite", offset: Number.POSITIVE_INFINITY, duration: 1 },
                    { name: "Negative", offset: 1, duration: -1 }
                ] }
            }
        ], testPath, "https://image.example");

        expect(result.content).toHaveLength(4);
        expect(result.audio).toHaveLength(2);
        expect(result.audio[0].artifactUrl).toMatch(/^https:\/\/image\.example\/mcp\/audio\//);
        expect(result.audio[1].timepoints).toEqual([{ name: "Valid", offset: 0, duration: 1 }]);
        expect(result.audio[0].artifactPath).not.toBe(result.audio[1].artifactPath);
    });

    it("handles empty and malformed rendering collections", async () => {
        await expect(convertRenderings(requestUuid, undefined, testPath)).resolves.toEqual({ content: [], audio: [], dropped: [] });
        const result = await convertRenderings(requestUuid, [
            {},
            { type_id: "ca.mcgill.a11y.image.renderer.Text", data: { text: 42 } },
            { type_id: "ca.mcgill.a11y.image.renderer.SegmentAudio", data: {} }
        ], testPath);

        expect(result.content).toEqual([]);
        expect(result.audio).toEqual([]);
        expect(result.dropped).toEqual(["unknown", "ca.mcgill.a11y.image.renderer.Text", "ca.mcgill.a11y.image.renderer.SegmentAudio"]);
    });

    it("drops malformed audio rather than exposing its data URL", async () => {
        const result = await convertRenderings(requestUuid, [
            { type_id: "ca.mcgill.a11y.image.renderer.SimpleAudio", data: { audio: "data:audio/mpeg;base64,not-base64" } }
        ], testPath);

        expect(result.audio).toEqual([]);
        expect(result.content).toEqual([]);
        expect(result.dropped).toEqual(["ca.mcgill.a11y.image.renderer.SimpleAudio"]);
    });
});
