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
import Articles from "articles";
import pluralize from "pluralize"

// JSON imports
import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import textJSON from "./schemas/renderers/text.schema.json";

const ajv = new Ajv({
    "schemas": [querySchemaJSON, handlerResponseJSON, definitionsJSON, textJSON]
});

const app = express();
const port = 80;

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/handler", async (req, res) => {
    console.debug("Sending request");
    // Check for good data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }
    // Check for the preprocessor data we need
    const preprocessors = req.body["preprocessors"];
    if (!(
        preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]
        && preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"]
    )) {
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

    const objectData = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"];
    if (objectData["objects"].length === 0) {
        console.warn("No objects detected despite running.");
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

    if (!req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.Text")) {
        console.warn("Text renderer not supported!");
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

    // Collect data
    // const sceneData = preprocessors["ca.mcgill.a11y.image.preprocessor.sceneRecognition"];
    // Scene recognition dropped due to poor/horrible results.
    const sceneData: any = undefined;
    const secondClassifierData = preprocessors["ca.mcgill.a11y.image.preprocessor.graphicTagger"]
    let intro;
    if (sceneData && sceneData["categories"].length > 0) {
        let sceneName = sceneData["categories"][0]["name"] as string;
        // '/' is used to have more specific categories
        if (sceneName.includes("/")) {
            sceneName = sceneName.split("/")[0]
        }
        sceneName = sceneName.replace("_", " ").trim();
        const articled = Articles.articlize(sceneName);
        intro = `This picture of ${articled} contains`;
    } else if (secondClassifierData) {
        const key: string = secondClassifierData["category"];
        if (key === "indoor" || key === "outdoor") {
            intro = `This ${key} picture contains`;
        } else {
            intro = "This picture contains";
        }
    } else {
        intro = "This picture contains";
    }

    const segments = [intro];
    const groupData = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"];
    for (const group of groupData["grouped"]) {
        const exId = group["IDs"][0];
        const exObjs = objectData["objects"].filter((obj: Record<string, unknown>) => {
            return obj["ID"] == exId;
        });
        const sType = (exObjs.length > 0) ? (exObjs[0]["type"]) : "object";
        const pType = pluralize(sType.trim());
        const num = group["IDs"].length;
        segments.push(`${num.toString()} ${pType}`);
    }
    for (const id of groupData["ungrouped"]) {
        const obj = objectData["objects"].find((obj: Record<string, unknown>) => {
            return obj["ID"] == id;
        });
        const sType = obj ? obj["type"] : "object";
        segments.push(`1 ${sType.trim()}`);
    }

    if (groupData["grouped"].length + groupData["ungrouped"].length > 1) {
        segments.splice(-1, 0, "and");
    }
    segments[segments.length - 1] += ".";
    const text = segments.join(" ");
    const response = {
        "request_uuid": req.body["request_uuid"],
        "timestamp": Math.round(Date.now() / 1000),
        "renderings": [
            {
                "type_id": "ca.mcgill.a11y.image.renderer.Text",
                "confidence": 50,
                "description": "A description of the image and its objects.",
                "data": {
                    "text": text
                }
            }
        ]
    };

    console.debug("Sending response");
    if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response) &&
       ajv.validate("https://image.a11y.mcgill.ca/renderers/text.schema.json", response["renderings"][0]["data"])) {
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
