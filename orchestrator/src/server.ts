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
import express from "express";
import fetch, { Response } from "node-fetch";
import Ajv2020 from "ajv";
import fs from "fs/promises";
import path from "path";
import hash from "object-hash";
import { validate, version } from "uuid";
import { performance } from "perf_hooks"; // https://nodejs.org/api/perf_hooks.html
import os from "os"; // Import 'os' to get the number of CPU cores
import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import preprocessorResponseSchemaJSON from "./schemas/preprocessor-response.schema.json";
import responseSchemaJSON from "./schemas/response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import { docker, getPreprocessorServices, getHandlerServices, DEFAULT_ROUTE_NAME, getFilteredContainers } from "./docker";
import { ServerCache } from "./server-cache";

interface PreprocessorResponse {
    name: string;
    data: Record<string, unknown>;
}

interface HandlerResponse {
    renderings: Array<{
        description: string;
        type_id: string;
    }>;
}

export type ServiceInfo = (string | number | boolean)[]
import { Graph, GraphNode, printGraph } from "./graph";

const app = express();
const serverCache = new ServerCache();
const memjsClient = serverCache.memjsClient;

console.debug("memcached server", memjsClient.servers);
// variable to store mapping of service (as defined in docker-compose) and preprocessor-id (as returned in the reponse)
const SERVICE_PREPROCESSOR_MAP : Record<string, string> = {};
const port = 8080;
const ajv = new Ajv2020({
    "schemas": [definitionsJSON, querySchemaJSON, responseSchemaJSON, handlerResponseSchemaJSON, preprocessorResponseSchemaJSON]
});

const PREPROCESSOR_TIME_MS = (!isNaN(parseInt(process.env.PREPROCESSOR_TIMEOUT || ""))) ? parseInt(process.env.PREPROCESSOR_TIMEOUT || "") : 15000;

const BASE_LOG_PATH = path.join("/var", "log", "IMAGE");

const MODIFY_REQUEST_INDEX = 4;  // The index returned by getPreprocessorServices corresponding to modifyRequest
const NAME_MODIFY_REQUEST = "ca.mcgill.a11y.image.request";
const RESTRICTED_FIELDS = [
    "request_uuid",
    "timestamp",
    "preprocessors",
];

app.use(express.json({limit: process.env.MAX_BODY}));

async function measureExecutionTime<T>(label: string, fn: () => Promise<T>): Promise<T> {
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
        // Normalize CPU Usage as a percentage of wall-clock duration and number of cores -- https://stackoverflow.com/questions/74776323/trying-to-get-normalized-cpu-usage-for-node-process
        const normalizedCpuUsage = parseFloat(((cpuTime / (duration * coreCount)) * 100).toFixed(2)); // normalized CPU usage

        console.log(`timestamp=${new Date().toISOString()} label=${label} execution_time_ms=${duration}ms cpu_time_ms=${cpuTime}ms normalized_cpu_usage_percent=${normalizedCpuUsage}%`);
        // To extract the log and store into a dictionary --> log_dict = {item.split('=')[0]: item.split('=')[1] for item in log.split(' ')}  
    }
}

async function checkCache(preprocessorName: string, hashedKey: string, cacheTimeOut: number): Promise<Response | null> {
    if (process.env.CACHE_OVERRIDE != undefined && preprocessorName) {
       const filepath = path.join(process.env.CACHE_OVERRIDE, hashedKey);
       try {
            // Load cache override and serve
            const contents = await fs.readFile(filepath);
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
        return JSON.parse(cacheValue) as Response;
    }

    return null; // cache miss
}

async function fetchPreprocessorResponse(preprocessor: ServiceInfo, data: Record<string, unknown>): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), PREPROCESSOR_TIME_MS);
    try {
        const response = await fetch(`http://${preprocessor[0]}:${preprocessor[1]}/preprocessor`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
            signal: controller.signal,
        });
        clearTimeout(timeout);
        return response;
    } catch (err) {
        console.error(`Error occurred while fetching from preprocessor "${preprocessor[0]}"`);
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
                // store preprocessor name returned in SERVICE_PREPROCESSOR_MAP 
                SERVICE_PREPROCESSOR_MAP[preprocessor[0] as string] = preprocessorName;
                // store data in cache
                // disable the cache if "ca.mcgill.a11y.image.cacheTimeout" is 0
                if (cacheTimeOut > 0) {
                    console.debug(`Saving response for ${preprocessorName} in cache with key ${hashedKey}`);
                    await serverCache.setResponseInCache(hashedKey, JSON.stringify(jsonResponse["data"]), cacheTimeOut);
                }
            } else {
                // Verify that name in response matches expectation.
                if (jsonResponse["name"] != NAME_MODIFY_REQUEST) {
                    console.debug(`Pseudo-preprocessor ${preprocessor[0]} attempted to modify the request, but returned unexpected name ${jsonResponse["name"]}. Ignoring response.`);
                } else {
                    // Make transmitted modifications, within reason.
                    for (const [field, value] of Object.entries(jsonResponse["data"])) {
                        if (RESTRICTED_FIELDS.includes(field)) {
                            console.debug(`Pseudo-preprocessor ${preprocessor[0]} attempted to modify restricted request field '${field}'. Ignoring modification.`);
                        } else {
                            data[field] = value;
                        }
                    }
                    // TODO caching
                }
            }
        } else {
            console.error(`Preprocessor "${preprocessor[0]}" response validation failed!`);
            console.error(JSON.stringify(ajv.errors));
        }
    } else if (response.status === 204) {
        console.debug(`Preprocessor "${preprocessor[0]}" not applicable`);
    } else {
        console.error(`Preprocessor "${preprocessor[0]}" responded with status ${response.status}`);
    }
}

