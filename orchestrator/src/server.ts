import express from "express";
import fetch from "node-fetch";
import Ajv2020 from "ajv";

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import responseSchemaJSON from "./schemas/response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import { docker, getPreprocessorServices, getHandlerServices } from "./docker";

const app = express();
const port = 8080;
const ajv = new Ajv2020({
    "schemas": [definitionsJSON, querySchemaJSON, responseSchemaJSON, handlerResponseSchemaJSON]
});

const PREPROCESSOR_TIME_MS = 15000;

app.use(express.json({limit: process.env.MAX_BODY}));

async function runPreprocessors(data: Record<string, unknown>, preprocessors: (string | number)[][]): Promise<Record<string, unknown>> {
    if (data["preprocessors"] === undefined) {
        data["preprocessors"] = {};
    }
    for (const preprocessor of preprocessors) {
        const controller = new AbortController();
        const timeout = setTimeout(() => {
            controller.abort();
        }, PREPROCESSOR_TIME_MS);

        const resp = await fetch(`http://${preprocessor[0]}:${preprocessor[1]}/preprocessor`, {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "body": JSON.stringify(data),
            "signal": controller.signal
        });
        clearTimeout(timeout);

        // OK data returned
        if (resp.status === 200) {
            try {
                const json = await resp.json();
                (data["preprocessors"] as Record<string, unknown>)[json["name"]] = json["data"];
            } catch (err) {
                console.error("Error occured on fetch");
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
                console.error("Error occured on fetch");
                console.error(err);
            }
        }
    }
    return data;
}

app.post("/render", (req, res) => {
    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        // get list of preprocessors and handlers
        docker.listContainers().then(async (containers) => {
            const preprocessors = getPreprocessorServices(containers);
            const handlers = getHandlerServices(containers);

            // TODO do things with these services
            // Preprocessors run in order
            let data = req.body;
            data = await runPreprocessors(data, preprocessors);

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
                        console.error(resp);
                        const result = await resp.json();
                        throw result;
                    }
                }).then(json => {
                    if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", json)) {
                        return json["renderings"];
                    } else {
                        console.error("Handler response failed validation!");
                        throw Error(JSON.stringify(ajv.errors));
                    }
                }).catch(err => {
                    console.error(err);
                    return [];
                });
            });

            return Promise.all(promises);
        }).then(results => {
            const renderings = results.reduce((a, b) => a.concat(b), []);
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
            return runPreprocessors(data, preprocessors);
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

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
