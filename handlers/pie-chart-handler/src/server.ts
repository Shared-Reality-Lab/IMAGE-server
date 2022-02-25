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
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.
 */
import express from "express";
import Ajv from "ajv";
import fs from "fs/promises";
import osc from "osc";
import { v4 as uuidv4 } from "uuid";

// JSON imports
import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import descriptionJSON from "./schemas/services/supercollider/pie-chart.schema.json";
import rendererDefJSON from "./schemas/renderers/definitions.json";
import simpleAudioJSON from "./schemas/renderers/simpleaudio.schema.json";

const ajv = new Ajv({
    "schemas": [querySchemaJSON, handlerResponseJSON, definitionsJSON, descriptionJSON, rendererDefJSON, simpleAudioJSON]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/pie-chart-handler-";

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    console.debug("Received request");
    // Check for good data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }
    // Check for the preprocessor data we need
    const preprocessors = req.body["preprocessors"];
    if (!(
        preprocessors["ca.mcgill.a11y.image.preprocessor.chart"]
        && preprocessors["ca.mcgill.a11y.image.preprocessor.chart"]["type"] === "Pie Chart"
    )) {
        console.debug("Not enough data to generate a rendering or not applicable.");
        const response = {
            "request_uuid": req.body["request_uuid"],
            "timestamp": Math.round(Date.now() / 1000),
            "renderings": []
        };
        if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid empty response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
        return;
    }

    if (!req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SimpleAudio")) {
        console.warn("Simple audio renderer not supported.");
        const response = {
            "request_uuid": req.body["request_uuid"],
            "timestamp": Math.round(Date.now() / 1000),
            "renderings": []
        };
        if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid empty response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
        return;
    }

    // Send data to supercollider
    const scData = {
        "wedges": preprocessors["ca.mcgill.a11y.image.preprocessor.chart"]["sectors"].map((e: Record<string, unknown>) => e["value"]),
    };
    const renderings: Record<string, unknown>[] = [];
    const outFile = filePrefix + uuidv4() + ".wav";
    await fs.writeFile(outFile, "");
    await fs.chmod(outFile, 0o664);
    const jsonFile = filePrefix + Math.round(Date.now()) + ".json";
    await fs.writeFile(jsonFile, JSON.stringify(scData));

    console.log("Forming OSC...");
    const oscPort = new osc.UDPPort({
        "remoteAddress": "supercollider",
        "remotePort": scPort,
        "localAddress": "0.0.0.0",
        "localPort": 0  // This will request a free port
    });
    try {
        await Promise.race<string>([
            new Promise<string>((resolve, reject) => {
                try {
                    oscPort.on("message", (oscMsg: osc.OscMessage) => {
                        const arg = oscMsg["args"] as osc.Argument[];
                        if (arg[0] === "done") {
                            oscPort.close();
                            resolve(outFile);
                        }
                        else if (arg[0] === "fail") {
                            oscPort.close();
                            reject(oscMsg);
                        }
                    });
                    oscPort.on("ready", () => {
                        oscPort.send({
                            "address": "/render/charts/pie",
                            "args": [
                                { "type": "s", "value": jsonFile },
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
            }),
            new Promise<string>((resolve, reject) => {
                setTimeout(() => {
                    try {
                        oscPort.close();
                    } catch (_) { /* noop */ }
                    reject("Timeout");
                }, 5000);
            })
        ]);
        await fs.readFile(outFile).then(buffer => {
            const dataURL = "data:audio/wav;base64," + buffer.toString("base64");
            const r = {
                "type_id": "ca.mcgill.a11y.image.renderer.SimpleAudio",
                "confidence": 50,
                "description": "A spatial sonification of a pie chart without label information.",
                "data": {
                    "audio": dataURL
                }
            };
            if (ajv.validate("https://image.a11y.mcgill.ca/renderers/simpleaudio.schema.json", r["data"])) {
                renderings.push(r);
            } else {
                console.error("Failed to generate a valid empty response!");
                console.error(ajv.errors);
            }
        });
    } catch (err) {
        console.error(err);
    } finally {
        if (jsonFile !== undefined) {
            fs.access(jsonFile).then(() => { return fs.unlink(jsonFile); }).catch(() => { /* noop */ });
        }
        if (outFile !== undefined) {
            fs.access(outFile).then(() => { return fs.unlink(outFile); }).catch(() => { /* noop */ });
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
        console.error("Failed to generate a valid response.");
        console.error(ajv.errors);
        res.status(500).json(ajv.errors);
    }
});

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
