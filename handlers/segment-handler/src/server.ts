import Ajv from "ajv";
import express from "express";
import fetch from "node-fetch";
import fs from "fs/promises";
import osc from "osc";
import { v4 as uuidv4 } from "uuid";

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";
import descriptionJSON from "./schemas/services/supercollider/tts-description.schema.json";
import segmentJSON from "./schemas/services/supercollider/tts-segment.schema.json";

import * as utils from "./utils";

const ajv = new Ajv({
    "schemas": [ querySchemaJSON, handlerResponseJSON, definitionsJSON, ttsRequestJSON, ttsResponseJSON, descriptionJSON, segmentJSON ]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/semantic-segmentation-handler-";

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    // Validate the request data (just in case)
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }

    // Check for required preprocessor data
    const preprocessors = req.body["preprocessors"];
    if (!preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]) {
        console.debug("No semantic segmentation data: can't render!");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);

        if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid empty response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
        return;
    }

    // Check for a usable renderer
    const hasSimple = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SimpleAudio");
    const hasSegment = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SegmentAudio");
    if (!hasSimple && !hasSegment) {
        console.warn("Simple and segment audio renderers not supported!");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid empty response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
        return;
    }

    // Going ahead with SimpleAudio and/or SegmentAudio
    // Form TTS announcement for each segment
    const segmentText: string[] = [];
    const segments = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]["segments"];
    if (segments.length === 0) {
        console.warn("No segments were detected, so we can't do anything!");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        res.json(response);
        return;
    }
    for (const segment of segments) {
        segmentText.push(segment["nameOfSegment"]);
    }

    let ttsResponse;
    // Get the TTS file for each audio plus snippet info
    try {
        ttsResponse = await fetch("http://espnet-tts/service/tts/segments", {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
            },
            "body": JSON.stringify({
                "segments": segmentText
            })
        }).then(resp => {
            return resp.json();
        });
        ttsResponse = ttsResponse as Record<string, unknown>;
    } catch (e) {
        console.error(e);
        res.status(500).json({"error": e.message});
        return;
    }

    // Add TTS location for name of each segment
    let runningOffset = 0;
    const durations = ttsResponse["durations"] as number[];
    for (let i = 0; i < segments.length; i++) {
        segments[i]["audio"] = {
            "offset": runningOffset,
            "duration": durations[i]
        };
        runningOffset += durations[i];
    }

    // TODO adjustment of contours
    // Sort contour points
    for (let i = 0; i < segments.length; i++) {
        const ref = segments[i]["coord"][0];
        const center = segments[i]["centroid"];
        segments[i]["coord"].sort(
            (a: [number, number], b: [number, number]) => {
                return utils.getContourRefAngle(center, ref, a) < utils.getContourRefAngle(center, ref, b);
            }
        );
    }
    // Order contours bottom-to-top to not conflict with rising pitches of sonification
    // Note: normalized coordinates follow graphics convention!
    type centroid = [number, number];
    segments.sort((a: { "centroid": centroid }, b: { "centroid": centroid }) => {
        return b["centroid"][1] - a["centroid"][1];
    });

    const scData = {
        "segments": segments,
        "ttsFileName": "",
    };

    // Put it all together
    let inFile: string, outFile: string, jsonFile: string;
    const renderings: Record<string, unknown>[] = [];
    const dataURI = ttsResponse["audio"] as string;
    // First turn data URI into a writable binary buffer
    await fetch(dataURI).then(resp => {
        return resp.arrayBuffer();
    }).then(async (buf) => {
        // Write files for SuperCollider
        inFile = filePrefix + Math.round(Date.now()) + ".wav";
        await fs.writeFile(inFile, Buffer.from(buf));
        scData["ttsFileName"] = inFile;
        jsonFile = filePrefix + Math.round(Date.now()) + ".json";
        await fs.writeFile(jsonFile, JSON.stringify(scData));
        outFile = filePrefix + uuidv4() + ".wav";
        await fs.writeFile(outFile, "");
        await fs.chmod(outFile, 0o664);

        console.log("Forming OSC...");
        const oscPort = new osc.UDPPort({
            "remoteAddress": "supercollider",
            "remotePort": scPort,
            "localAddress": "0.0.0.0"
        });

        // Send response and receive reply or timeout
        return Promise.race<{"name": string, "offset": number, "duration": number}[]>([
            new Promise<{"name": string, "offset": number, "duration": number}[]>((resolve, reject) => {
                try {
                    // Handle response from SuperCollider
                    oscPort.on("message", (oscMsg: osc.OscMessage) => {
                        const arg = oscMsg["args"] as osc.Argument[];
                        if (arg[0] === "done") {
                            const respArr: {"name": string, "offset": number, "duration": number}[] = [];
                            if ((arg.length) > 1 && ((arg.length - 1) % 3 == 0)) {
                                for (let i = 1; i < arg.length; i += 3) {
                                    respArr.push({
                                        "name": arg[i] as string,
                                        "offset": arg[i+1] as number,
                                        "duration": arg[i+2] as number
                                    });
                                }
                            }
                            oscPort.close();
                            resolve(respArr);
                        }
                        else if (arg[0] === "fail") {
                            oscPort.close();
                            reject(oscMsg);
                        }
                    });
                    // Send command when able
                    oscPort.on("ready", () => {
                        oscPort.send({
                            "address": "/render/semanticSegmentation",
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
            new Promise<{"name": string, "offset": number, "duration": number}[]>((resolve, reject) => {
                setTimeout(() => {
                    try {
                        oscPort.close();
                    } catch (_) { /* noop */ }
                    reject("Timeout");
                }, 5000);
            })
        ]);
    }).then(async (segArray) => {
        const buffer = await fs.readFile(outFile);
        // TODO detect MIME type from file
        const dataURL = "data:audio/wav;base64," + buffer.toString("base64");
        if (hasSimple) {
            renderings.push({
                "type_id": "ca.mcgill.a11y.image.renderer.SimpleAudio",
                "confidence": 50, // TODO magic number
                "description": "A sonification of segments detected in the image.",
                "data": {
                    "audio": dataURL
                }
            });
        }
        if (segArray.length > 0 && hasSegment) {
            renderings.push({
                "type_id": "ca.mcgill.a11y.image.renderer.SegmentAudio",
                "confidence": 50, // TODO magic number
                "description": "Navigable sonifications of segments detected in the image.",
                "data": {
                    "audioFile": dataURL,
                    "audioInfo": segArray
                }
            });
        }
    }).catch(err => {
        console.error(err);
    }).finally(() => {
        // Delete files off of the disk
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

    const response = utils.generateEmptyResponse(req.body["request_uuid"]);
    response["renderings"] = renderings;

    if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
        res.json(response);
    } else {
        console.error("Failed to generate a valid response.");
        console.error(ajv.errors);
        res.status(500).json(ajv.errors);
    }
});

// Run the server
app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
