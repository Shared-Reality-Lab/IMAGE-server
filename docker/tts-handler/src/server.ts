import express from "express";
import Ajv from "ajv/dist/2020";
import fetch from "node-fetch";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import osc from "osc";

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";

// Load necessary schema files for our purposes so we can validate JSON.
const ajv = new Ajv({
    "schemas": [querySchemaJSON, definitionsJSON, handlerResponseSchemaJSON, ttsRequestJSON, ttsResponseJSON]
});

const app = express();
const port = 80;
const scPort = 57120;

app.use(express.json());

app.post("/atp/handler", async (req, res) => {
    if (ajv.validate("https://bach.cim.mcgill.ca/atp/request.schema.json", req.body)) {
        const renderings: Record<string, unknown>[] = [];
        // Check for the preprocessor we need
        if (req.body["preprocessors"]["ca.mcgill.cim.bach.atp.objectDetection.preprocessor"]) {
            const ttsStrings = ["In this picture there is:"];
            try {
                const objectData = req.body["preprocessors"]["ca.mcgill.cim.bach.atp.objectDetection.preprocessor"]["objects"];
                for (const object of objectData) {
                    ttsStrings.push(object["name"]);
                }
            } catch (e) {
                console.error(e);
                ttsStrings.push("an error");
            }

            const ttsRequest = {
                "segments": ttsStrings
            };

            if (!ajv.validate("https://bach.cim.mcgill.ca/atp/tts/segment.request.json", ttsRequest)) {
                console.warn("Failed to validate TTS!");
                console.warn(ajv.errors);
            }

            await fetch("http://espnet-tts/service/tts/segments", {
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": JSON.stringify({
                    "segments": ttsStrings
                })
            }).then(async resp => {
                if (resp.ok) {
                    return resp.json();
                } else {
                    const err = await resp.json();
                    throw err;
                }
            }).then((data: any) => {
                if (ajv.validate("https://bach.cim.mcgill.ca/atp/tts/segment.response.json", data)) {
                    // eslint-disable-next-line @typescript-eslint/no-unused-vars
                    const durations = data["durations"] as number[];
                    const dataURI = data["audio"] as string;

                    return fetch(dataURI);
                } else {
                    throw ajv.errors;
                }
            }).then(resp => {
                return resp.arrayBuffer();
            }).then(buf => {
                const inFile = "/tmp/sc-store/tts-handler-" + Math.round(Date.now()) + ".wav";
                fs.writeFileSync(inFile, Buffer.from(buf));
                const outFile = "/tmp/sc-store/tts-handler-" + uuidv4() + ".wav";

                const oscPort = new osc.UDPPort({
                    "remoteAddress": "supercollider",
                    "remotePort": scPort,
                    "localAddress": "0.0.0.0"
                });
                const promise = new Promise((resolve, reject) => {
                    try {
                        oscPort.on("message", (oscMsg) => {
                            oscPort.close();
                            resolve(oscMsg);
                        });
                        oscPort.on("ready", () => {
                            oscPort.send({
                                "address": "/render",
                                "args": [
                                    { "type": "s", "value": inFile },
                                    { "type": "s", "value": outFile }
                                ]
                            });
                        });
                        oscPort.open();
                    } catch (e) {
                        oscPort.close();
                        reject(e);
                    }
                });
                return promise;
            }).then(done => {
                console.log(done);
            }).catch(err => {
                console.error(err);
            });
        }

        const response = {
            "request_uuid": req.body["request_uuid"],
            "timestamp": Math.round(Date.now() / 1000),
            "renderings": renderings
        };
        if (ajv.validate("https://bach.cim.mcgill.ca/atp/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
    } else {
        console.warn("Request did not pass the schema.");
        res.status(400).json(ajv.errors);
    }
});

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
