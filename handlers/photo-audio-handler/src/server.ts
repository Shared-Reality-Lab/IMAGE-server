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
import descriptionJSON from "./schemas/services/supercollider/tts-description.schema.json";
import segmentJSON from "./schemas/services/supercollider/tts-segment.schema.json";
import rendererDefJSON from "./schemas/renderers/definitions.json";
import simpleAudioJSON from "./schemas/renderers/simpleaudio.schema.json";
import segmentAudioJSON from "./schemas/renderers/segmentaudio.schema.json";
import textJSON from "./schemas/renderers/text.schema.json";

const ajv = new Ajv({
    "schemas": [ querySchemaJSON, handlerResponseJSON, definitionsJSON, ttsRequestJSON, ttsResponseJSON, descriptionJSON, segmentJSON, rendererDefJSON, simpleAudioJSON, segmentAudioJSON, textJSON ]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/photo-audio-handler-";

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    console.debug("Received request");
    // Validate the request data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }

    const renderings = [];

    // Get preprocessors
    const preprocessors = req.body["preprocessors"];
    const secondCat = preprocessors["ca.mcgill.a11y.image.preprocessor.graphicTagger"];
    const semseg = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"];
    const objDet = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"];
    const objGroup = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"];

    // Ignore secondCat since it isn't useful on its own
    if (!(semseg && semseg?.segments) && !(objDet && objDet?.objects) && !objGroup) {
        console.debug("No usable preprocessor data! Can't render.");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }
    // Filter objects
    utils.filterObjectsBySize(objDet, objGroup);

    if (semseg?.segments.length === 0 && objDet?.objects.length === 0) {
        console.debug("No segments or objects detected! Can't render.");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }

    // Check renderers
    const hasText = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.Text");
    const hasSimple = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SimpleAudio");
    const hasSegment = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SegmentAudio");
    if (!hasText && !hasSimple && !hasSegment) {
        console.warn("No compatible renderers supported! (Text, SimpleAudio, SegmentAudio)");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }

    // Begin forming text...
    // This is variable depending on which preprocessor data is available.
    const ttsData: utils.TTSSegment[] = [];
    ttsData.push({"value": utils.generateIntro(secondCat), "type": "text"});
    if (semseg && semseg["segments"].length > 0) {
        // Use all segments returned for now.
        // Filtering may be helpful later.
        ttsData.push(...utils.generateSemSeg(semseg));
        if (objDet && objGroup && objDet["objects"].length > 0) {
            ttsData.push({"value": "It also", "type": "text"});
        }
    }
    if (objDet && objGroup && objDet["objects"].length > 0) {
        ttsData.push(...utils.generateObjDet(objDet, objGroup));
    }

    // Concatenate adjacent text entries
    for (let i = 0; i < ttsData.length - 1; i++) {
        if (ttsData[i].type === "text" && ttsData[i+1].type === "text") {
            ttsData[i].value += " " + ttsData[i+1].value;
            ttsData.splice(i+1, 1);
        }
    }

    // Generate rendering title
    const renderingTitle = utils.renderingTitle(semseg, objDet, objGroup);

    // Construct Text (if requested)
    if (hasText) {
        const textString = ttsData.map(x => x["value"]).join(" ");
        const rendering = {
            "type_id": "ca.mcgill.a11y.image.renderer.Text",
            "description": renderingTitle + " (text only)",
            "data": { "text": textString }
        };
        if (ajv.validate("https://image.a11y.mcgill.ca/renderers/text.schema.json", rendering["data"])) {
            renderings.push(rendering);
        } else {
            console.error("Failed to generate a valid text rendering!");
            console.error(ajv.errors);
            console.warn("Trying to continue...");
        }
    } else {
        console.debug("Skipped text rendering.");
    }

    if (hasSimple || hasSegment) {
        try {
            // Do TTS
            const ttsResponse = await utils.getTTS(ttsData.map(x => x["value"]));
            // Add offset values to data
            for (let i = 0, offset = 0; i < ttsData.length; i++) {
                ttsData[i]["audio"] = {
                    "offset": offset,
                    "duration": ttsResponse.durations[i]
                };
                offset += ttsResponse.durations[i];
            }

            const scData = {
                "data": ttsData,
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
                outFile = filePrefix + uuidv4() + ".flac";
                await fs.writeFile(outFile, "");
                await fs.chmod(outFile, 0o664);

                console.log("Forming OSC...");
                return utils.sendOSC(jsonFile, outFile, "supercollider", scPort);
            }).then(async (segArray) => {
                const buffer = await fs.readFile(outFile);
                // TODO detect mime type from file
                const dataURL = "data:audio/flac;base64," + buffer.toString("base64");
                if (hasSegment && segArray.length > 0) {
                    const rendering = {
                        "type_id": "ca.mcgill.a11y.image.renderer.SegmentAudio",
                        "description": renderingTitle,
                        "data": {
                            "audioFile": dataURL,
                            "audioInfo": segArray
                        }
                    };
                    if (ajv.validate("https://image.a11y.mcgill.ca/renderers/segmentaudio.schema.json", rendering["data"])) {
                        renderings.push(rendering);
                    } else {
                        console.error(ajv.errors);
                    }
                }
                else if (hasSimple) {
                    const rendering = {
                        "type_id": "ca.mcgill.a11y.image.renderer.SimpleAudio",
                        "description": renderingTitle,
                        "data": {
                            "audio": dataURL
                        }
                    };
                    if (ajv.validate("https://image.a11y.mcgill.ca/renderers/simpleaudio.schema.json", rendering["data"])) {
                        renderings.push(rendering);
                    } else {
                        console.error(ajv.errors);
                    }
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

    // Send response

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
