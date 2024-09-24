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
import Ajv from "ajv";
import fetch from "node-fetch";
import { v4 as uuidv4 } from "uuid";
import fs from "fs/promises";
import osc from "osc";

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";
import rendererDefJSON from "./schemas/renderers/definitions.json";
import simpleAudioJSON from "./schemas/renderers/simpleaudio.schema.json";

// Load necessary schema files for our purposes so we can validate JSON.
const ajv = new Ajv({
    "schemas": [querySchemaJSON, definitionsJSON, handlerResponseSchemaJSON, ttsRequestJSON, ttsResponseJSON, rendererDefJSON, simpleAudioJSON]
});

const app = express();
const port = 80;
const scPort = 57120;

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    console.debug("Received request");
    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        const renderings: Record<string, unknown>[] = [];
        // Check for the renderer we need
        if (req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SimpleAudio")) {
            // Check for the preprocessor we need
            let inFile: string, outFile: string;
            if (req.body["preprocessors"]["ca.mcgill.a11y.image.preprocessor.objectDetection"]) {
                const ttsStrings = ["In this picture there is:"];
                try {
                    const objectData = req.body["preprocessors"]["ca.mcgill.a11y.image.preprocessor.objectDetection"]["objects"];
                    for (const object of objectData) {
                        ttsStrings.push(object["type"]);
                    }
                } catch (e) {
                    console.error(e);
                    ttsStrings.push("an error");
                }

                const ttsRequest = {
                    "segments": ttsStrings
                };

                if (!ajv.validate("https://image.a11y.mcgill.ca/services/tts/segment.request.json", ttsRequest)) {
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
                    if (ajv.validate("https://image.a11y.mcgill.ca/services/tts/segment.response.json", data)) {
                        // eslint-disable-next-line @typescript-eslint/no-unused-vars
                        const durations = data["durations"] as number[];
                        const dataURI = data["audio"] as string;

                        return fetch(dataURI);
                    } else {
                        throw ajv.errors;
                    }
                }).then(resp => {
                    return resp.arrayBuffer();
                }).then(async (buf) => {
                    inFile = "/tmp/sc-store/tts-handler-" + Math.round(Date.now()) + ".wav";
                    await fs.writeFile(inFile, Buffer.from(buf));
                    outFile = "/tmp/sc-store/tts-handler-" + uuidv4() + ".wav";
                    await fs.writeFile(outFile, "");
                    await fs.chmod(outFile, 0o664);

                    const oscPort = new osc.UDPPort({
                        "remoteAddress": "supercollider",
                        "remotePort": scPort,
                        "localAddress": "0.0.0.0",
                        "localPort": 0  // This will request a free port
                    });
                    console.log("Sending message...");
                    return new Promise<string>((resolve, reject) => {
                        try {
                            oscPort.on("message", (oscMsg) => {
                                console.log(oscMsg);
                                oscPort.close();
                                resolve(outFile);
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
                            console.error(e);
                            oscPort.close();
                            reject(e);
                        }
                    });
                }).then(out => {
                    console.log("Received response! Reading file..");
                    return fs.readFile(out);
                }).then(buffer => {
                    const dataURL = "data:audio/wav;base64," + buffer.toString("base64");
                    renderings.push({
                        "type_id": "ca.mcgill.a11y.image.renderer.SimpleAudio",
                        "confidence": 70,
                        "description": "An audio description of the elements in the image.",
                        "data": {
                            "audio": dataURL,
                        }
                    });
                    // Verify match of simple audio
                    if (!ajv.validate("https://image.a11y.mcgill.ca/renderers/simpleaudio.schema.json", renderings[renderings.length - 1]["data"])) {
                        console.error("Failed to validate data of simple renderer.");
                        renderings.pop();
                        throw ajv.errors;
                    }
                }).catch(err => {
                    console.error(err);
                }).finally(() => {
                    // Delete the created files (if they exist).
                    if (inFile !== undefined) {
                        fs.access(inFile).then(() => {
                            // it exists
                            return fs.unlink(inFile);
                        }).catch(() => {
                            // didn't exist
                        });
                    }
                    if (outFile !== undefined) {
                        fs.access(outFile).then(() => {
                            return fs.unlink(outFile);
                        }).catch(() => {
                            // didn't exist
                        });
                    }
                });
            }
        }

        const response = {
            "request_uuid": req.body["request_uuid"],
            "timestamp": Math.round(Date.now() / 1000),
            "renderings": renderings
        };
        console.debug("Sending response");
        if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
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
