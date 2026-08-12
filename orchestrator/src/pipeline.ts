/*
 * Copyright (c) 2021 IMAGE Project, Shared Reality Lab, McGill University
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 * You should have received a copy of the GNU Affero General Public License
 * and our Additional Terms along with this program.
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.
 */
import fs from "fs/promises";
import path from "path";
import os from "os"; // Import 'os' to get the number of CPU cores
import { ajv } from "./ajv";
import { docker, getPreprocessorServices, getHandlerServices, DEFAULT_ROUTE_NAME, getFilteredContainers } from "./docker";
import { ServerCache } from "./server-cache";
import { PreprocessorResponse, HandlerResponse, ServiceInfo } from "./types";
import { Graph, GraphNode } from "./graph";

const serverCache = new ServerCache();
const memjsClient = serverCache.memjsClient;

console.debug("memcached server", memjsClient.servers);

const PREPROCESSOR_TIME_MS = (!isNaN(parseInt(process.env.PREPROCESSOR_TIMEOUT || ""))) ? parseInt(process.env.PREPROCESSOR_TIMEOUT || "") : 15000;

export const BASE_LOG_PATH = path.join("/var", "log", "IMAGE");

const MODIFY_REQUEST_INDEX = 4;  // The index returned by getPreprocessorServices corresponding to modifyRequest
const NAME_MODIFY_REQUEST = "ca.mcgill.a11y.image.request";
const RESTRICTED_FIELDS = [
    "request_uuid",
    "timestamp",
    "preprocessors",
];

// build a consistent log tag "req=<id> " (uses the existing request_uuid in the schema)
export function reqTag(data: Record<string, unknown>): string {
    const id = (data as any)?.request_uuid as string | undefined;
    return id ? `req=${id} ` : "";
}

async function measureExecutionTime<T>(label: string, fn: () => Promise<T>, tagPrefix = ""): Promise<T> {
    /*
    Organized Metrics Logged with Units:
    - timestamp:  timestamp of the log entry
    - label: label (in preprocessor's case, this would be 'preprocessor')
    - execution_time_ms: Wall-clock time in milliseconds (ms)
    - cpu_time_ms: CPU time in milliseconds (ms)
    - normalized_cpu_usage_percent: CPU usage as a percentage (%)

    Sample log output:
    timestamp=2025-01-10T08:30:00.123Z label=cache_check execution_time_ms=7.69ms cpu_time_ms=7.23ms normalized_cpu_usage_percent=95.62%
    */

    const startTime = performance.now();
    const startCpuUsage = process.cpuUsage();
    const coreCount = os.cpus().length; // Number of CPU cores

    try {
        const result = await fn();
        return result;
    } finally {
        const endTime = performance.now();
        const duration = parseFloat((endTime - startTime).toFixed(2)); // wall-clock duration in ms
        const endCpuUsage = process.cpuUsage(startCpuUsage);
        const cpuTime = parseFloat(((endCpuUsage.user + endCpuUsage.system) / 1000).toFixed(2)); // CPU time in ms
        // Normalize CPU Usage as a percentage of wall-clock duration to account for multi-core systems -- see https://stackoverflow.com/questions/74776323/why-is-node-js-process-cpuusage-returning-more-than-100
        const normalizedCpuUsage = parseFloat(((cpuTime / (duration * coreCount)) * 100).toFixed(2)); // normalized CPU usage

        console.log(`${tagPrefix}timestamp=${new Date().toISOString()} label=${label} execution_time_ms=${duration}ms cpu_time_ms=${cpuTime}ms normalized_cpu_usage_percent=${normalizedCpuUsage}%`);
        // To extract the log and store into a dictionary --> log_dict = {item.split('=')[1] for item in log.split(' ')}
    }
}

