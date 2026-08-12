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
    "mcp-protocol-version": "2026-07-28"
};

function modernMcpRequest(method: string, id: number, params: Record<string, unknown> = {}) {
    return {
        jsonrpc: "2.0",
        id,
        method,
        params: {
            ...params,
            _meta: {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientInfo": { name: "test-client", version: "1.0.0" },
                "io.modelcontextprotocol/clientCapabilities": {}
            }
        }
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
            http: {
                req: new Request("http://orchestrator:8080/mcp", {
                    headers: { host: "unicorn.cim.mcgill.ca", "x-forwarded-proto": "https", "x-forwarded-prefix": "/image" }
                })
            }
        } as Parameters<typeof publicBaseUrl>[0];

        expect(publicBaseUrl(context)).toBe("https://unicorn.cim.mcgill.ca/image");
    });

    it("serves the registered tool and audio UI resource through the SDK", async () => {
        const tools = await request(app).post("/mcp")
            .set({ ...mcpHeaders, "mcp-method": "tools/list" })
            .send(modernMcpRequest("tools/list", 1));
        const resources = await request(app).post("/mcp")
            .set({ ...mcpHeaders, "mcp-method": "resources/list" })
            .send(modernMcpRequest("resources/list", 2));

        expect(tools.status).toBe(200);
        expect(tools.body.result.tools[0]).toMatchObject({ name: "interpret_graphic", annotations: { readOnlyHint: true } });
        expect(resources.status).toBe(200);
        expect(resources.body.result.resources[0]).toMatchObject({ uri: "ui://image/audio-experience" });
    });

    it("requires the configured MCP bearer token", async () => {
        process.env.IMAGE_MCP_TOKEN = "test-token";
        const body = modernMcpRequest("tools/list", 1);

        const rejected = await request(app).post("/mcp")
            .set({ ...mcpHeaders, "mcp-method": "tools/list" })
            .send(body);
        const accepted = await request(app).post("/mcp")
            .set({ ...mcpHeaders, "mcp-method": "tools/list", authorization: "Bearer test-token" })
            .send(body);

        expect(rejected.status).toBe(401);
        expect(accepted.status).toBe(200);
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
