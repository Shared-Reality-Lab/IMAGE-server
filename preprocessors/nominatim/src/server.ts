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
import logger, { configureLogging } from "./config/logging_utils";
import fetch from "node-fetch";

import querySchemaJSON from "./schemas/request.schema.json";
import preprocessorResponseJSON from "./schemas/preprocessor-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import nominatimJSON from "./schemas/preprocessors/nominatim.schema.json";

configureLogging();

const ajv = new Ajv({
    "schemas": [ querySchemaJSON, preprocessorResponseJSON, definitionsJSON, nominatimJSON ]
});

const app = express();
const port = 80;

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/preprocessor", async (req, res) => {
    logger.debug("Received request");
    // Validate the request data
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        logger.warn("Request did not pass the schema!");
        logger.pii(`Validation errors: ${JSON.stringify(ajv.errors)}`);
        res.status(400).json(ajv.errors);
        return;
    }

    if (!("coordinates" in req.body)) {
        logger.debug("Coordinates not available, cannot make a request for reverse geocode.");
        res.sendStatus(204);
        return;
    }

    const coordinates = req.body["coordinates"];

    const nominatimServer = ("NOMINATIM_SERVER" in process.env) ? process.env.NOMINATIM_SERVER : "https://nominatim.openstreetmap.org";

    const requestUrl = new URL(`./reverse?lat=${coordinates["latitude"]}&lon=${coordinates["longitude"]}&format=jsonv2`, nominatimServer);
    logger.debug("Sending request to " + requestUrl.href);

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
                logger.error("Preprocessor response validation failed.");
                logger.pii(`Validation errors: ${JSON.stringify(ajv.errors)}`);
                return res.status(500).json(ajv.errors);
            } else {
                logger.error("Nominatim preprocessor data failed validation (possibly not an object?)");
                logger.pii(`Validation errors: ${JSON.stringify(ajv.errors)}`);
                return res.status(500).json(ajv.errors);
            }
        } else {
            logger.error("Failed to generate a valid response");
            res.status(500).json(ajv.errors);
        }
    } catch (e) {
        const errorMessage = (e as Error).message;
        logger.error("Failed to fetch Nominatim data.");
        logger.pii(`Error details: ${errorMessage}`);
        return res.status(500).json({ message: errorMessage });
    }
});

app.listen(port, () => {
    logger.log("Started server on port " + port);
});
