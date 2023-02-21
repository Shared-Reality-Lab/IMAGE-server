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

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import preprocessorResponseSchemaJSON from "./schemas/preprocessor-response.schema.json";
import responseSchemaJSON from "./schemas/response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import { docker, getPreprocessorServices, getHandlerServices } from "./docker";

const app = express();
const port = 8080;
const ajv = new Ajv2020({
    "schemas": [definitionsJSON, querySchemaJSON, responseSchemaJSON, handlerResponseSchemaJSON, preprocessorResponseSchemaJSON]
});

const PREPROCESSOR_TIME_MS = 15000;

const BASE_LOG_PATH = path.join("/var", "log", "IMAGE");

app.use(express.json({limit: process.env.MAX_BODY}));

async function runPreprocessorsParallel(data: Record<string, unknown>, preprocessors: (string | number)[][]): Promise<Record<string, unknown>> {
    if (data["preprocessors"] === undefined) {
        data["preprocessors"] = {};
    }
    let currentPriorityGroup: number | undefined = undefined;
    let promises: Promise<Response | void>[] = [];
    const awaitResponses = async () => {
        const responses = (await Promise.all(promises)).filter(a => a instanceof Response) as Response[];
        for (const resp of responses) {
            // const resp = await promise;
            // OK data returned
            if (resp.status === 200) {
                try {
                    const json = await resp.json();
                    if (ajv.validate("https://image.a11y.mcgill.ca/preprocessor-response.schema.json", json)) {
                        (data["preprocessors"] as Record<string, unknown>)[json["name"]] = json["data"];
                    } else {
                        console.error("Preprocessor response failed validation!");
                        console.error(JSON.stringify(ajv.errors));
                    }
                } catch (err) {
                    console.error("Error occured on fetch from " + resp.url);
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
                    console.error("Error occured on fetch from " + resp.url);
                    console.error(err);
                }
            }
        }
        promises = [];
    };
    for (const preprocessor of preprocessors) {
        if (preprocessor[2] !== currentPriorityGroup) {
            if (promises.length > 0) {
                await awaitResponses();
            }
            currentPriorityGroup = Number(preprocessor[2]);
            console.log("Now on priority group " + currentPriorityGroup);
        }

        const promise = new Promise<Response | void>((resolve) => {
            const controller = new AbortController();
            const timeout = setTimeout(() => {
                controller.abort();
            }, PREPROCESSOR_TIME_MS);
            console.debug("Sending to preprocessor \"" + preprocessor[0] + "\"");
            fetch(`http://${preprocessor[0]}:${preprocessor[1]}/preprocessor`, {
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": JSON.stringify(data),
                "signal": controller.signal
            }).then(r => {
                clearTimeout(timeout);
                resolve(r);
            }).catch(err => {
                console.error("Error occured fetching from " + preprocessor[0]);
                console.error(err);
                resolve();
            });
        });
        promises.push(promise);
    }
    if (promises.length > 0) {
        await awaitResponses();
    }
    return data;
}

