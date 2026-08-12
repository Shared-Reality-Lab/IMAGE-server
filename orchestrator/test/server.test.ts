import request from "supertest";
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
            .send(mcpRequest("resources/read", 3, { uri: "ui://image/audio-experience-v6.html" }));

        expect(tools.status).toBe(200);
        expect(tools.body.result.tools[0]).toMatchObject({
            name: "interpret_graphic",
            annotations: { readOnlyHint: true },
            outputSchema: {
                type: "object",
                required: ["audio", "text"]
            },
            _meta: {
                ui: { resourceUri: "ui://image/audio-experience-v6.html", visibility: ["model", "app"] },
                "openai/outputTemplate": "ui://image/audio-experience-v6.html"
            }
        });
        expect(resources.status).toBe(200);
        expect(resources.body.result.resources).toEqual(expect.arrayContaining([
            expect.objectContaining({ uri: "ui://image/audio-experience-v6.html" }),
            expect.objectContaining({ uri: "ui://image/audio-experience-v5.html" }),
            expect.objectContaining({ uri: "ui://image/audio-experience" })
        ]));
        expect(resource.status, JSON.stringify(resource.body)).toBe(200);
        expect(resource.body.result.contents[0]).toMatchObject({
            uri: "ui://image/audio-experience-v6.html",
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
            .send(mcpRequest("resources/read", 3, { uri: "ui://image/audio-experience-v6.html" }));

        expect(resource.status).toBe(200);
        expect(resource.body.result.contents[0]).toMatchObject({
            uri: "ui://image/audio-experience-v6.html",
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
