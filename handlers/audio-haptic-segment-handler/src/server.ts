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
import osc from "osc";
import { v4 as uuidv4 } from "uuid";
import Articles from "articles";
import pluralize from "pluralize"

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";
import descriptionJSON from "./schemas/services/supercollider/tts-description.schema.json";
import segmentJSON from "./schemas/services/supercollider/tts-segment.schema.json";
import rendererDefJSON from "./schemas/renderers/definitions.json";
import segmentAudioHapticsJSON from "./segmentaudiohapticscombined.schema.json";

import * as utils from "./utils";

const ajv = new Ajv({
    "schemas": [ querySchemaJSON, 
        handlerResponseJSON, 
        definitionsJSON, 
        ttsRequestJSON, 
        ttsResponseJSON, 
        descriptionJSON, 
        segmentJSON, 
        rendererDefJSON, 
        segmentAudioHapticsJSON ]
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

    // *******************************************************
    // Check for preprocessor data
    // *******************************************************
    const preprocessors = req.body["preprocessors"];
    const preSemSeg = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]
    const preObjDet = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]

    if (!preObjDet && !preSemSeg) {
        console.debug("No semantic segmentation and object detection data: can't render!");
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

    // *******************************************************
    // Check for renderer availability
    // *******************************************************
    // const hasSegmentAudioHaptic = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SegmentAudioHaptics");
    // if (!hasSegmentAudioHaptic) {
    //     console.warn("Segment audio-haptic renderers not supported!");
    //     const response = utils.generateEmptyResponse(req.body["request_uuid"]);
    //     if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
    //         res.json(response);
    //     } else {
    //         console.error("Failed to generate a valid empty response!");
    //         console.error(ajv.errors);
    //         res.status(500).json(ajv.errors);
    //     }
    //     return;
    // }

    //const hapticInfo: any = [];//: ({ centroids: number[]; coordinates: number[]; }[] | { text: string; centroids: number[]; coords: number[]; }[])[] = []; //: { centroids: number[]; coordinates: number[]; }[] = [];
    const hapticInfo = [];
    const hapticObjInfo = [];
    const hapticSegInfo = [];
    let audioInfo;

    // *******************************************************
    // Check that we have at least one segment
    // *******************************************************
    const segments = preSemSeg["segments"];
    if (segments.length !== 0) {
        
        // *******************************************************
        // Get segment info
        // *******************************************************
        const ttsText: string[] = [];
        for (const segment of segments) {
            ttsText.push(segment["nameOfSegment"]);

            // Grab coordinates for haptic
            const contourPoints: number[] = segment["coord"];
            const center: number[] = segment["centroid"];
            const data = {
                "centroid": center,
                "coordinates": contourPoints 
            }
            hapticSegInfo.push(data);
        }

        // Array of arrays for semantic info
        hapticInfo.push(hapticSegInfo);

        // *******************************************************
        // Call TTS service for segment info
        // *******************************************************
        // let ttsResponse;
        // try {
        //     ttsResponse = await getTTS(ttsText);
        // } catch (e) {
        //     console.error(e);
        //     res.status(500).json({"error": (e as Error).message});
        // }
        // ttsResponse = ttsResponse as Record<string, unknown>;

        let ttsResponse;
        // Get the TTS file for each audio plus snippet info
        try {
            ttsResponse = await fetch("http://espnet-tts/service/tts/segments", {
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                },
                "body": JSON.stringify({
                    "segments": ttsText
                })
            }).then(resp => {
                return resp.json();
            });
            ttsResponse = ttsResponse as Record<string, unknown>;
        } catch (e) {
            console.error(e);
            res.status(500).json({"error": (e as Error).message});
            return;
        }

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

            const center = segments[i]["centroid"];
            const ref = segments[i]["coord"][0];
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

        pushAudioInfo(ttsResponse, scData, audioInfo);
    } else {
        console.warn("No segments were detected, skipping to objection detection.");
    }

    // *******************************************************
    // Object detection
    // *******************************************************
    const objects = req.body["preprocessors"]["ca.mcgill.a11y.image.preprocessor.objectDetection"]["objects"]
    if (objects.length !== 0) {

        for (const obj of objects) {
            const centroid: number[] = obj["centroid"]
            const dimensions: number[] = obj["dimensions"]

            // For haptics
            const data = {
                "centroid": centroid,
                "coordinates": dimensions
            }
            hapticObjInfo.push(data)
        }
        hapticInfo.push(hapticObjInfo);

        // *******************************************************
        // TTS for object detection
        // *******************************************************

        // Form TTS segments
        // const sceneData = preprocessors["ca.mcgill.a11y.image.preprocessor.sceneRecognition"];
        // Removing scenes due to server#167.
        const sceneData: any = undefined;
        const secondClassifierData = preprocessors["ca.mcgill.a11y.image.preprocessor.secondCategoriser"];
        let ttsIntro;
        if (sceneData && sceneData["categories"].length > 0) {
            let sceneName = sceneData["categories"][0]["name"] as string;
            // '/' is used to have more specific categories
            if (sceneName.includes("/")) {
                sceneName = sceneName.split("/")[0]
            }
            sceneName = sceneName.replace("_", " ").trim();
            const articled = Articles.articlize(sceneName);
            ttsIntro = `This picture of ${articled} contains`;
        } else if (secondClassifierData) {
            const category: string = secondClassifierData["category"];
            if (category === "indoor" || category === "outdoor") {
                ttsIntro = `This ${category} picture contains`;
            } else {
                ttsIntro = "This picture contains";
            }
        } else {
            ttsIntro = "This picture contains";
        }

        const staticSegments = [ttsIntro, "with", "and"];
        const ttsSegments = Array.from(staticSegments);
        const groupData = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"];
        for (const object of objects["objects"]) {
            const articled = Articles.articlize(object["type"].trim());
            ttsSegments.push(`${articled}`);
        }
        for (const group of groupData["grouped"]) {
            const exId = group["IDs"][0];
            const exObjs = objects["objects"].filter((obj: Record<string, unknown>) => {
                return obj["ID"] == exId;
            });
            const sType = (exObjs.length > 0) ? (exObjs[0]["type"]) : "object";
            const pType = pluralize(sType.trim());
            const num = group["IDs"].length;
            ttsSegments.push(`${num.toString()} ${pType}`);
        }

        // let ttsResponse;
        // try {
        //     ttsResponse = await getTTS(ttsSegments);
        // } catch (e) {
        //     console.error(e);
        //     res.status(500).json({"error": (e as Error).message});
        // }
        // ttsResponse = ttsResponse as Record<string, unknown>;
        let ttsResponse;
        // Get the TTS file for each audio plus snippet info
        try {
            ttsResponse = await fetch("http://espnet-tts/service/tts/segments", {
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                },
                "body": JSON.stringify({
                    "segments": ttsSegments
                })
            }).then(resp => {
                return resp.json();
            });
            ttsResponse = ttsResponse as Record<string, unknown>;
        } catch (e) {
            console.error(e);
            res.status(500).json({"error": (e as Error).message});
            return;
        }

        const durations = (ttsResponse as Record<string, unknown>)["durations"] as number[];
        const joining: Record<string, unknown> = {};
        const intro = {
            "offset": 0,
            "duration": durations[0]
        };
        let runningOffset = durations[0];
        for (let i = 1; i < staticSegments.length; i++) {
            joining[staticSegments[i]] = {
                "offset": runningOffset,
                "duration": durations[i]
            };
            runningOffset += durations[i];
        }

        const scData = {
            "audioTemplate": {
                "intro": intro,
                "joining": joining
            },
            "objects": objects["objects"],
            "groups": groupData["grouped"],
            "ordering": "leftToRight",
            "ttsFileName": ""
        };

        let durIdx = staticSegments.length;
        for (const object of scData["objects"]) {
            object["audio"] = {
                "offset": runningOffset,
                "duration": durations[durIdx]
            };
            runningOffset += durations[durIdx];
            durIdx += 1;
        }
        for (const group of scData["groups"]) {
            group["audio"] = {
                "offset": runningOffset,
                "duration": durations[durIdx]
            };
            runningOffset += durations[durIdx];
            durIdx += 1;
        }
        pushAudioInfo(ttsResponse, scData, audioInfo);
    } else {
        console.warn("No objects were detected, so we can't do anything!");
    }

    //TODO: require image?
    const image = req.body.image;
    const r = {
         "type_id": "ca.mcgill.a11y.image.renderer.SegmentAudioHaptics",
        "confidence": 50, // TODO magic number
        "description": "Navigable segment sonifications and tracing detected in the image.",
        "data": {
            "image": image,
            "audio": audioInfo,
            "haptic": hapticInfo
        }       
    };

    const renderings: Record<string, unknown>[] = [];

    if (ajv.validate("https://image.a11y.mcgill.ca/renderers/segmentaudiohaptics.schema.json", r["data"])) {
        renderings.push(r);
    } else {
        console.error(ajv.errors);
        throw ajv.errors;
    }

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


/** Returns TTS json. */
async function getTTS(ttsText: string[]) {
    return fetch("http://espnet-tts/service/tts/segments", {
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
        },
        "body": JSON.stringify({
            "segments": ttsText
        })
    }).then(response => response.json() as Promise<{ audio: string, durations: number[] }>);
}
/** Pushes SuperCollider audio data to passed audioArray. */
async function pushAudioInfo(ttsResponse: any, scData: any, audioArray: any) {

    let inFile: string, outFile: string, jsonFile: string;
    //const renderings: Record<string, unknown>[] = [];
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
    }).then(async (array) => {
        const buffer = await fs.readFile(outFile);
        // TODO detect MIME type from file
        const dataURL = "data:audio/wav;base64," + buffer.toString("base64");

        if (array.length > 0) {
            const data = {
                "audioFile": dataURL,
                "audioInfo": array
            }
            audioArray.push(data);
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
}

// Run the server
app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
