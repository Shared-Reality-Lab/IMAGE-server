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
    const sceneData = preprocessors["ca.mcgill.a11y.image.preprocessor.sceneRecognition"];
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

    segments.splice(-1, 0, "and");
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