async function checkCache(preprocessorName: string, hashedKey: string, cacheTimeOut: number): Promise<PreprocessorResponse | null> {
    if (process.env.CACHE_OVERRIDE != undefined && preprocessorName) {
       const filepath = path.join(process.env.CACHE_OVERRIDE, hashedKey);
       try {
            // Load cache override and serve
            const contents = await fs.readFile(filepath);
            console.debug(`Loaded from file ${filepath} for preprocessor ${preprocessorName}`);
            const override = JSON.parse(contents.toString());
            return override;
        } catch (e: any) {
            if (e.code !== 'ENOENT') {  // Ignoring as this will occur if there is no override
                console.warn(`While reading the override for ${hashedKey}, an error occurred: ${e.name}`);
            }
        }
    }

    // Timeout only is applicable to regular cache.
    if (cacheTimeOut <= 0) {
        return null; // no caching if timeout is 0, skip lookup
    }

    const cacheValue = await serverCache.getResponseFromCache(hashedKey);
    if (cacheValue && preprocessorName) {
        // Return the value from cache if found
        console.debug(`Response for preprocessor "${preprocessorName}" served from cache`);
        return JSON.parse(cacheValue) as PreprocessorResponse;
    }

    return null; // cache miss
}

async function fetchPreprocessorResponse(preprocessor: ServiceInfo, data: Record<string, unknown>): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), PREPROCESSOR_TIME_MS);
    try {
        const response = await fetch(`http://${preprocessor[0]}:${preprocessor[1]}/preprocessor`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Request-ID": ((data as any)?.request_uuid ?? "") // pass client request_uuid downstream; ok if empty
            },
            body: JSON.stringify(data),
            signal: controller.signal,
        });
        clearTimeout(timeout);
        return response;
    } catch (err) {
        console.error(`${reqTag(data)}Error occurred while fetching from preprocessor "${preprocessor[0]}"`);
        throw err;
    }
}

async function processResponse(response: Response, preprocessor: ServiceInfo, data: Record<string, unknown>, hashedKey: string, cacheTimeOut: number): Promise<void> {
    if (response.status === 200) {
        const jsonResponse = await response.json() as PreprocessorResponse;
        if (ajv.validate("https://image.a11y.mcgill.ca/preprocessor-response.schema.json", jsonResponse)) {
            if (preprocessor[MODIFY_REQUEST_INDEX] == false) {
                const preprocessorName = jsonResponse["name"];
                (data["preprocessors"] as Record<string, unknown>)[preprocessorName] = jsonResponse["data"];
                // store data in cache
                // disable the cache if "ca.mcgill.a11y.image.cacheTimeout" is 0
                if (cacheTimeOut > 0) {
                    console.debug(`${reqTag(data)}Saving response for ${preprocessorName} in cache with key ${hashedKey}`);
                    await serverCache.setResponseInCache(hashedKey, jsonResponse["name"], jsonResponse["data"], cacheTimeOut);
                }
            } else {
                // Verify that name in response matches expectation.
                if (jsonResponse["name"] != NAME_MODIFY_REQUEST) {
                    console.debug(`${reqTag(data)}Pseudo-preprocessor ${preprocessor[0]} attempted to modify the request, but returned unexpected name ${jsonResponse["name"]}. Ignoring response.`);
                } else {
                    // Make transmitted modifications, within reason.
                    for (const [field, value] of Object.entries(jsonResponse["data"])) {
                        if (RESTRICTED_FIELDS.includes(field)) {
                            console.debug(`${reqTag(data)}Pseudo-preprocessor ${preprocessor[0]} attempted to modify restricted request field '${field}'. Ignoring modification.`);
                        } else {
                            data[field] = value;
                        }
                    }
                    // TODO caching
                }
            }
        } else {
            console.error(`${reqTag(data)}Preprocessor "${preprocessor[0]}" response validation failed!`);
            console.error(`${reqTag(data)}${JSON.stringify(ajv.errors)}`);
        }
    } else if (response.status === 204) {
        console.debug(`${reqTag(data)}Preprocessor "${preprocessor[0]}" not applicable`);
    } else {
        console.error(`${reqTag(data)}Preprocessor "${preprocessor[0]}" responded with status ${response.status}`);
    }
}

