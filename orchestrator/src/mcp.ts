import { createMcpHandler, McpServer } from "@modelcontextprotocol/server";
import { z } from "zod";
import { prepareImageRequest } from "./mcp-input";
import { runPipeline } from "./pipeline";

export const AUDIO_UI_RESOURCE_URI = "ui://image/audio-experience";

const audioExperienceHtml = "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>IMAGE audio experience</title></head><body><main><h1>IMAGE audio experience</h1><p>Audio playback will appear here when an IMAGE interpretation includes audio.</p></main></body></html>";

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

/**
 * Builds a per-request MCP server. The SDK factory is intentionally stateless,
 * including for its built-in 2025-11-25 compatibility fallback.
 */
export function createImageMcpHandler() {
    return createMcpHandler(async () => {
        const server = new McpServer(
            { name: "image-orchestrator", version: "0.2.1" },
            {
                instructions: "IMAGE creates accessible text and audio interpretations for blind and low-vision users."
            }
        );

        server.registerTool("interpret_graphic", {
            title: "IMAGE graphic interpreter (photos, images, screenshots, and charts)",
            description: "Creates accessible text and audio interpretations for an image supplied directly or obtained from another connector.",
            inputSchema,
            annotations: {
                readOnlyHint: true,
                destructiveHint: false,
                idempotentHint: false,
                openWorldHint: true
            },
            _meta: { "ui/resourceUri": AUDIO_UI_RESOURCE_URI }
        }, async input => {
            try {
                const result = await runPipeline(await prepareImageRequest(input));
                if (!result.valid) {
                    return { isError: true, content: [{ type: "text", text: "IMAGE produced an invalid response." }] };
                }
                const text = (result.response.renderings as Array<{ type_id?: string; data?: { text?: unknown } }>)
                    .filter(rendering => rendering.type_id === "ca.mcgill.a11y.image.renderer.Text")
                    .map(rendering => rendering.data?.text)
                    .filter((value): value is string => typeof value === "string");
                return { content: text.length ? text.map(value => ({ type: "text" as const, text: value })) : [{ type: "text" as const, text: "IMAGE did not produce a text interpretation." }] };
            } catch (error) {
                return { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : "Unable to process the supplied image." }] };
            }
        });

        server.registerResource("audio-experience", AUDIO_UI_RESOURCE_URI, {
            title: "IMAGE audio experience",
            mimeType: "text/html;profile=mcp-app"
        }, async uri => ({
            contents: [{
                uri: uri.href,
                mimeType: "text/html;profile=mcp-app",
                text: audioExperienceHtml
            }]
        }));

        return server;
    }, { responseMode: "json" });
}
