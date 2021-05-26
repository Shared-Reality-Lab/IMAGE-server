import express from "express";
import Ajv from "ajv/dist/2020";
import fetch from "node-fetch";

import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";

// Load necessary schema files for our purposes so we can validate JSON.
const ajv = new Ajv({
    "schemas": [querySchemaJSON, definitionsJSON, handlerResponseSchemaJSON]
});

const app = express();
const port = 80;

app.use(express.json());

app.post("/atp/handler", async (req, res) => {
    if (ajv.validate("https://bach.cim.mcgill.ca/atp/request.schema.json", req.body)) {
        const renderings: Record<string, unknown>[] = [];
        // Check for the preprocessor we need
        if (req.body["preprocessors"]["ca.mcgill.cim.bach.atp.objectDetection.preprocessor"]) {
            const ttsStrings = ["In this picture there is:"];
            try {
                const objectData = req.body["preprocessors"]["ca.mcgill.cim.bach.atp.objectDetection.preprocessor"]["objects"];
                for (const object of objectData) {
                    ttsStrings.push(object["name"]);
                }
            } catch (e) {
                console.error(e);
                ttsStrings.push("an error");
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
            }).then(data => {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const durations = data["durations"];
                const dataURI = data["audio"];
                renderings.push({
                    "type_id": "ca.mcgill.cim.bach.atp.renderer.SimpleAudio",
                    // TODO Base this on the confidence values from the model when available
                    "confidence": 70,
                    "description": "An audio description of the elements in the image.",
                    "data": {
                        "audio": dataURI
                    }
                });
            }).catch(err => {
                console.error(err);
            });
        }

        const response = {
            "request_uuid": req.body["request_uuid"],
            "timestamp": Math.round(Date.now() / 1000),
            "renderings": renderings
        };
        if (ajv.validate("https://bach.cim.mcgill.ca/atp/handler-response.schema.json", response)) {
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
