import { randomBytes } from "crypto";
import fs from "fs/promises";
import path from "path";
import { BASE_LOG_PATH } from "./pipeline";

const MAX_AUDIO_BYTES = Number(process.env.IMAGE_MCP_MAX_AUDIO_BYTES || 20 * 1024 * 1024);
const SIMPLE_AUDIO = "ca.mcgill.a11y.image.renderer.SimpleAudio";
const SEGMENT_AUDIO = "ca.mcgill.a11y.image.renderer.SegmentAudio";
const TEXT = "ca.mcgill.a11y.image.renderer.Text";

interface Rendering {
    type_id?: unknown;
    description?: unknown;
    data?: Record<string, unknown>;
}

interface AudioInfo {
    name?: unknown;
    offset?: unknown;
    duration?: unknown;
}

function audioDataUrl(value: unknown): Buffer | undefined {
    if (typeof value !== "string") {
        return undefined;
    }
    const match = /^data:audio\/(?:mpeg|mp3);base64,([A-Za-z0-9+/]+={0,2})$/.exec(value);
    if (!match || match[1].length % 4 !== 0) {
        return undefined;
    }
    const bytes = Buffer.from(match[1], "base64");
    return bytes.length > 0 && bytes.length <= MAX_AUDIO_BYTES && bytes.toString("base64") === match[1] ? bytes : undefined;
}

function timepoints(value: unknown) {
    if (!Array.isArray(value)) {
        return [];
    }
    return value.flatMap(item => {
        const point = item as AudioInfo;
        return typeof point.name === "string" && typeof point.offset === "number" && point.offset >= 0 &&
            typeof point.duration === "number" && point.duration >= 0
            ? [{ name: point.name, offset: point.offset, duration: point.duration }]
            : [];
    });
}

async function storeAudio(basePath: string, requestUuid: string, bytes: Buffer): Promise<string> {
    const token = randomBytes(32).toString("base64url");
    const directory = path.join(basePath, requestUuid, "mcp-audio");
    await fs.mkdir(directory, { recursive: true });
    await fs.writeFile(path.join(directory, `${token}.mp3`), bytes, { mode: 0o600 });
    return token;
}

/** Converts usable IMAGE renderings to compact MCP content without exposing base64 audio. */
export async function convertRenderings(requestUuid: string, renderings: unknown, basePath = BASE_LOG_PATH, publicBase = "") {
    const content: Array<{ type: "text"; text: string }> = [];
    const audio: Array<Record<string, unknown>> = [];
    const dropped: string[] = [];
    for (const rendering of Array.isArray(renderings) ? renderings as Rendering[] : []) {
        const type = typeof rendering.type_id === "string" ? rendering.type_id : "unknown";
        if (type === TEXT && typeof rendering.data?.text === "string") {
            content.push({ type: "text", text: rendering.data.text });
            continue;
        }
        const dataUrl = type === SIMPLE_AUDIO ? rendering.data?.audio : type === SEGMENT_AUDIO ? rendering.data?.audioFile : undefined;
        if (type === SIMPLE_AUDIO || type === SEGMENT_AUDIO) {
            const bytes = audioDataUrl(dataUrl);
            if (!bytes) {
                dropped.push(type);
                continue;
            }
            const token = await storeAudio(basePath, requestUuid, bytes);
            const points = type === SEGMENT_AUDIO ? timepoints(rendering.data?.audioInfo) : [];
            const description = typeof rendering.description === "string" ? rendering.description : "IMAGE audio interpretation";
            const artifactPath = `/mcp/audio/${requestUuid}/${token}.mp3`;
            const artifactUrl = publicBase ? `${publicBase}${artifactPath}` : artifactPath;
            audio.push({ description, mimeType: "audio/mpeg", bytes: bytes.length, artifactPath, artifactUrl, timepoints: points });
            content.push({ type: "text", text: `${description}\nAudio: ${artifactUrl}${points.length ? `\nSegments: ${points.map(point => `${point.name} (${point.offset}s, ${point.duration}s)`).join("; ")}` : ""}` });
            continue;
        }
        dropped.push(type);
    }
    return { content, audio, dropped };
}
