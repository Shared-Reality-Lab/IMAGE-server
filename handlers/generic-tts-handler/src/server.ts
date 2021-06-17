import express from "express";
import Ajv from "ajv/dist/2020";
import fetch from "node-fetch";

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

app.use(express.json({limit: process.env.MAX_BODY}));

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
    const joining: Record<string, any> = {};
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
    res.status(501);
});

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
