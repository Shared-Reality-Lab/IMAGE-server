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
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.
 */
import express from "express";
import Ajv from "ajv";

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

    const rendering = {
        "type_id": "ca.mcgill.a11y.image.renderer.Text",
        "description": "Server status message.",
        "data": {
            "text": process.env.MOTD
        }
    };

    if (!ajv.validate("https://image.a11y.mcgill.ca/renderers/text.schema.json", rendering["data"])) {
        console.error("Failed to generate a valid text rendering!");
        console.error(ajv.errors);
        res.status(500).json(ajv.errors);
        return;
    }
    const response = {
        "request_uuid": req.body["request_uuid"],
        "timestamp": Math.round(Date.now() / 1000),
        "renderings": [rendering]
    };
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
