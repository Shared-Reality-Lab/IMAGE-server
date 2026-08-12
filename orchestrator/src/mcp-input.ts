import { randomUUID } from "crypto";
import sharp from "sharp";

const MAX_INPUT_BYTES = Number(process.env.IMAGE_MCP_MAX_INPUT_BYTES || 10 * 1024 * 1024);
const MAX_OUTPUT_BYTES = Number(process.env.IMAGE_MCP_MAX_NORMALIZED_BYTES || 10 * 1024 * 1024);
const MAX_PIXELS = Number(process.env.IMAGE_MCP_MAX_PIXELS || 40_000_000);
const DOWNLOAD_TIMEOUT_MS = Number(process.env.IMAGE_MCP_DOWNLOAD_TIMEOUT_MS || 15_000);

export interface InterpretGraphicInput {
    graphic?: string;
    file?: { download_url?: string; file_id?: string; mime_type?: string; file_name?: string };
    language?: string;
    context?: string;
    url?: string;
}

function fail(message: string): never {
    throw new Error(message);
}

function decodeDataUrl(value: string): { bytes: Buffer; format: string } {
    const match = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/]+={0,2})$/.exec(value);
    if (!match || match[2].length % 4 !== 0) {
        return fail("graphic must be a base64 JPEG, PNG, or WebP data URL.");
    }
    const bytes = Buffer.from(match[2], "base64");
    if (bytes.length === 0 || bytes.toString("base64") !== match[2] || bytes.length > MAX_INPUT_BYTES) {
        return fail("graphic contains invalid or oversized base64 image data.");
    }
    return { bytes, format: match[1].slice("image/".length).replace("jpg", "jpeg") };
}

async function downloadFile(file: InterpretGraphicInput["file"]): Promise<Buffer> {
    if (!file?.download_url) {
        return fail("file.download_url is required for a ChatGPT file input.");
    }
    let url: URL;
    try {
        url = new URL(file.download_url);
    } catch {
        return fail("file.download_url must be a valid HTTPS URL.");
    }
    if (url.protocol !== "https:") {
        return fail("file.download_url must use HTTPS.");
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DOWNLOAD_TIMEOUT_MS);
    try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) {
            return fail("Unable to download the supplied file.");
        }
        const length = Number(response.headers.get("content-length") || 0);
        if (length > MAX_INPUT_BYTES) {
            return fail("The supplied file is too large.");
        }
        const bytes = Buffer.from(await response.arrayBuffer());
        if (bytes.length === 0 || bytes.length > MAX_INPUT_BYTES) {
            return fail("The supplied file is empty or too large.");
        }
        return bytes;
    } finally {
        clearTimeout(timeout);
    }
}

export async function prepareImageRequest(input: InterpretGraphicInput): Promise<Record<string, unknown>> {
    if ((input.graphic === undefined) === (input.file === undefined)) {
        return fail("Provide exactly one of graphic or file.");
    }
    if (input.language !== undefined && !/^[A-Za-z]{2}$/.test(input.language)) {
        return fail("language must be a two-letter IMAGE language code.");
    }
    if (input.context !== undefined && input.context.length > 8_000) {
        return fail("context is too long.");
    }
    if (input.url !== undefined && input.url.length > 2_000) {
        return fail("url is too long.");
    }

    const decoded = input.graphic === undefined ? { bytes: await downloadFile(input.file), format: undefined } : decodeDataUrl(input.graphic);
    const bytes = decoded.bytes;
    const metadata = await sharp(bytes, { animated: false, limitInputPixels: MAX_PIXELS, failOn: "error" }).metadata();
    if (!metadata.format || !["jpeg", "png", "webp"].includes(metadata.format) || (metadata.pages !== undefined && metadata.pages > 1)) {
        return fail("Only single-frame JPEG, PNG, and WebP images are supported.");
    }
    if (decoded.format !== undefined && decoded.format !== metadata.format) {
        return fail("The graphic MIME type does not match its image data.");
    }
    const normalized = await sharp(bytes, { animated: false, limitInputPixels: MAX_PIXELS, failOn: "error" })
        .rotate()
        .jpeg({ quality: 90, mozjpeg: true })
        .toBuffer({ resolveWithObject: true });
    if (!normalized.info.width || !normalized.info.height || normalized.data.length > MAX_OUTPUT_BYTES) {
        return fail("The normalized image is invalid or too large.");
    }

    return {
        request_uuid: randomUUID(),
        timestamp: Math.round(Date.now() / 1000),
        graphic: `data:image/jpeg;base64,${normalized.data.toString("base64")}`,
        dimensions: [normalized.info.width, normalized.info.height],
        context: input.context || "",
        language: (input.language || "en").toLowerCase(),
        ...(input.url ? { URL: input.url } : {}),
        capabilities: [],
        renderers: [
            "ca.mcgill.a11y.image.renderer.Text",
            "ca.mcgill.a11y.image.renderer.SimpleAudio",
            "ca.mcgill.a11y.image.renderer.SegmentAudio"
        ]
    };
}
