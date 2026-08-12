import fs from "fs/promises";
import path from "path";
import express from "express";
import request from "supertest";
import { afterEach, describe, expect, it } from "vitest";
import { mcpAudioHandler } from "../src/mcp-audio";

const basePath = path.join("/tmp", "image-mcp-audio-test");
const uuid = "123e4567-e89b-42d3-a456-426614174002";
const token = "A".repeat(43);

function app() {
    const server = express();
    server.get("/mcp/audio/:uuid/:token.mp3", mcpAudioHandler(basePath));
    return server;
}

afterEach(async () => {
    await fs.rm(basePath, { recursive: true, force: true });
});

describe("MCP audio artifacts", () => {
    it("streams MP3 artifacts with byte-range support", async () => {
        const directory = path.join(basePath, uuid, "mcp-audio");
        await fs.mkdir(directory, { recursive: true });
        await fs.writeFile(path.join(directory, `${token}.mp3`), "abcdefghij");

        const response = await request(app()).get(`/mcp/audio/${uuid}/${token}.mp3`).set("Range", "bytes=2-5");

        expect(response.status).toBe(206);
        expect(response.headers["content-type"]).toContain("audio/mpeg");
        expect(response.headers["accept-ranges"]).toBe("bytes");
        expect(response.headers["content-range"]).toBe("bytes 2-5/10");
        expect(Buffer.from(response.body)).toEqual(Buffer.from("cdef"));
    });

    it("serves complete, open-ended, and suffix ranges", async () => {
        const directory = path.join(basePath, uuid, "mcp-audio");
        await fs.mkdir(directory, { recursive: true });
        await fs.writeFile(path.join(directory, `${token}.mp3`), "abcdefghij");

        const complete = await request(app()).get(`/mcp/audio/${uuid}/${token}.mp3`);
        const open = await request(app()).get(`/mcp/audio/${uuid}/${token}.mp3`).set("Range", "bytes=7-");
        const suffix = await request(app()).get(`/mcp/audio/${uuid}/${token}.mp3`).set("Range", "bytes=-3");
        const unsatisfiable = await request(app()).get(`/mcp/audio/${uuid}/${token}.mp3`).set("Range", "bytes=20-30");

        expect(complete.status).toBe(200);
        expect(complete.headers["content-type"]).toContain("audio/mpeg");
        expect(Buffer.from(complete.body)).toEqual(Buffer.from("abcdefghij"));
        expect(Buffer.from(open.body)).toEqual(Buffer.from("hij"));
        expect(Buffer.from(suffix.body)).toEqual(Buffer.from("hij"));
        expect(unsatisfiable.status).toBe(416);
        expect(unsatisfiable.headers["content-range"]).toBe("bytes */10");
    });

    it("does not reveal missing or malformed artifacts", async () => {
        await expect(request(app()).get(`/mcp/audio/${uuid}/${token}.mp3`)).resolves.toMatchObject({ status: 404 });
        await expect(request(app()).get("/mcp/audio/not-a-uuid/not-a-token.mp3")).resolves.toMatchObject({ status: 404 });
        await expect(request(app()).get(`/mcp/audio/123e4567-e89b-12d3-a456-426614174002/${token}.mp3`)).resolves.toMatchObject({ status: 404 });
        await expect(request(app()).get(`/mcp/audio/${uuid}/${"A".repeat(42)}.mp3`)).resolves.toMatchObject({ status: 404 });
    });
});