async function executeHandler(handler: ServiceInfo, data: Record<string, unknown>): Promise<any[]> {
    return measureExecutionTime(`Handler "${handler[0]}"`, async () => {
        try {
            const resp = await fetch(`http://${handler[0]}:${handler[1]}/handler`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Request-ID": ((data as any)?.request_uuid ?? "") // pass client request_uuid downstream; ok if empty
                },
                body: JSON.stringify(data)
            });

            if (!resp.ok) {
                console.error(`${reqTag(data)}Received ${resp.status} ${resp.statusText} from ${handler[0]}`);
                const result = await resp.json();
                throw result;
            }

            const json = await resp.json() as HandlerResponse;

            if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", json)) {
                // Check each rendering for expected renderers
                const renderers = data["renderers"] as any;
                return json["renderings"].filter((rendering: { type_id: string }) => {
                    const inList = renderers.includes(rendering["type_id"]);
                    if (!inList) {
                        console.warn(
                            `Excluding a rendering of type "${rendering["type_id"]}" from handler "${handler[0]}".\nThis renderer was not in the advertised list for this request.`
                        );
                    }
                    return inList;
                });
            } else {
                console.error(`${reqTag(data)}Handler response failed validation!`);
                throw Error(JSON.stringify(ajv.errors));
            }
        } catch (err) {
            console.error(`${reqTag(data)}Handler "${handler[0]}" execution failed:`, err);
            return [];
        }
    }, reqTag(data));
}

async function executePreprocessor(preprocessor: ServiceInfo, data: Record<string, unknown>): Promise<void> {
    const preprocessorName = preprocessor[0] as string;
    const hashedKey = serverCache.constructCacheKey(data, preprocessorName);
    const cacheTimeOut = preprocessor[3] as number;
    const isModifyRequest = preprocessor[MODIFY_REQUEST_INDEX] as boolean;

    // profile preprocessor lifecycle performance
    await measureExecutionTime(`Preprocessor "${preprocessor[0]}"`, async () => {
        // check if a cached response exists for the current preprocessor
        const cacheResponse = await checkCache(preprocessorName, hashedKey, cacheTimeOut);
        if (cacheResponse && !isModifyRequest) {  // if the response is found in cache, update `data` directly without making any calls
            (data["preprocessors"] as Record<string, unknown>)[cacheResponse["name"]] = cacheResponse["data"];
            return; // cache hit, no further processing is needed
        }

        // fetch the preprocessor response from its endpoint
        const response = await fetchPreprocessorResponse(preprocessor, data);

        // Delegate response handling to `processResponse` - attempt to process the response, validate it, and update data and the cache (if enabled)
        await processResponse(response, preprocessor, data, hashedKey, cacheTimeOut);
    }, reqTag(data));
}

async function runServicesParallel(data: Record<string, unknown>, preprocessors: ServiceInfo[], G: Graph, R: Set<GraphNode>): Promise<{ data: Record<string, unknown>, handlerResults: any[][] }> {
    if (data["preprocessors"] === undefined) {
        data["preprocessors"] = {};
    }

    const handlerResults: any[][] = [];

    // Get unique set of nodes that are running
    const running = Array.from(R)
        .map((service) => executeGraphNode(service, data, handlerResults));

    //Run until no more can run
    await Promise.all(running);

    return { data, handlerResults };
}

// modified executepreprocessor
async function executeGraphNode(service: GraphNode, data: Record<string, unknown>, handlerResults: any[][]): Promise<void> {
    if (service.type === "P") {
        await executePreprocessor(service.value, data);
    } else if (service.type === "H") {
        const result = await executeHandler(service.value, data);
        handlerResults.push(result);  // accumulate result
    }

    const newRun: Promise<void>[] = [];
    for (const child of service.children) {
        child.parents.delete(service);
        if (child.parents.size === 0) {
            newRun.push(executeGraphNode(child, data, handlerResults));
        }
    }
    await Promise.all(newRun);
}

