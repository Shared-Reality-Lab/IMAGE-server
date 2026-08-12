import { afterEach, describe, expect, it, vi } from "vitest";
import { docker } from "../src/docker";
import { runPipeline } from "../src/pipeline";

const requestUuid = "123e4567-e89b-42d3-a456-426614174000";
const textRenderer = "ca.mcgill.a11y.image.renderer.Text";

function request(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        request_uuid: requestUuid,
        timestamp: 1,
        coordinates: { latitude: 45.5, longitude: -73.6 },
        context: "",
        language: "en",
        capabilities: [],
        renderers: [textRenderer],
        ...overrides
    };
}

function container(service: string, labels: Record<string, string>): Record<string, unknown> {
    return {
        Id: `${service}-id`,
        State: "running",
        Labels: {
            "com.docker.compose.service": service,
            ...labels
        },
        NetworkSettings: { Networks: { image: { NetworkID: "image-network" } } }
    };
}

function pipelineContainers(options: { preprocessors?: number; cyclic?: boolean; handlers?: boolean } = {}): unknown[] {
    const ownContainer = container(String(process.env.HOSTNAME), {});
    ownContainer.Id = `${String(process.env.HOSTNAME)}-id`;
    const preprocessors = Array.from({ length: options.preprocessors ?? 1 }, (_, index) =>
        container(`preprocessor-${index + 1}`, {
            "ca.mcgill.a11y.image.preprocessor": String(index + 1),
            "ca.mcgill.a11y.image.port": "80",
            "ca.mcgill.a11y.image.route": "default",
            "ca.mcgill.a11y.image.required_dependencies": options.cyclic
                ? `preprocessor-${index === 0 ? 2 : 1}`
                : "",
            "ca.mcgill.a11y.image.optional_dependencies": ""
        })
    );
    const handlers = options.handlers === false ? [] : [container("handler", {
        "ca.mcgill.a11y.image.handler": "enable",
        "ca.mcgill.a11y.image.port": "80",
        "ca.mcgill.a11y.image.route": "default",
        "ca.mcgill.a11y.image.required_dependencies": "",
        "ca.mcgill.a11y.image.optional_dependencies": ""
    })];
    return [ownContainer, ...preprocessors, ...handlers];
}

function response(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json" }
    });
}

function installPipelineMocks(options: { preprocessors?: number; cyclic?: boolean; handlers?: boolean; extraRendering?: boolean } = {}) {
    vi.spyOn(docker, "listContainers").mockResolvedValue(pipelineContainers(options) as never);
    vi.stubGlobal("fetch", vi.fn((url: string) => {
        if (url.endsWith("/preprocessor")) {
            return Promise.resolve(response({
                request_uuid: requestUuid,
                timestamp: 1,
                name: "ca.mcgill.a11y.image.preprocessor.Test",
                data: {}
            }));
        }
        return Promise.resolve(response({
            request_uuid: requestUuid,
            timestamp: 1,
            renderings: [
                { type_id: textRenderer, description: "Text interpretation", data: {} },
                ...(options.extraRendering ? [{ type_id: "ca.mcgill.a11y.image.renderer.Unknown", description: "Unsupported", data: {} }] : [])
            ]
        }));
    }));
}

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete process.env.PARALLEL_PREPROCESSORS;
});

describe("runPipeline", () => {
    it("runs preprocessors serially and filters handler renderings", async () => {
        installPipelineMocks({ extraRendering: true });

        const result = await runPipeline(request());

        expect(result.valid).toBe(true);
        expect(result.response.renderings).toEqual([
            { type_id: textRenderer, description: "Text interpretation", data: {} }
        ]);
        expect(fetch).toHaveBeenCalledTimes(2);
    });

    it("runs the dependency graph path when parallel preprocessors are enabled", async () => {
        process.env.PARALLEL_PREPROCESSORS = "ON";
        installPipelineMocks({ preprocessors: 2 });

        const result = await runPipeline(request());

        expect(result.valid).toBe(true);
        expect(fetch).toHaveBeenCalledTimes(3);
    });

    it("falls back when the dependency graph contains a cycle", async () => {
        process.env.PARALLEL_PREPROCESSORS = "ON";
        installPipelineMocks({ preprocessors: 2, cyclic: true });

        const result = await runPipeline(request());

        expect(result.valid).toBe(true);
        expect(fetch).toHaveBeenCalledTimes(3);
    });

    it("returns a valid empty response when no handlers are available", async () => {
        installPipelineMocks({ handlers: false });

        const result = await runPipeline(request());

        expect(result).toMatchObject({ valid: true, response: { renderings: [] } });
    });

    it("keeps concurrent response validation errors isolated", async () => {
        installPipelineMocks({ handlers: false });

        const [wrongType, wrongPattern] = await Promise.all([
            runPipeline(request({ request_uuid: 1 })),
            runPipeline(request({ request_uuid: "not-a-uuid" }))
        ]);

        expect(wrongType.valid).toBe(false);
        expect(wrongPattern.valid).toBe(false);
        expect(JSON.stringify(wrongType.errors)).toContain("must be string");
        expect(JSON.stringify(wrongPattern.errors)).toContain("must match pattern");
    });
});
