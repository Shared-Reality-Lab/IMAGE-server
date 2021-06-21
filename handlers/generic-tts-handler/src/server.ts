import express from "express";
import Ajv from "ajv/dist/2020";
import fetch from "node-fetch";
import fs from "fs/promises";
import osc from "osc";
import { v4 as uuidv4 } from "uuid";

// JSON imports
import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";
import descriptionJSON from "./schemas/services/supercollider/tts-description.schema.json";

const ajv = new Ajv({
    "schemas": [querySchemaJSON, handlerResponseJSON, definitionsJSON, ttsRequestJSON, ttsResponseJSON, descriptionJSON]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/generic-tts-handler-";

app.use(express.json({limit: process.env.MAX_BODY}));

function calcConfidence(objects: Record<string, unknown>[]): number {
    let confidence = objects.reduce((acc, cur) => {
        acc += cur["confidence"] as number;
        return acc;
    }, 0);
    confidence /= objects.length;
    return confidence;
}

app.post("/atp/handler", async (req, res) => {
    // Check for good data
    if (!ajv.validate("https://bach.cim.mcgill.ca/atp/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }
    // Check for the preprocessor data we need
    const preprocessors = req.body["preprocessors"];
    if (!(
        preprocessors["ca.mcgill.cim.bach.atp.preprocessor.sceneRecognition"]
        && preprocessors["ca.mcgill.cim.bach.atp.preprocessor.objectDetection"]
        // && preprocessors["ca.mcgill.cim.bach.atp.preprocessor.grouping
    )) {
        console.warn("Not enough data to generate a rendering.");
        const response = {
            "request_uuid": req.body["request_uuid"],
            "timestamp": Math.round(Date.now() / 1000),
            "renderings": []
        };
        if (ajv.validate("https://bach.cim.mcgill.ca/atp/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid empty response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
        return;
    }

    // Form TTS segments
    const sceneData = preprocessors["ca.mcgill.cim.bach.atp.preprocessor.sceneRecognition"];
    let ttsIntro;
    if (sceneData["categories"].length > 0) {
        ttsIntro = `This picture of a ${sceneData["categories"][0]["name"]} contains`;
    } else {
        ttsIntro = "This picture contains";
    }

    const staticSegments = [ttsIntro, "with", "and"];
    const segments = Array.from(staticSegments);
    const objectData = preprocessors["ca.mcgill.cim.bach.atp.preprocessor.objectDetection"];
    for (const object of objectData["objects"]) {
        segments.push(`a ${object["type"]}`);
    }

    let ttsResponse;
    try {
        ttsResponse = await fetch("http://espnet-tts/service/tts/segments", {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "body": JSON.stringify({
                "segments": segments
            })
        }).then(resp => {
            return resp.json();
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({"error": e.message});
        return;
    }

    const durations = ttsResponse["durations"];
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
        "objects": objectData["objects"],
        "ordering": "leftToRight",
        "ttsFileName": ""
    };

    let durIdx = staticSegments.length;
    for (const object of scData["objects"]) {
        object["offset"] = {
            "offset": runningOffset,
            "duration": durations[durIdx]
        };
        runningOffset += durations[durIdx];
        durIdx += 1;
    }

    console.log(scData);

    // Save files and handle process
    let inFile: string, outFile: string, jsonFile: string;
    const renderings: Record<string, unknown>[] = [];
    await fetch(ttsResponse["audio"]).then(resp => {
        return resp.arrayBuffer();
    }).then(async (buf) => {
        inFile = filePrefix + Math.round(Date.now()) + ".wav";
        await fs.writeFile(inFile, Buffer.from(buf));
        scData["ttsFileName"] = inFile;
        jsonFile = filePrefix + Math.round(Date.now()) + ".json";
        await fs.writeFile(jsonFile, JSON.stringify(scData));
        outFile = filePrefix + uuidv4() + ".wav";
        await fs.writeFile(outFile, "");
        await fs.chmod(outFile, 0o664);

        // Form OSC message
        const oscPort = new osc.UDPPort({
            "remoteAddress": "supercollider",
            "remotePort": scPort,
            "localAddress": "0.0.0.0"
        });
        return new Promise<string>((resolve, reject) => {
            try {
                oscPort.on("message", (oscMsg) => {
                    console.log(oscMsg);
                    oscPort.close();
                    resolve(outFile);
                });
                oscPort.on("ready", () => {
                    oscPort.send({
                        // TODO update this once the function is ready
                        "address": "/render/genericTTS",
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
        });
    }).then(out => {
        // Read response audio
        return fs.readFile(out);
    }).then(buffer => {
        // TODO detect mime type from file since we will eventually use a compressed format
        const dataURL = "data:audio/wav;base64," + buffer.toString("base64");
        renderings.push({
            "type_id": "ca.mcgill.cim.bach.atp.renderer.SimpleAudio",
            "confidence": calcConfidence(objectData["objects"]),
            "description": "An audio description of elements in the iamge with non-speech effects.",
            "data": {
                "audio": dataURL
            }
        });
    }).catch(err => {
        console.error(err);
    }).finally(() => {
        // Delete our files if they exist on the disk
        if (inFile !== undefined) {
            fs.access(inFile).then(() => { return fs.unlink(inFile); }).catch(() => { /* noop */ });
        }
        if (jsonFile !== undefined) {
            fs.access(jsonFile).then(() => { return fs.unlink(jsonFile); }).catch(() => { /* noop */ });
        }
        if (outFile !== undefined) {
            fs.access(outFile).then(() => { return fs.unlink(jsonFile); }).catch(() => { /* noop */ });
        }
    });
});

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