export async function runPreprocessorsParallel(data: Record<string, unknown>, preprocessors: ServiceInfo[]): Promise<Record<string, unknown>> {
    if (data["preprocessors"] === undefined) {
        data["preprocessors"] = {};
    }
    let currentPriorityGroup: number | undefined = undefined;
    const queue: ServiceInfo[] = []; //Microservice queue for preprocessors and handlers


    //function that dequeues everything in the queue at once, executes them and waits for them to finish processing
    const processQueue = async (): Promise<void> => {
        try {
            await Promise.all(queue.map(preprocessor => executePreprocessor(preprocessor, data)));
        } catch (error) {
            console.error(`${reqTag(data)}One or more promises failed at priority group ${currentPriorityGroup}.`, error);
        }
        finally {   //empty the queue
            queue.length = 0;
        }
    };

    for (const preprocessor of preprocessors) {
        //If the priority group changes, process the queue and move to the next group
        if (preprocessor[2] !== currentPriorityGroup) {
            if (queue.length > 0) {
                await processQueue(); //Process everything in the queue
            }
            currentPriorityGroup = Number(preprocessor[2]);
            console.debug(`${reqTag(data)}Now on priority group ${currentPriorityGroup}`);
        }

        //Add the preprocessor to the queue
        queue.push(preprocessor);
    }

    //Process any remaining items in the queue
    if (queue.length > 0) {
        await processQueue();
    }

    return data;
}

export async function runPreprocessors(data: Record<string, unknown>, preprocessors: ServiceInfo[]): Promise<Record<string, unknown>> {
    if (data["preprocessors"] === undefined) {
        data["preprocessors"] = {};
    }
    for (const preprocessor of preprocessors) {
        const controller = new AbortController();
        const timeout = setTimeout(() => {
            controller.abort();
        }, PREPROCESSOR_TIME_MS);

        let resp;
        // get value from cache for each preprocessor if it exists
        const cacheTimeOut = preprocessor[3] as number;
        const preprocessorName = preprocessor[0] as string;
        const hashedKey = serverCache.constructCacheKey(data, preprocessorName);
        const cacheValue = await serverCache.getResponseFromCache(hashedKey);
        if (cacheTimeOut && cacheValue && preprocessorName){
            // add cache value in response
            console.debug(`${reqTag(data)}Response for preprocessor ${preprocessorName} served from cache`);
            const cacheResponse = JSON.parse(cacheValue) as PreprocessorResponse;
            (data["preprocessors"] as Record<string, unknown>)[cacheResponse["name"]] = cacheResponse["data"];
        }
        else {
            // make fetch call to preprocessor since value not found in cache
            try {
                console.debug(`${reqTag(data)}Sending to preprocessor "${preprocessor[0]}"`);
                resp = await measureExecutionTime(`Preprocessor "${preprocessor[0]}"`, async () =>
                    fetch(`http://${preprocessor[0]}:${preprocessor[1]}/preprocessor`, {
                        "method": "POST",
                        "headers": {
                            "Content-Type": "application/json",
                            "X-Request-ID": ((data as any)?.request_uuid ?? "")
                        },
                        "body": JSON.stringify(data),
                        "signal": controller.signal
                    }), reqTag(data)
                );
                clearTimeout(timeout);
            } catch (err) {
                // Most likely a timeout
                console.error(`${reqTag(data)}Error occured fetching from ${preprocessor[0]}`);
                console.error(`${reqTag(data)}`, err);
                continue;
            }

            // OK data returned
            if (resp.status === 200) {
                try {
                    const json = await resp.json() as PreprocessorResponse;
                    if (ajv.validate("https://image.a11y.mcgill.ca/preprocessor-response.schema.json", json)) {
                        if (preprocessor[MODIFY_REQUEST_INDEX] == false) {
                            (data["preprocessors"] as Record<string, unknown>)[json["name"]] = json["data"];
                            // store the value in cache
                            // disable the cache if "ca.mcgill.a11y.image.cacheTimeout" is 0
                            if(cacheTimeOut > 0){
                                const hashedKey =  serverCache.constructCacheKey(data, preprocessorName);
                                console.debug(`Saving Response for ${preprocessorName} in cache with key ${hashedKey}`);
                                await serverCache.setResponseInCache(hashedKey, json["name"], json["data"], cacheTimeOut)
                            }
                        } else {
                            if (json["name"] != NAME_MODIFY_REQUEST) {
                                console.debug(`Pseudo-preprocessor ${preprocessorName} attempted to modify the request, but returned unexpected name ${json["name"]}. Ignoring response.`);
                            } else {
                                for (const [field, value] of Object.entries(json["data"])) {
                                    if (RESTRICTED_FIELDS.includes(field)) {
                                        console.debug(`Pseudo-preprocessor ${preprocessorName} attempted to modify restricted request field '${field}'. Ignoring modification.`);
                                    } else {
                                        data[field] = value;
                                    }
                                }
                                // TODO caching
                            }
                        }
                    } else {
                        console.error(`${reqTag(data)}Preprocessor response failed validation!`);
                        console.error(`${reqTag(data)}${JSON.stringify(ajv.errors)}`);
                    }
                } catch (err) {
                    console.error(`${reqTag(data)}Error occured on fetch from ${preprocessor[0]}`);
                    console.error(`${reqTag(data)}`, err);
                }
            }
            // No Content preprocessor not applicable
            else if (resp.status === 204) {
                continue;
            } else {
                try {
                    const result = await resp.json();
                    throw result;
                } catch (err) {
                    console.error(`${reqTag(data)}Error occured on fetch from ${preprocessor[0]}`);
                    console.error(`${reqTag(data)}`, err);
                }
            }
        }
    }
    return data;
}

