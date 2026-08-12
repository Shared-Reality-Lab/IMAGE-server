import express from "express";
import request from "supertest";
import { describe, expect, it } from "vitest";
import { toNodeHandler } from "@modelcontextprotocol/node";
import { createMcpHandler, McpServer } from "@modelcontextprotocol/server";
import { z } from "zod";

const protocolVersion = "2026-07-28";

function modernRequest(method: string, id: number) {
    return {
        jsonrpc: "2.0",
        id,
        method,
        params: {
            _meta: {
                "io.modelcontextprotocol/protocolVersion": protocolVersion,
                "io.modelcontextprotocol/clientInfo": { name: "compatibility-spike", version: "1.0.0" },
                "io.modelcontextprotocol/clientCapabilities": {}
            }
        }
    };
}

function createSpikeApp() {
    const handler = createMcpHandler(async () => {
        const server = new McpServer(
            { name: "image-mcp-spike", version: "0.0.0" },
            { instructions: "Compatibility spike only." }
        );
        server.registerTool("spike_tool", {
            description: "Proves modern tool discovery.",
            inputSchema: z.object({})
        }, async () => ({ content: [{ type: "text", text: "ok" }] }));
        return server;
    }, { responseMode: "json" });
    const app = express();
    app.use(express.json());
    const nodeHandler = toNodeHandler(handler);
    app.post("/mcp", (req, res) => nodeHandler(req, res, req.body));
    return app;
}

function sseResult(text: string): { result: Record<string, unknown> } {
    const data = text.split("\n").find(line => line.startsWith("data: "));
    return JSON.parse(data?.slice("data: ".length) || "{}");
}

describe("MCP v2 Express compatibility spike", () => {
    it("serves modern discovery and tools/list through Express 4", async () => {
        const app = createSpikeApp();
        const headers = {
            accept: "application/json, text/event-stream",
            "content-type": "application/json",
            "mcp-protocol-version": protocolVersion
        };

        const discovery = await request(app).post("/mcp").set({ ...headers, "mcp-method": "server/discover" }).send(modernRequest("server/discover", 1));
        const tools = await request(app).post("/mcp").set({ ...headers, "mcp-method": "tools/list" }).send(modernRequest("tools/list", 2));

        expect(discovery.status).toBe(200);
        expect(discovery.body.result.resultType).toBe("complete");
        expect(discovery.body.result.ttlMs).toBe(0);
        expect(discovery.body.result.cacheScope).toBe("private");
        expect(tools.status).toBe(200);
        expect(tools.body.result.resultType).toBe("complete");
        expect(tools.body.result.tools).toHaveLength(1);
        expect(tools.body.result.tools[0].name).toBe("spike_tool");
    });

    it("provides the SDK's stateless 2025-11-25 fallback", async () => {
        const app = createSpikeApp();
        const headers = {
            accept: "application/json, text/event-stream",
            "content-type": "application/json"
        };
        const initialize = {
            jsonrpc: "2.0",
            id: 1,
            method: "initialize",
            params: {
                protocolVersion: "2025-11-25",
                capabilities: {},
                clientInfo: { name: "compatibility-spike", version: "1.0.0" }
            }
        };
        const tools = {
            jsonrpc: "2.0",
            id: 2,
            method: "tools/list",
            params: {}
        };

        const initializeResponse = await request(app).post("/mcp").set(headers).send(initialize);
        const toolsResponse = await request(app).post("/mcp").set(headers).send(tools);

        expect(initializeResponse.status).toBe(200);
        expect(initializeResponse.headers["content-type"]).toContain("text/event-stream");
        expect(sseResult(initializeResponse.text).result.protocolVersion).toBe("2025-11-25");
        expect(initializeResponse.headers["mcp-session-id"]).toBeUndefined();
        expect(toolsResponse.status).toBe(200);
        expect(toolsResponse.headers["content-type"]).toContain("text/event-stream");
        expect((sseResult(toolsResponse.text).result.tools as Array<{ name: string }>)[0].name).toBe("spike_tool");
        expect(toolsResponse.headers["mcp-session-id"]).toBeUndefined();
    });
});
