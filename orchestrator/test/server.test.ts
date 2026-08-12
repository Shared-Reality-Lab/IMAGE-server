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

const validRequest = {
    request_uuid: "123e4567-e89b-42d3-a456-426614174000",
    timestamp: 1,
    coordinates: { latitude: 45.5, longitude: -73.6 },
    context: "",
    language: "en",
    capabilities: [],
    renderers: ["ca.mcgill.a11y.image.renderer.Text"]
};

afterEach(() => {
    vi.clearAllMocks();
    delete process.env.STORE_IMAGE_DATA;
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