export interface PipelineResult {
    response: Record<string, unknown>;
    valid: boolean;
    errors: unknown;
}

export function getRoute(data: Record<string, unknown>): string {
    if (data["route"] === undefined) {
        console.debug(`${reqTag(data)}No route defined in request. Setting default value.`);
        return DEFAULT_ROUTE_NAME;
    } else {
        console.debug(`${reqTag(data)}Route for request set to ${data["route"]}`);
        return data["route"] as string;
    }
}

export async function storeResponse(requestBody: any, response: Record<string, unknown>): Promise<void> {
    const requestPath = path.join(BASE_LOG_PATH, requestBody.request_uuid);
    try {
        await fs.mkdir(requestPath, { recursive: true });
        await fs.writeFile(
            path.join(requestPath, "request.json"),
            JSON.stringify(requestBody)
        );
        await fs.writeFile(
            path.join(requestPath, "response.json"),
            JSON.stringify(response)
        );
        console.debug(`${reqTag(requestBody)}Wrote temporary files to ${requestPath}`);
    } catch (e) {
        console.error(`${reqTag(requestBody)}Error occurred while logging to ${requestPath}`);
        console.error(`${reqTag(requestBody)}`, e);
    }
}

/**
 * Runs the full IMAGE pipeline for an already-validated request:
 * pseudo-preprocessors, preprocessors, and handlers (per the dependency
 * graph and PARALLEL_PREPROCESSORS setting), then assembles and validates
 * the final response. Shared by /render and /mcp.
 *
 * The caller is responsible for validating requestBody against
 * request.schema.json before calling this function.
 */