async function runPreprocessors(data: Record<string, unknown>, preprocessors: (string | number)[][]): Promise<Record<string, unknown>> {
    if (data["preprocessors"] === undefined) {
        data["preprocessors"] = {};
    }
    for (const preprocessor of preprocessors) {
        const controller = new AbortController();
        const timeout = setTimeout(() => {
            controller.abort();
        }, PREPROCESSOR_TIME_MS);

        let resp;
        try {
            console.debug("Sending to preprocessor \"" + preprocessor[0] + "\"");
            resp = await fetch(`http://${preprocessor[0]}:${preprocessor[1]}/preprocessor`, {
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": JSON.stringify(data),
                "signal": controller.signal
            });
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
                const json = await resp.json();
                if (ajv.validate("https://image.a11y.mcgill.ca/preprocessor-response.schema.json", json)) {
                    (data["preprocessors"] as Record<string, unknown>)[json["name"]] = json["data"];
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
    return data;
}

app.post("/render", (req, res) => {
    console.debug("Received request");
    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        // get list of preprocessors and handlers
        docker.listContainers().then(async (containers) => {
            const preprocessors = getPreprocessorServices(containers);
            const handlers = getHandlerServices(containers);

            // Preprocessors
            let data = JSON.parse(JSON.stringify(req.body));
            if (process.env.PARALLEL_PREPROCESSORS === "ON" || process.env.PARALLEL_PREPROCESSORS === "on") {
                console.debug("Running preprocessors in parallel...");
                data = await runPreprocessorsParallel(data, preprocessors);
            } else {
                console.debug("Running preprocessors in series...");
                data = await runPreprocessors(data, preprocessors);
            }

            // Handlers
            const promises = handlers.map(handler => {
                return fetch(`http://${handler[0]}:${handler[1]}/handler`, {
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": JSON.stringify(data)
                }).then(async (resp) => {
                    if (resp.ok) {
                        return resp.json();
                    } else {
                        console.error(`${resp.status} ${resp.statusText}`);
                        const result = await resp.json();
                        throw result;
                    }
                }).then(json => {
                    if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", json)) {
                        // Check each rendering for expected renderers
                        const renderers = data["renderers"];
                        const renderings = json["renderings"];
                        return renderings.filter((rendering: {"type_id": string}) => {
                            const inList = renderers.includes(rendering["type_id"]);
                            if (!inList) {
                                console.warn("Excluding a renderering of type \"%s\" from handler \"%s\".\nThis renderer was not in the advertised list for this request.", rendering["type_id"], handler[0]);
                            }
                            return inList;
                        });
                    } else {
                        console.error("Handler response failed validation!");
                        throw Error(JSON.stringify(ajv.errors));
                    }
                }).catch(err => {
                    console.error(err);
                    return [];
                });
            });

            console.debug("Waiting for handlers...");
            return Promise.all(promises);
        }).then(async (results) => {
            // Hard code sorting so MOTD appears first...
            const renderings = results.reduce((a, b) => a.concat(b), [])
                .sort((a: { "description": string }) => (a["description"] === "Server status message.") ? -1 : 0);
            const response = {
                "request_uuid": req.body.request_uuid,
                "timestamp": Math.round(Date.now() / 1000),
                "renderings": renderings
            }
            if (ajv.validate("https://image.a11y.mcgill.ca/response.schema.json", response)) {
                console.debug("Valid response generated.");
                res.json(response);
            } else {
                console.debug("Failed to generate a valid response (did the schema change?)");
                res.status(500).send(ajv.errors);
            }

            if (process.env.STORE_IMAGE_DATA === "on" || process.env.STORE_IMAGE_DATA === "ON") {
                const requestPath = path.join(BASE_LOG_PATH, req.body.request_uuid);
                fs.mkdir(
                    requestPath,
                    { recursive: true }
                ).then(() => {
                    return fs.writeFile(
                        path.join(requestPath, "request.json"),
                        JSON.stringify(req.body)
                    );
                }).then(() => {
                    return fs.writeFile(
                        path.join(requestPath, "response.json"),
                        JSON.stringify(response)
                    );
                }).then(() => { console.debug("Wrote temporary files to " + requestPath); })
                .catch(e => {
                    console.error("Error occurred while logging to " + requestPath);
                    console.error(e);
                });
            }
        }).catch(e => {
            console.error(e);
            res.status(500).send(e.name + ": " + e.message);
        });
    } else {
        res.status(400).send(ajv.errors);
    }
});

app.post("/render/preprocess", (req, res) => {
    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        // get list of preprocessors and handlers
        docker.listContainers().then(async (containers) => {
            const preprocessors = getPreprocessorServices(containers);
            const data = req.body;
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

app.get("/authenticate/:uuid/:check", async (req, res) => {
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

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
