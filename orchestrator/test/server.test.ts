import request from "supertest";
import sharp from "sharp";
import { afterEach, describe, expect, it, vi } from "vitest";

const pipelineMocks = vi.hoisted(() => ({
    runPipeline: vi.fn(),
    storeResponse: vi.fn()
}));

vi.mock("../src/pipeline", () => ({
    BASE_LOG_PATH: "/tmp",
    getRoute: vi.fn(() => "default"),
    reqTag: vi.fn(() => ""),
    runPipeline: pipelineMocks.runPipeline,
    runPreprocessors: vi.fn(),
    runPreprocessorsParallel: vi.fn(),
    storeResponse: pipelineMocks.storeResponse
}));

import { app } from "../src/server";
import { publicBaseUrl } from "../src/mcp";

const validRequest = {
    request_uuid: "123e4567-e89b-42d3-a456-426614174000",
    timestamp: 1,
    coordinates: { latitude: 45.5, longitude: -73.6 },
    context: "",
    language: "en",
    capabilities: [],
    renderers: ["ca.mcgill.a11y.image.renderer.Text"]
};

const mcpHeaders = {
    accept: "application/json, text/event-stream",
    "content-type": "application/json",
    "mcp-protocol-version": "2025-06-18"
};

const legacyMcpHeaders = { ...mcpHeaders, "mcp-protocol-version": "2025-11-25" };

function mcpRequest(method: string, id: number, params: Record<string, unknown> = {}) {
    return {
        jsonrpc: "2.0",
        id,
        method,
        params
    };
}

afterEach(() => {
    vi.clearAllMocks();
    delete process.env.STORE_IMAGE_DATA;
    delete process.env.IMAGE_MCP_TOKEN;
});

