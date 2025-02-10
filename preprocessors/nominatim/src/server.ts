/*
 * Copyright (c) 2023 IMAGE Project, Shared Reality Lab, McGill University
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
import { piiLogger } from "./config/logging_utils";

import querySchemaJSON from "./schemas/request.schema.json";
import preprocessorResponseJSON from "./schemas/preprocessor-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import nominatimJSON from "./schemas/preprocessors/nominatim.schema.json";

const ajv = new Ajv({
    "schemas": [ querySchemaJSON, preprocessorResponseJSON, definitionsJSON, nominatimJSON ]
});

const app = express();
const port = 80;

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/preprocessor", async (req, res) => {
    console.debug("Received request");
    // Validate the request data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        piiLogger.pii(`Validation error: ${JSON.stringify(ajv.errors)}`);
        res.status(400).json(ajv.errors);
        return;
    }

    if (!("coordinates" in req.body)) {
        console.debug("Coordinates not available, cannot make a request for reverse geocode.");
        res.sendStatus(204);
        return;
    }

    const coordinates = req.body["coordinates"];

    const nominatimServer = ("NOMINATIM_SERVER" in process.env) ? process.env.NOMINATIM_SERVER : "https://nominatim.openstreetmap.org";

    const requestUrl = new URL(`./reverse?lat=${coordinates["latitude"]}&lon=${coordinates["longitude"]}&format=jsonv2`, nominatimServer);
    console.debug("Sending request to " + requestUrl.href);

    try {
        const json = await fetch(requestUrl.href)
            .then(async response => {
                const result = await response.json();
                if (response.ok) {
                    return result;
                } else {
                    throw new Error(result);
                }
            });
        const response = {
            "request_uuid": req.body.request_uuid,
            "timestamp": Math.round(Date.now() / 1000),
            "name": "ca.mcgill.a11y.image.preprocessor.nominatim",
            "data": json
        };
        if (ajv.validate("https://image.a11y.mcgill.ca/preprocessor-response.schema.json", response)) {
            if (ajv.validate("https://image.a11y.mcgill.ca/preprocessors/nominatim.schema.json", response["data"])) {
                console.debug("Valid response generated.");
                res.json(response);
            } else {
                console.error("Nominatim preprocessor data failed validation (possibly not an object?)");
                piiLogger.pii(`Validation error: ${JSON.stringify(ajv.errors)}`);
                res.status(500).json(ajv.errors);
            }
        } else {
            console.error("Failed to generate a valid response");
            piiLogger.pii(`Validation error: ${JSON.stringify(ajv.errors)} | Response: ${JSON.stringify(response)}`);
            res.status(500).json(ajv.errors);
        }
    } catch (e) {
        console.error("Unexpected error occured.");
        piiLogger.pii(`${(e as Error).message}`);
        res.status(500).json({"message": (e as Error).message});
    }
});

app.get("/health", (req, res) => {
    res.status(200).json({ status: "healthy", timestamp: new Date().toISOString() });
});

app.listen(port, () => {
    console.log("Started server on port " + port);
});
