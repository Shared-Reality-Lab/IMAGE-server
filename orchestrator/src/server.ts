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
import fs from "fs/promises";
import path from "path";
import hash from "object-hash";
import { validate, version } from "uuid";
import { performance } from "perf_hooks";
import { ajv } from "./ajv";
import { docker, getPreprocessorServices } from "./docker";
import { BASE_LOG_PATH, getRoute, reqTag, runPipeline, runPreprocessors, runPreprocessorsParallel, storeResponse } from "./pipeline";

export const app = express();

const port = 8080;

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/render", (req: express.Request, res: express.Response) => {
    const requestBody = req.body; // capture req.body early
    const totalRequestStartTime = performance.now();

    // build a tag directly from the body (request_uuid) for early logs/catch blocks
    const bodyTag = reqTag(requestBody); // this makes early logs traceable before we clone to `data`

    console.debug(`${bodyTag}Received request`); // prefix the first request log with req id (from body)

    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", requestBody)) {
        runPipeline(requestBody).then(async ({ response, valid, errors }) => {
            if (valid) {
                res.json(response);
            } else {
                res.status(500).send(errors);
            }
            // Preserve /render behavior: send the response before waiting for
            // optional request/response persistence.
            if (process.env.STORE_IMAGE_DATA === "on" || process.env.STORE_IMAGE_DATA === "ON") {
                await storeResponse(requestBody, response);
            }
            const totalRequestEndTime = performance.now();
            console.log(`${bodyTag}TotalRequestExecutionTime execution_time_ms=${(totalRequestEndTime - totalRequestStartTime).toFixed(2)}ms`);
        }).catch(e => {
            // use the bodyTag derived from requestBody for early/exception logs
            console.error(`${bodyTag}${e}`);
            const message = (e && e.name !== undefined) ? e.name + ": " + e.message : String(e);
            res.status(500).send(message);
            const totalRequestEndTime = performance.now();
            console.log(`${bodyTag}TotalRequestExecutionTime execution_time_ms=${(totalRequestEndTime - totalRequestStartTime).toFixed(2)}ms`);
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
                console.debug(`${reqTag(data)}Running preprocessors in parallel...`);
                return runPreprocessorsParallel(data, preprocessors);
            } else {
                console.debug(`${reqTag(data)}Running preprocessors in series...`);
                return runPreprocessors(data, preprocessors);
            }
        }).then(data => {
            if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", data)) {
                console.debug(`${reqTag(data)}Valid response generated.`);
                res.json(data);
            } else {
                console.debug(`${reqTag(data)}Failed to generate a valid response.`);
                res.status(500).send(ajv.errors);
            }
        }).catch(e => {
            console.error(`${reqTag(data)}${e}`);
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

if (require.main === module) {
    const server = app.listen(port, () => {
        console.log(`Started server on port ${port}`);
    });

    const serverTimeout = parseInt(process.env.SERVER_TIMEOUT || "");
    if (!isNaN(serverTimeout) && serverTimeout > 0) {
        server.requestTimeout = serverTimeout;
        server.headersTimeout = serverTimeout + 10000;
        server.timeout = serverTimeout;
        console.log(`Server timeouts set to ${serverTimeout}ms`);
    }
}
