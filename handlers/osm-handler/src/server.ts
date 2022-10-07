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
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.
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

const ajv = new Ajv({
    "schemas": [ querySchemaJSON, handlerResponseJSON, definitionsJSON, ttsRequestJSON, ttsResponseJSON, descriptionJSON, segmentJSON, rendererDefJSON, simpleAudioJSON, segmentAudioJSON ]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/osm-handler-";

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    console.debug("Received request");
    // Validate the request data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }

    const renderings: utils.Rendering[] = [];

    // Get preprocessors
    const preprocessors = req.body["preprocessors"];
    const osmPreprocessor = preprocessors["ca.mcgill.a11y.image.preprocessor.openstreetmap"];

    if (osmPreprocessor === undefined || osmPreprocessor.streets.length === 0) {
        console.debug("No streets returned, can't render.");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }

    // Check renderers
    const hasSimple = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SimpleAudio");
    const hasSegment = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SegmentAudio");
    if (!hasSimple && !hasSegment) {
        console.warn("No compatible renderers supported! (SimpleAudio, SegmentAudio)");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }

    // TODO Add TTS for Streets, POIs
    // Create wordlist to TTS
    const osmNames: string[] = [];
    for (const street of osmPreprocessor.streets as utils.Street[]) {
        if (street.street_name !== undefined) {
            osmNames.push(street.street_name);
        } else if (street.street_type !== undefined) {
            osmNames.push(street.street_type);
        }
    }
    if (osmPreprocessor.points_of_interest !== undefined) {
        for (const poi of osmPreprocessor.points_of_interest as utils.POI[]) {
            if (poi.name !== undefined) {
                osmNames.push(poi.name);
            } else {
                osmNames.push(poi.cat);
            }
        }
    }
    // Actually TTS it
    try {
        const ttsResponse = await utils.getTTS(osmNames);

        // Add offset values to relevant points incrementing along way
        // Duration values are in order of appearance and their running sum
        // is the offset.
        let i = 0, offset = 0;
        for (const street of osmPreprocessor.streets as utils.Street[]) {
            if (street.street_name !== undefined || street.street_type !== undefined) {
                street["audio"] = {
                    "offset": offset,
                    "duration": ttsResponse.durations[i]
                };
                offset += ttsResponse.durations[i];
                i += 1;
            }
        }
        if (osmPreprocessor.points_of_interest !== undefined) {
            for (const poi of osmPreprocessor.points_of_interest as utils.POI[]) {
                poi["audio"] = {
                    "offset": offset,
                    "duration": ttsResponse.durations[i]
                };
                offset += ttsResponse.durations[i];
                i += 1;
            }
        }

        const scData = {
            "data": osmPreprocessor,
            "ttsFileName": ""
        };

        // Write out data & audio to file
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
            // Touch file and set to group writeable
            await fs.writeFile(outFile, "");
            await fs.chmod(outFile, 0o664);

            console.log("Forming OSC...");
            return utils.sendOSC(jsonFile, outFile, "supercollider", scPort);
        }).then(async (segArray) => {
            const buffer = await fs.readFile(outFile);
            const dataURL = "data:audio/mp3;base64," + buffer.toString("base64");
            if (hasSegment && segArray.length > 0) {
                const rendering = {
                    "type_id": "ca.mcgill.a11y.image.renderer.SegmentAudio",
                    // TODO split out, get ready for i18n
                    "description": "Audio sweeps of streets with points of interest along them.",
                    "data": {
                        "audioFile": dataURL,
                        "audioInfo": segArray
                    },
                    "metadata": {
                        "homepage": "https://image.a11y.mcgill.ca/pages/howto.html#interpretations-maps"
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
                "description": "Audio sweeps of streets with points of interest along them.",
                "data": {
                    "audio": dataURL
                },
                "metadata": {
                    "homepage": "https://image.a11y.mcgill.ca/pages/howto.html#interpretations-maps"
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