async function executeHandler(handler: ServiceInfo, data: Record<string, unknown>): Promise<any[]> {
    return measureExecutionTime(`Handler "${handler[0]}"`, async () => {
        try {
            const resp = await fetch(`http://${handler[0]}:${handler[1]}/handler`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            if (!resp.ok) {
                console.error(`Received ${resp.status} ${resp.statusText} from ${handler[0]}`);
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
                console.error("Handler response failed validation!");
                throw Error(JSON.stringify(ajv.errors));
            }
        } catch (err) {
            console.error(`Handler "${handler[0]}" execution failed:`, err);
            return [];
        }
    });
}

async function executePreprocessor(preprocessor: ServiceInfo, data: Record<string, unknown>): Promise<void> {
    const preprocessorName = SERVICE_PREPROCESSOR_MAP[preprocessor[0] as string] || '';
    const hashedKey = serverCache.constructCacheKey(data, preprocessorName);
    const cacheTimeOut = preprocessor[3] as number;
    const isModifyRequest = preprocessor[MODIFY_REQUEST_INDEX] as boolean;

    // profile preprocessor lifecycle performance
    await measureExecutionTime(`Preprocessor "${preprocessor[0]}"`, async () => {
        // check if a cached response exists for the current preprocessor
        const cacheResponse = await checkCache(preprocessorName, hashedKey, cacheTimeOut);
        if (cacheResponse && !isModifyRequest) {  // if the response is found in cache, update `data` directly without making any calls
            (data["preprocessors"] as Record<string, unknown>)[preprocessorName] = cacheResponse;
            return; // cache hit, no further processing is needed
        }

        // fetch the preprocessor response from its endpoint
        const response = await fetchPreprocessorResponse(preprocessor, data);

        // Delegate response handling to `processResponse` - attempt to process the response, validate it, and update data and the cache (if enabled) 
        await processResponse(response, preprocessor, data, hashedKey, cacheTimeOut);
    });
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

async function runPreprocessorsParallel(data: Record<string, unknown>, preprocessors: ServiceInfo[]): Promise<Record<string, unknown>> {
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
            console.error(`One or more of the promises failed at priority group ${currentPriorityGroup}.`, error);
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
            console.debug(`Now on priority group ${currentPriorityGroup}`);
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

async function runPreprocessors(data: Record<string, unknown>, preprocessors: ServiceInfo[]): Promise<Record<string, unknown>> {
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
        const preprocessorName = SERVICE_PREPROCESSOR_MAP[preprocessor[0] as string] || '';
        const hashedKey = serverCache.constructCacheKey(data, preprocessorName);
        const cacheValue = await serverCache.getResponseFromCache(hashedKey);
        if (cacheTimeOut && cacheValue && preprocessorName){
            // add cache value in response
            console.debug(`Response for preprocessor ${preprocessorName} served from cache`);
            const cacheResponse = JSON.parse(cacheValue) as Response;
            (data["preprocessors"] as Record<string, unknown>)[preprocessorName] = cacheResponse;
        }
        else {
            // make fetch call to preprocessor since value not found in cache
            try {
                console.debug("Sending to preprocessor \"" + preprocessor[0] + "\"");
                resp = await measureExecutionTime(`Preprocessor "${preprocessor[0]}"`, async () =>
                    fetch(`http://${preprocessor[0]}:${preprocessor[1]}/preprocessor`, {
                        "method": "POST",
                        "headers": {
                            "Content-Type": "application/json"
                        },
                        "body": JSON.stringify(data),
                        "signal": controller.signal
                    })
                );
                clearTimeout(timeout);
            } catch (err) {
                // Most likely a timeout
                console.error("Error occured fetching from " + preprocessor[0]);
                console.error(err);
                continue;
            }

            // OK data returned
            if (resp.status === 200) {
                try {
                    const json = await resp.json() as PreprocessorResponse;
                    if (ajv.validate("https://image.a11y.mcgill.ca/preprocessor-response.schema.json", json)) {
                        if (preprocessor[MODIFY_REQUEST_INDEX] == false) {
                            (data["preprocessors"] as Record<string, unknown>)[json["name"]] = json["data"];
                            // store preprocessor name returned in SERVICE_PREPROCESSOR_MAP
                            SERVICE_PREPROCESSOR_MAP[preprocessor[0] as string] = json["name"];
                            // store the value in cache
                            // disable the cache if "ca.mcgill.a11y.image.cacheTimeout" is 0
                            if(cacheTimeOut > 0){
                                const hashedKey =  serverCache.constructCacheKey(data, json["name"]);
                                console.debug(`Saving Response for ${json["name"]} in cache with key ${hashedKey}`);
                                await serverCache.setResponseInCache(hashedKey, JSON.stringify(json["data"]), cacheTimeOut)
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
                        console.error("Preprocessor response failed validation!");
                        console.error(JSON.stringify(ajv.errors));
                    }
                } catch (err) {
                    console.error("Error occured on fetch from " + preprocessor[0]);
                    console.error(err);
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
                    console.error("Error occured on fetch from " + preprocessor[0]);
                    console.error(err);
                }
            }
        }
    }
    return data;
}

function finalizeResponse(results: any[][],requestBody: any,res: express.Response): Record<string, unknown> {
    const renderings = (results as HandlerResponse["renderings"][])
        .reduce((a, b) => a.concat(b), [])
        .sort((a) => (a.description === "Server status message.") ? -1 : 0);

    const response = {
        request_uuid: requestBody.request_uuid,
        timestamp: Math.round(Date.now() / 1000),
        renderings: renderings
    };

    if (ajv.validate("https://image.a11y.mcgill.ca/response.schema.json", response)) {
        console.debug("Valid response generated.");
        res.json(response);
    } else {
        console.debug("Failed to generate a valid response (did the schema change?)");
        res.status(500).send(ajv.errors);
    }
    
    return response;
}

async function storeResponse(requestBody: any, req: express.Request, response: Record<string, unknown>) {
    const requestPath = path.join(BASE_LOG_PATH, requestBody.request_uuid);
    try {
        await fs.mkdir(requestPath, { recursive: true });
        await fs.writeFile(
            path.join(requestPath, "request.json"),
            JSON.stringify(req.body)
        );
        await fs.writeFile(
            path.join(requestPath, "response.json"),
            JSON.stringify(response)
        );
        console.debug("Wrote temporary files to " + requestPath);
    } catch (e) {
        console.error("Error occurred while logging to " + requestPath);
        console.error(e);
    }
}



function getRoute(data: Record<string, unknown>): string {
    if (data["route"] === undefined) {
        console.debug("No route defined in request. Setting default value.");
        return DEFAULT_ROUTE_NAME;
    } else {
        console.debug("Route for request set to " + data["route"]);
        return data["route"] as string;
    }
}

app.post("/render", (req: express.Request, res: express.Response) => {
    console.debug("Received request");
    const requestBody = req.body; // capture req.body early
    const totalRequestStartTime = performance.now();

    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", requestBody)) {
        // get route variable or set to default
        let data = JSON.parse(JSON.stringify(requestBody));
        const route = getRoute(data);
        // get list of preprocessors and handlers
        docker.listContainers().then(async (containers) => {
            let response: Record<string, unknown> | null = null;
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
            console.debug("Preprocessor graph produced successfully.");

            // Preprocessors
            if (process.env.PARALLEL_PREPROCESSORS === "ON" || process.env.PARALLEL_PREPROCESSORS === "on") {
                // Deal with pseudo-preprocessors first, if any
                if (pseudoGraph.isAcyclic()) {
                    console.debug("Running pseudo-preprocessors in parallel...");
                    const { data: modifiedData, handlerResults: tmpHResults} = await runServicesParallel(data, pseudopreprocessors, pseudoGraph, pseudoReady);
                    data = modifiedData;
                } else {
                    console.debug("Dependency graph has cycles, please check for cyclic dependencies in pseudopreprocessors.");
                    console.debug("Defaulting to serial execution.");
                    data = await runPreprocessors(data, pseudopreprocessors);
                }
                console.debug("Running preprocessors in parallel...");
                if(graph.isAcyclic()){
                    console.debug("Dependency graph passes cycle check.");
                    const { data: processedData, handlerResults } = await runServicesParallel(data, preprocessors, graph, readyToRun);
                    response = finalizeResponse(handlerResults, requestBody, res);
                    
                } else {
                    console.debug("Dependency graph passes failed check. Please ensure that the preprocesors don't have cyclic dependencies.");
                    console.debug("Using priority level execution...");
                    data = await runPreprocessorsParallel(data, preprocessors);
                    const handlerResults: any[][] = await Promise.all(
                        handlers.map(handler => executeHandler(handler, data))
                    );                
                    response = finalizeResponse(handlerResults, requestBody, res);
                }

            } else {
                console.debug("Running pseudo-preprocessors in series...");
                data = await runPreprocessors(data, pseudopreprocessors);
                console.debug("Running preprocessors in series...");
                data = await runPreprocessors(data, preprocessors);
                const handlerResults: any[][] = await Promise.all(
                    handlers.map(handler => executeHandler(handler, data))
                );                
                response = finalizeResponse(handlerResults, requestBody, res);
            }
            if (process.env.STORE_IMAGE_DATA === "on" || process.env.STORE_IMAGE_DATA === "ON") {
                await storeResponse(requestBody, req, response as Record<string, unknown>);
            }
            const totalRequestEndTime = performance.now();
            console.log(`TotalRequestExecutionTime execution_time_ms=${(totalRequestEndTime - totalRequestStartTime).toFixed(2)}ms`);

        }).catch(e => {
            console.error(e);
            res.status(500).send(e.name + ": " + e.message);
            const totalRequestEndTime = performance.now();
            console.log(`TotalRequestExecutionTime execution_time_ms=${(totalRequestEndTime - totalRequestStartTime).toFixed(2)}ms`);

        });
    } else {
        res.status(400).send(ajv.errors);
    }
});

app.post("/render/preprocess", (req: express.Request, res: express.Response) => {
    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        const data = req.body;
        const route = getRoute(data);
        // get list of preprocessors and handlers
        docker.listContainers().then(async (containers) => {
            const preprocessors = getPreprocessorServices(containers, route);
            
            if (process.env.PARALLEL_PREPROCESSORS === "ON" || process.env.PARALLEL_PREPROCESSORS === "on") {
                console.debug("Running preprocessors in parallel...");
                return runPreprocessorsParallel(data, preprocessors);
            } else {
                console.debug("Running preprocessors in series...");
                return runPreprocessors(data, preprocessors);
            }
        }).then(data => {
            if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", data)) {
                console.debug("Valid response generated.");
                res.json(data);
            } else {
                console.debug("Failed to generate a valid response.");
                res.status(500).send(ajv.errors);
            }
        }).catch(e => {
            console.error(e);
            res.status(500).send(e.name + ":" + e.message);
        });
    } else {
        res.status(400).send(ajv.errors);
    }
});

app.get("/authenticate/:uuid/:check", async (req: express.Request, res: express.Response) => {
    if (process.env.STORE_IMAGE_DATA === "on" || process.env.STORE_IMAGE_DATA === "ON") {
        // Check for valid uuidv4 path
        const uuid = req.params.uuid;
        const check = req.params.check;
        if (!(validate(uuid) && version(uuid) == 4)) {
            console.log("Submitted id " + uuid + " was not UUID-v4.");
            res.status(400).end();
            return;
        }

        // Check if ID exists
        await fs.readFile(path.join(BASE_LOG_PATH, uuid, "request.json"), { encoding: "utf-8" }).then(async (contents) => {
            let sourceCheck: string;
            try {
                const obj = JSON.parse(contents);
                sourceCheck = hash.sha1(obj);
            } catch (e) {
                console.error(e);
                res.status(500).end();
                return
            }
            if (sourceCheck === check) {
                await fs.writeFile(path.join(BASE_LOG_PATH, uuid, "auth"), "");
                res.status(200).end();
                return;
            }
        }).catch(e => {
            if (e.code !== "ENOENT") {
                console.error(e);
            }
        });

        res.status(401).end();
    } else {
        console.warn("Auth endpoint hit while off!");
        res.status(503).end();
    }
});

// Healthcheck endpoint
app.get("/health", (req: express.Request, res: express.Response) => {
    res.status(200).json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});

