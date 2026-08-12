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
        await expect(fs.readFile(path.join(testPath, requestUuid, "mcp-audio", artifactPath.split("/")[1]))).resolves.toEqual(Buffer.from("test mp3"));
        expect(result.dropped).toEqual(["ca.mcgill.a11y.image.renderer.TactileSVG"]);
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
