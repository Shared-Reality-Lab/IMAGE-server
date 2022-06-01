/*
 * Copyright (c) 2022 IMAGE Project, Shared Reality Lab, McGill University
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
import Ajv from "ajv";
import express from "express";
import fetch from "node-fetch";
import fs from "fs/promises";
import { v4 as uuidv4 } from "uuid";

import * as utils from "./utils";

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";
import rendererDefJSON from "./schemas/renderers/definitions.json";
import simpleAudioJSON from "./schemas/renderers/simpleaudio.schema.json";

const ajv = new Ajv({
    "schemas": [ querySchemaJSON, handlerResponseJSON, definitionsJSON, ttsRequestJSON, ttsResponseJSON, rendererDefJSON, simpleAudioJSON ]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/highcharts-handler-";

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    console.debug("Received request");
    // Validate the request data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }

    // Check renderers
    const hasSimple = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SimpleAudio");
    if (!hasSimple) {
        console.warn("No compatible renderers supported! (SimpleAudio)");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }

    if (!("highChartsData" in req.body)) {
        console.debug("No high charts data in this request. Skipping.");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }

    const renderings: Record<string, unknown>[] = [];
    const highChartsData = req.body["highChartsData"];

    const series: { type: string }[] | undefined = highChartsData?.series;
    if (series && series.length === 1) {
        const serie = series[0] as { type: string, data: Record<string, unknown>[] };
        console.log("hello");
	console.log(serie["type"]);
	//console.log(serie["data"][0]);
	if (serie["data"] && serie["data"].length > 0) {
            const data = serie["data"];
            if (serie["type"] === "line" || serie["type"] === "area") {
                // We can work with this
                console.log("Length: " + data.length);
		// console.log("first point", data[0]);
                let title: string;
                if (highChartsData?.title) {
                    title = highChartsData?.title;
                } else {
                    title = "Untitled line chart."
                }

                try {
                    const ttsResponse = await utils.getTTS([title]);
                    const scData = {
                        "audio": {
                            "offset": 0,
                            "duration": ttsResponse.durations[0]
                        },
                        "seriesData": data,
                        "ttsFileName": ""
                    };
                    // Write to file
                    let inFile: string, outFile: string, jsonFile: string;
                    await fetch(ttsResponse["audio"]).then(resp => {
                        return resp.arrayBuffer();
                    }).then(async (buf) => {
                        inFile = filePrefix + req.body["request_uuid"] + ".wav";
                        await fs.writeFile(inFile, Buffer.from(buf));
                        scData["ttsFileName"] = inFile;
                        jsonFile = filePrefix + req.body["request_uuid"] + ".json";
                        await fs.writeFile(jsonFile, JSON.stringify(scData));
                        outFile = filePrefix + uuidv4() + ".mp3";
                        await fs.writeFile(outFile, "");
                        await fs.chmod(outFile, 0o664);

                        console.log("Forming OSC...");
                        return utils.sendOSC(jsonFile, outFile, "supercollider", scPort, "/render/charts/line");
                    }).then(async () => {
                        const buffer = await fs.readFile(outFile);
                        // TODO detect mime type from file
                        const dataURL = "data:audio/mp3;base64," + buffer.toString("base64");
                        const rendering = {
                            "type_id": "ca.mcgill.a11y.image.renderer.SimpleAudio",
                            "description": "Simple Line Chart",
                            "data": {
                                "audio": dataURL
                            },
                            "metadata": {
                                "homepage": "https://image.a11y.mcgill.ca/pages/howto.html#interpretations-charts"
                            }
                        };
                        if (ajv.validate("https://image.a11y.mcgill.ca/renderers/simpleaudio.schema.json", rendering["data"])) {
                            renderings.push(rendering);
                        } else {
                            console.error(ajv.errors);
                        }
                    }).finally(() => {
                        // Delete our files if they exist on the disk
                        if (inFile !== undefined) {
                            fs.access(inFile).then(() => { return fs.unlink(inFile); }).catch(() => { /* noop */ });
                        }
                        if (jsonFile !== undefined) {
                            fs.access(jsonFile).then(() => { return fs.unlink(jsonFile); }).catch(() => { /* noop */ });
                        }
                        if (outFile !== undefined) {
                            fs.access(outFile).then(() => { return fs.unlink(outFile); }).catch(() => { /* noop */ });
                        }
                    });
                } catch(e) {
                    console.error("Failed to generate audio!");
                    console.error(e);
                }
            } else if (serie["type"] === "pie") {
                console.log("Pie chart");
                const segmentNames: string[] = [];
                console.log(data);
		for (const segment of data) {
                    if ("name" in segment) {
                        const name = String(segment["name"]);
                        const value = (("y" in segment) ? String(segment["y"]): "0") + " percent";
                        segmentNames.push(name + ", " + value);
                    } else {
                        segmentNames.push("Unnamed data");
                    }
                }
                try {
                    const ttsResponse = await utils.getTTS(segmentNames);
                    for (let offset=0, i = 0; i < data.length; i++) {
                        data[i]["offset"] = offset;
                        data[i]["duration"] = ttsResponse.durations[i];
                        offset += ttsResponse.durations[i];
                    }
                    const scData = {
                        "seriesData": data,
                        "ttsFileName": ""
                    };
                    // Write to file
                    let inFile: string, outFile:string, jsonFile: string;
                    await fetch(ttsResponse["audio"]).then(resp => {
                        return resp.arrayBuffer();
                    }).then(async (buf) => {
                        inFile = filePrefix + req.body["request_uuid"] + ".wav";
                        await fs.writeFile(inFile, Buffer.from(buf));
                        scData["ttsFileName"] = inFile;
                        jsonFile = filePrefix + req.body["request_uuid"] + ".json";
                        await fs.writeFile(jsonFile, JSON.stringify(scData));
                        outFile = filePrefix + uuidv4() + ".mp3";
                        await fs.writeFile(outFile, "");
                        await fs.chmod(outFile, 0o664);
                        console.log("Forming OSC...");
                        return utils.sendOSC(jsonFile, outFile, "supercollider", scPort, "/render/charts/pie");
                    }).then(async () => {
                        const buffer = await fs.readFile(outFile);
                        const dataURL = "data:audio/mp3;base64," + buffer.toString("base64");
                        const rendering = {
                            "type_id": "ca.mcgill.a11y.image.renderer.SimpleAudio",
                            "description": "Simple Pie Chart",
                            "data": {
                                "audio": dataURL
                            },
                            "metadata": { "homepage": "https://image.a11y.mcgill.ca/pages/howto.html#interpretations-charts" }
                        };
                        if (ajv.validate("https://image.a11y.mcgill.ca/renderers/simpleaudio.schema.json", rendering["data"])) {
                            renderings.push(rendering);
                        } else {
                            console.error(ajv.errors);
                        }
                    }).finally(() => {
                        // Delete our files if they exist on the disk
                        if (inFile !== undefined) {
                            fs.access(inFile).then(() => { return fs.unlink(inFile); }).catch(() => { /* noop */ });
                        }
                        if (jsonFile !== undefined) {
                            fs.access(jsonFile).then(() => { return fs.unlink(jsonFile); }).catch(() => { /* noop */ });
                        }
                        if (outFile !== undefined) {
                            fs.access(outFile).then(() => { return fs.unlink(outFile); }).catch(() => { /* noop */ });
                        }
                    });
                } catch(e) {
                    console.error("Failed to generate audio!");
                    console.error(e);
                }
            }
        }
    }
    const response = utils.generateEmptyResponse(req.body["request_uuid"]);
    response["renderings"] = renderings;
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
    console.log("Started server on port " + port);
});