export async function runPipeline(requestBody: any): Promise<PipelineResult> {
    let data = JSON.parse(JSON.stringify(requestBody));
    const route = getRoute(data);

    const containers = await docker.listContainers();
    //Get the list of filtered containers that are connected to one of the Orchestrator networks
    const connectedContainers = getFilteredContainers(containers);
    const allPreprocessors = getPreprocessorServices(connectedContainers, route);
    const pseudopreprocessors = allPreprocessors.filter(p => p[MODIFY_REQUEST_INDEX] == true);
    const preprocessors = allPreprocessors.filter(p => p[MODIFY_REQUEST_INDEX] == false);
    const handlers = getHandlerServices(connectedContainers, route);

    // Construct pseudo-preprocessor graph
    const pseudoGraph = new Graph();
    const pseudoReady = await pseudoGraph.constructGraph(
        pseudopreprocessors,
        [],
        connectedContainers
    );

    const graph = new Graph();
    //Construct the graph using the handlers and preprocessors
    const readyToRun =  await graph.constructGraph(
        preprocessors,
        handlers,
        connectedContainers
    );
    console.debug(`${reqTag(data)}Preprocessor graph produced successfully.`);

    let handlerResults: any[][];

    // Preprocessors
    if (process.env.PARALLEL_PREPROCESSORS === "ON" || process.env.PARALLEL_PREPROCESSORS === "on") {
        // Deal with pseudo-preprocessors first, if any
        if (pseudoGraph.isAcyclic()) {
            console.debug(`${reqTag(data)}Running pseudo-preprocessors in parallel...`);
            const { data: modifiedData } = await runServicesParallel(data, pseudopreprocessors, pseudoGraph, pseudoReady);
            data = modifiedData;
        } else {
            console.debug(`${reqTag(data)}Dependency graph has cycles, please check for cyclic dependencies in pseudopreprocessors.`);
            console.debug(`${reqTag(data)}Defaulting to serial execution.`);
            data = await runPreprocessors(data, pseudopreprocessors);
        }
        console.debug(`${reqTag(data)}Running preprocessors in parallel...`);
        if (graph.isAcyclic()) {
            console.debug(`${reqTag(data)}Dependency graph passes cycle check.`);
            const result = await runServicesParallel(data, preprocessors, graph, readyToRun);
            handlerResults = result.handlerResults;
        } else {
            console.debug(`${reqTag(data)}Dependency graph has cycles, please check for cyclic dependencies in preprocessors.`);
            console.debug(`${reqTag(data)}Defaulting to serial execution.`);
            data = await runPreprocessorsParallel(data, preprocessors);
            handlerResults = await Promise.all(
                handlers.map(handler => executeHandler(handler, data))
            );
        }

    } else {
        console.debug(`${reqTag(data)}Running pseudo-preprocessors in series...`);
        data = await runPreprocessors(data, pseudopreprocessors);
        console.debug(`${reqTag(data)}Running preprocessors in series...`);
        data = await runPreprocessors(data, preprocessors);
        handlerResults = await Promise.all(
            handlers.map(handler => executeHandler(handler, data))
        );
    }

    const renderings = (handlerResults as HandlerResponse["renderings"][])
        .reduce((a, b) => a.concat(b), [])
        .sort((a) => (a.description === "Server status message.") ? -1 : 0);

    const response = {
        request_uuid: requestBody.request_uuid,
        timestamp: Math.round(Date.now() / 1000),
        renderings: renderings
    };

    const valid = ajv.validate("https://image.a11y.mcgill.ca/response.schema.json", response);
    // AJV stores errors on the shared validator; copy them before any await
    // allows another request to overwrite them.
    const errors = valid ? null : JSON.parse(JSON.stringify(ajv.errors));
    if (valid) {
        console.debug(`${reqTag(requestBody)}Valid response generated.`);
    } else {
        console.debug(`${reqTag(requestBody)}Failed to generate a valid response (did the schema change?)`);
    }

    return { response, valid: valid as boolean, errors };
}
