import express from "express";
import fetch from "node-fetch";
import Ajv from "ajv/dist/2020";

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import responseSchemaJSON from "./schemas/response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import { docker, getPreprocessorServices, getHandlerServices } from "./docker";

const app = express();
const port = 8080;
const ajv = new Ajv({
    "schemas": [definitionsJSON, querySchemaJSON, responseSchemaJSON, handlerResponseSchemaJSON]
});

const PREPROCESSOR_TIME_MS = 15000;

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/atp/render", (req, res) => {
    if (ajv.validate("https://bach.cim.mcgill.ca/atp/request.schema.json", req.body)) {
        // get list of preprocessors and handlers
        docker.listContainers().then(async (containers) => {
            const preprocessors = getPreprocessorServices(containers);
            const handlers = getHandlerServices(containers);

            // TODO do things with these services
            // Preprocessors run in order
            const data = req.body;
            if (data["preprocessors"] === undefined) {
                data["preprocessors"] = {};
            }
            for (const preprocessor of preprocessors) {
                const controller = new AbortController();
                const timeout = setTimeout(() => {
                    controller.abort();
                }, PREPROCESSOR_TIME_MS);

                await fetch(`http://${preprocessor[0]}:${preprocessor[1]}/atp/preprocessor`, {
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": JSON.stringify(data),
                    "signal": controller.signal
                }).then(async (resp) => {
                    if (resp.ok) {
                        return resp.json();
                    } else {
                        let result = await resp.json();
                        throw result;
                    }
                }).then(json => {
                    data["preprocessors"][json["name"]] = json["data"];
                }).catch(err => {
                    // Try to continue...
                    // tslint:disable-next-line:no-console
                    console.error("Error occured on fetch");
                    // tslint:disable-next-line:no-console
                    console.error(err);
                });
            }

            // Handlers
            const promises = handlers.map(handler => {
                return fetch(`http://${handler[0]}:${handler[1]}/atp/handler`, {
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": JSON.stringify(data)
                }).then(async (resp) => {
                    if (resp.ok) {
                        return resp.json();
                    } else {
                        // tslint:disable-next-line:no-console
                        console.error(resp);
                        let result = await resp.json();
                        throw result;
                    }
                }).then(json => {
                    if (ajv.validate("https://bach.cim.mcgill.ca/atp/handler-response.schema.json", json)) {
                        return json["renderings"];
                    } else {
                        // tslint:disable-next-line:no-console
                        console.error("Handler response failed validation!");
                        throw Error(JSON.stringify(ajv.errors));
                    }
                }).catch(err => {
                    // tslint:disable-next-line:no-console
                    console.error(err);
                    return [];
                });
            });

            return Promise.all(promises);
        }).then(results => {
            let renderings = results.reduce((a, b) => a.concat(b), []);
            const response = {
                "request_uuid": req.body.request_uuid,
                "timestamp": Math.round(Date.now() / 1000),
                "renderings": renderings
            }
            if (ajv.validate("https://bach.cim.mcgill.ca/atp/response.schema.json", response)) {
                // tslint:disable-next-line:no-console
                console.debug("Valid response generated.");
                res.json(response);
            } else {
                // tslint:disable-next-line:no-console
                console.debug("Failed to generate a valid response (did the schema change?)");
                res.status(500).send(ajv.errors);
            }
        }).catch(e => {
            // tslint:disable-next-line:no-console
            console.error(e);
            res.status(500).send(e.name + ": " + e.message);
        });
    } else {
        res.status(400).send(ajv.errors);
    }
});

app.listen(port, () => {
    // tslint:disable-next-line:no-console
    console.log(`Started server on port ${port}`);
});