describe("POST /mcp", () => {
    it("uses the reverse proxy's public path prefix for artifact links", () => {
        const context = {
            protocol: "http",
            get: (name: string) => ({
                host: "unicorn.cim.mcgill.ca",
                "x-forwarded-proto": "https",
                "x-forwarded-prefix": "/image"
            })[name]
        } as Parameters<typeof publicBaseUrl>[0];

        expect(publicBaseUrl(context)).toBe("https://unicorn.cim.mcgill.ca/image");
    });

    it("serves the registered tool and audio UI resource through the SDK", async () => {
        const tools = await request(app).post("/mcp")
            .set(mcpHeaders)
            .send(mcpRequest("tools/list", 1));
        const resources = await request(app).post("/mcp")
            .set(mcpHeaders)
            .send(mcpRequest("resources/list", 2));
        const resource = await request(app).post("/mcp")
            .set(mcpHeaders)
            .send(mcpRequest("resources/read", 3, { uri: "ui://image/audio-experience-v7.html" }));

        expect(tools.status).toBe(200);
        expect(tools.body.result.tools[0]).toMatchObject({
            name: "interpret_graphic",
            annotations: { readOnlyHint: true },
            outputSchema: {
                type: "object",
                required: ["audio", "text"]
            },
            _meta: {
                ui: { resourceUri: "ui://image/audio-experience-v7.html", visibility: ["model", "app"] },
                "openai/outputTemplate": "ui://image/audio-experience-v7.html",
                "openai/fileParams": ["file"]
            }
        });
        expect(tools.body.result.tools[0].inputSchema.properties.file).toMatchObject({
            type: "object",
            required: ["download_url", "file_id"],
            additionalProperties: false,
            properties: {
                download_url: { type: "string" },
                file_id: { type: "string" },
                mime_type: { type: "string" },
                file_name: { type: "string" }
            }
        });
        expect(resources.status).toBe(200);
        expect(resources.body.result.resources).toEqual(expect.arrayContaining([
            expect.objectContaining({ uri: "ui://image/audio-experience-v7.html" }),
            expect.objectContaining({ uri: "ui://image/audio-experience-v6.html" }),
            expect.objectContaining({ uri: "ui://image/audio-experience-v5.html" }),
            expect.objectContaining({ uri: "ui://image/audio-experience" })
        ]));
        expect(resource.status, JSON.stringify(resource.body)).toBe(200);
        expect(resource.body.result.contents[0]).toMatchObject({
            uri: "ui://image/audio-experience-v7.html",
            mimeType: "text/html;profile=mcp-app",
            text: expect.stringContaining("IMAGE audio experience")
        });
    });

    it("requires the configured MCP bearer token", async () => {
        process.env.IMAGE_MCP_TOKEN = "test-token";
        const body = mcpRequest("tools/list", 1);

        const rejected = await request(app).post("/mcp")
            .set(mcpHeaders)
            .send(body);
        const accepted = await request(app).post("/mcp")
            .set({ ...mcpHeaders, authorization: "Bearer test-token" })
            .send(body);

        expect(rejected.status).toBe(401);
        expect(accepted.status).toBe(200);
    });

    it("accepts ChatGPT resource reads without nonstandard method or name headers", async () => {
        const resource = await request(app).post("/mcp")
            .set(mcpHeaders)
            .send(mcpRequest("resources/read", 3, { uri: "ui://image/audio-experience-v7.html" }));

        expect(resource.status).toBe(200);
        expect(resource.body.result.contents[0]).toMatchObject({
            uri: "ui://image/audio-experience-v7.html",
            mimeType: "text/html;profile=mcp-app",
            text: expect.stringContaining("IMAGE audio experience")
        });
    });

    it("keeps previously advertised template URIs readable for cached ChatGPT descriptors", async () => {
        const resource = await request(app).post("/mcp")
            .set(mcpHeaders)
            .send(mcpRequest("resources/read", 4, { uri: "ui://image/audio-experience-v4" }));

        expect(resource.status).toBe(200);
        expect(resource.body.result.contents[0]).toMatchObject({
            uri: "ui://image/audio-experience-v4",
            mimeType: "text/html;profile=mcp-app",
            text: expect.stringContaining("IMAGE audio experience")
        });
    });

    it("supports legacy initialize and stateless utility requests", async () => {
        const initialized = await request(app).post("/mcp").set(legacyMcpHeaders).send(mcpRequest("initialize", 10, {
            protocolVersion: "2025-11-25",
            capabilities: {},
            clientInfo: { name: "legacy-test", version: "1.0.0" }
        }));
        const ping = await request(app).post("/mcp").set(legacyMcpHeaders).send(mcpRequest("ping", 11));

        expect(initialized.status).toBe(200);
        expect(initialized.body.result).toMatchObject({
            protocolVersion: "2025-11-25",
            serverInfo: { name: "image-orchestrator", version: "0.2.1" }
        });
        expect(initialized.headers["mcp-session-id"]).toBeUndefined();
        expect(ping).toMatchObject({ status: 200, body: { result: {} } });
    });

    it("returns JSON-RPC errors for unknown methods, tools, and invalid parameters", async () => {
        const unknownMethod = await request(app).post("/mcp").set(mcpHeaders).send(mcpRequest("not/a-method", 12));
        const unknownTool = await request(app).post("/mcp").set(mcpHeaders).send(mcpRequest("tools/call", 13, { name: "missing", arguments: {} }));
        const invalidTool = await request(app).post("/mcp").set(mcpHeaders).send(mcpRequest("tools/call", 14, { name: "interpret_graphic", arguments: {} }));

        expect(unknownMethod.body.error.code).toBe(-32601);
        expect(unknownTool.body.result).toMatchObject({ isError: true });
        expect(invalidTool.body.result).toMatchObject({ isError: true });
        expect(pipelineMocks.runPipeline).not.toHaveBeenCalled();
    });

    it("calls interpret_graphic and returns portable and structured text", async () => {
        const bytes = await sharp({ create: { width: 1, height: 1, channels: 3, background: "#fff" } }).png().toBuffer();
        pipelineMocks.runPipeline.mockResolvedValue({
            valid: true,
            errors: null,
            response: {
                request_uuid: "123e4567-e89b-42d3-a456-426614174003",
                timestamp: 1,
                renderings: [{ type_id: "ca.mcgill.a11y.image.renderer.Text", data: { text: "A white square." } }]
            }
        });

        const response = await request(app).post("/mcp").set(mcpHeaders).send(mcpRequest("tools/call", 18, {
            name: "interpret_graphic",
            arguments: { graphic: `data:image/png;base64,${bytes.toString("base64")}` }
        }));

        expect(response.status).toBe(200);
        expect(response.body.result).toMatchObject({
            content: [{ type: "text", text: "A white square." }],
            structuredContent: { audio: [], text: ["A white square."] }
        });
        expect(pipelineMocks.runPipeline).toHaveBeenCalledWith(expect.objectContaining({
            dimensions: [1, 1],
            graphic: expect.stringMatching(/^data:image\/jpeg;base64,/)
        }));
    });

    it("keeps tool metadata stable across client initialization capabilities", async () => {
        const before = await request(app).post("/mcp").set(mcpHeaders).send(mcpRequest("tools/list", 15));
        await request(app).post("/mcp").set(legacyMcpHeaders).send(mcpRequest("initialize", 16, {
            protocolVersion: "2025-11-25",
            capabilities: { extensions: { "io.modelcontextprotocol/ui": {} } },
            clientInfo: { name: "app-client", version: "1" }
        }));
        const after = await request(app).post("/mcp").set(mcpHeaders).send(mcpRequest("tools/list", 17));

        expect(after.body.result.tools).toEqual(before.body.result.tools);
    });

});

describe("POST /render", () => {
    it("returns a pipeline response", async () => {
        const result = { request_uuid: validRequest.request_uuid, timestamp: 2, renderings: [] };
        pipelineMocks.runPipeline.mockResolvedValue({ response: result, valid: true, errors: null });

        const response = await request(app).post("/render").send(validRequest);

        expect(response.status).toBe(200);
        expect(response.body).toEqual(result);
        expect(pipelineMocks.runPipeline).toHaveBeenCalledWith(validRequest);
    });

    it("rejects schema-invalid requests before invoking the pipeline", async () => {
        const response = await request(app).post("/render").send({});

        expect(response.status).toBe(400);
        expect(pipelineMocks.runPipeline).not.toHaveBeenCalled();
    });

    it("sends the response before optional persistence completes", async () => {
        process.env.STORE_IMAGE_DATA = "ON";
        const result = { request_uuid: validRequest.request_uuid, timestamp: 2, renderings: [] };
        let finishStore: (() => void) | undefined;
        pipelineMocks.runPipeline.mockResolvedValue({ response: result, valid: true, errors: null });
        pipelineMocks.storeResponse.mockImplementation(() => new Promise<void>(resolve => {
            finishStore = resolve;
        }));

        const response = await request(app).post("/render").send(validRequest);

        expect(response.status).toBe(200);
        expect(pipelineMocks.storeResponse).toHaveBeenCalledWith(validRequest, result);
        expect(finishStore).toBeTypeOf("function");
        finishStore?.();
    });
});
