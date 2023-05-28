import express from "express";
import Ajv from "ajv";
import fs from "fs/promises";
import osc from "osc";
import { v4 as uuidv4 } from "uuid";
import { LatLonVectors as LatLon } from "geodesy";

// JSON imports
import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";
import descriptionJSON from "./schemas/services/supercollider/tts-description.schema.json";
import rendererDefJSON from "./schemas/renderers/definitions.json";
import simpleAudioJSON from "./schemas/renderers/simpleaudio.schema.json";

const ajv = new Ajv({
    "schemas": [querySchemaJSON, handlerResponseJSON, definitionsJSON, ttsRequestJSON, ttsResponseJSON, descriptionJSON, rendererDefJSON, simpleAudioJSON]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/autour-handler-";
const filterCategories = [89]; // Remove OSM way segments

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    console.debug("Request received!");
    // Check for good data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }
    // Check for the preprocessor data we need
    const preprocessors = req.body["preprocessors"];
    if (!preprocessors["ca.mcgill.a11y.image.preprocessor.autour"]) {
        console.warn("Not enough data to generate a rendering.");
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

    const autourData = preprocessors["ca.mcgill.a11y.image.preprocessor.autour"];
    if (autourData["places"].length === 0) {
        console.warn("No places detected despite running.");
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

    // Sort and filter POIs
    // Do this before since TTS is time consuming
    const places = autourData["places"].filter((p: { "cat": number }) => !filterCategories.includes(p["cat"]));
    const source = new LatLon(autourData["lat"], autourData["lon"]);
    for (const place of places) {
        const dest = new LatLon(place["ll"][0], place["ll"][1]);
        place["dist"] = source.distanceTo(dest);
        place["azimuth"] = source.bearingTo(dest) * Math.PI / 180;
    }
    places.sort((a: { dist: number }, b: { dist: number }) => a["dist"] - b["dist"]);
    places.splice(20);  // Cut off at 20 for now

    // Form TTS segments
    const ttsIntro = "From due north moving clockwise, there are the following";
    const segments = [ttsIntro];
    for (const place of places) {
        segments.push(place["title"]);
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
        ttsResponse = ttsResponse as Record<string, unknown>;
    } catch (e) {
        console.error(e);
        res.status(500).json({"error": (e as Error).message});
        return;
    }

    const durations = (ttsResponse as Record<string, unknown>)["durations"] as number[];
    let runningOffset = 0;
    const scData = JSON.parse(JSON.stringify(autourData));
    scData["places"] = places;
    scData["ttsFileName"] = "";

    let durIdx = 0;
    scData["intro"] = {
        "offset": runningOffset,
        "duration": durations[durIdx]
    };
    runningOffset += durations[durIdx];
    durIdx += 1;
    for (const place of scData["places"]) {
        place["audio"] = {
            "offset": runningOffset,
            "duration": durations[durIdx]
        };
        runningOffset += durations[durIdx];
        durIdx += 1;
    }

    // Save files and handle process
    let inFile: string, outFile: string, jsonFile: string;
    const renderings: Record<string, unknown>[] = [];
    const dataURI = (ttsResponse as Record<string, unknown>)["audio"] as string;
    await fetch(dataURI).then(resp => {
        return resp.arrayBuffer();
    }).then(async (buf) => {
        inFile = filePrefix + Math.round(Date.now()) + ".wav";
        await fs.writeFile(inFile, Buffer.from(buf));
        scData["ttsFileName"] = inFile;
        jsonFile = filePrefix + Math.round(Date.now()) + ".json";
        await fs.writeFile(jsonFile, JSON.stringify(scData));
        outFile = filePrefix + uuidv4() + ".mp3";
        await fs.writeFile(outFile, "");
        await fs.chmod(outFile, 0o664);

        // Form OSC message
        console.log("Forming OSC...");
        const oscPort = new osc.UDPPort({
            "remoteAddress": "supercollider",
            "remotePort": scPort,
            "localAddress": "0.0.0.0"
        });
        return Promise.race<string>([
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
                            // TODO update this once the function is ready
                            "address": "/render/map/autourPOI",
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
            // Since OSC is unreliable, timeout after 5000
            new Promise<string>((resolve, reject) => {
                setTimeout(() => {
                    try {
                        oscPort.close();
                    } catch (_) { /* noop */ }
                    reject("Timeout");
                    }, 5000);
            })
        ]);
    }).then(out => {
        // Read response audio
        return fs.readFile(out);
    }).then(buffer => {
        // TODO detect mime type from file since we will eventually use a compressed format
        const dataURL = "data:audio/mp3;base64," + buffer.toString("base64");
        renderings.push({
            "type_id": "ca.mcgill.a11y.image.renderer.SimpleAudio",
            "description": "Points of interest around the location in the map.",
            "data": {
                "audio": dataURL
            },
            "metadata": {
                "homepage": "https://image.a11y.mcgill.ca/pages/howto.html#interpretations-maps"
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

    const response = {
        "request_uuid": req.body["request_uuid"],
        "timestamp": Math.round(Date.now() / 1000),
        "renderings": renderings
    };

    console.debug("Sending response.");
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
