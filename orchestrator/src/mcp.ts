import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { prepareImageRequest } from "./mcp-input";
import { runPipeline } from "./pipeline";
import { convertRenderings } from "./mcp-renderings";
import { AUDIO_EXPERIENCE_HTML } from "./mcp-app";

export const AUDIO_UI_RESOURCE_URI = "ui://image/audio-experience-v6.html";
export const AUDIO_UI_RESOURCE_URIS = [
    AUDIO_UI_RESOURCE_URI,
    "ui://image/audio-experience-v5.html",
    "ui://image/audio-experience-v4",
    "ui://image/audio-experience-v3",
    "ui://image/audio-experience-v2",
    "ui://image/audio-experience"
] as const;
const RESOURCE_MIME_TYPE = "text/html;profile=mcp-app";

const inputSchema = z.object({
    graphic: z.string().optional().describe("A base64 image data URL."),
    file: z.object({
        download_url: z.string().url().optional(),
        file_id: z.string().optional(),
        mime_type: z.string().optional(),
        file_name: z.string().optional()
    }).passthrough().optional().describe("A ChatGPT file object."),
    language: z.string().optional().describe("The requested interpretation language. Defaults to en."),
    context: z.string().optional().describe("Bounded surrounding context for the image."),
    url: z.string().optional().describe("A source-page identifier. IMAGE does not fetch this URL.")
}).refine(value => Number(value.graphic !== undefined) + Number(value.file !== undefined) === 1, {
    message: "Provide exactly one of graphic or file."
});

const outputSchema = z.object({
    audio: z.array(z.object({
        description: z.string(),
        mimeType: z.literal("audio/mpeg"),
        bytes: z.number().int().nonnegative(),
        artifactPath: z.string(),
        artifactUrl: z.string().url(),
        timepoints: z.array(z.object({
            name: z.string(),
            offset: z.number().nonnegative(),
            duration: z.number().nonnegative()
        }))
    })),
    text: z.array(z.string())
});

export interface PublicRequest {
    protocol: string;
    get(name: string): string | undefined;
}

export function publicBaseUrl(request: PublicRequest): string {
    const host = request.get("host");
    if (!host) return "";
    const protocol = request.get("x-forwarded-proto")?.split(",")[0].trim() || request.protocol;
    const prefix = request.get("x-forwarded-prefix")?.replace(/\/+$/, "") || "";
    return `${protocol}://${host}${prefix.startsWith("/") ? prefix : ""}`;
}

export function createImageMcpServer(request: PublicRequest) {
    const server = new McpServer(
        { name: "image-orchestrator", version: "0.2.1" },
        { instructions: "IMAGE creates accessible text and audio interpretations for blind and low-vision users." }
    );

    server.registerTool("interpret_graphic", {
            title: "IMAGE graphic interpreter (photos, images, screenshots, and charts)",
            description: "Creates accessible text and audio interpretations for an image supplied directly or obtained from another connector.",
            inputSchema,
            outputSchema,
            annotations: {
                readOnlyHint: true,
                destructiveHint: false,
                idempotentHint: false,
                openWorldHint: true
            },
            _meta: {
                ui: { resourceUri: AUDIO_UI_RESOURCE_URI, visibility: ["model", "app"] },
                "openai/outputTemplate": AUDIO_UI_RESOURCE_URI,
                "openai/widgetAccessible": true
            }
        }, async input => {
            try {
                const result = await runPipeline(await prepareImageRequest(input));
                if (!result.valid) {
                    return { isError: true, content: [{ type: "text", text: "IMAGE produced an invalid response." }] };
                }
                const converted = await convertRenderings(String(result.response.request_uuid), result.response.renderings, undefined, publicBaseUrl(request));
                return {
                    content: converted.content.length ? converted.content : [{ type: "text", text: "IMAGE did not produce a usable interpretation." }],
                    structuredContent: { audio: converted.audio, text: converted.content.map(item => item.text) },
                    _meta: { "ca.mcgill.a11y.image/audio": converted.audio, "ca.mcgill.a11y.image/droppedRenderings": converted.dropped }
                };
            } catch (error) {
                return { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : "Unable to process the supplied image." }] };
            }
        });

    for (const [index, resourceUri] of AUDIO_UI_RESOURCE_URIS.entries()) server.registerResource(`audio-experience-${index}`, resourceUri, {
            title: "IMAGE audio experience",
            mimeType: RESOURCE_MIME_TYPE
        }, async () => ({
            contents: [{
                uri: resourceUri,
                mimeType: RESOURCE_MIME_TYPE,
                text: AUDIO_EXPERIENCE_HTML,
                _meta: {
                    ui: {
                        prefersBorder: true,
                        csp: {
                            resourceDomains: process.env.IMAGE_MCP_PUBLIC_ORIGIN ? [process.env.IMAGE_MCP_PUBLIC_ORIGIN] : []
                        }
                    },
                    "openai/widgetPrefersBorder": true,
                    "openai/widgetCSP": {
                        resource_domains: process.env.IMAGE_MCP_PUBLIC_ORIGIN ? [process.env.IMAGE_MCP_PUBLIC_ORIGIN] : []
                    }
                }
            }]
        }));

    return server;
}
