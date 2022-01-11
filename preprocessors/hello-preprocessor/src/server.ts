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

import querySchemaJSON from "./schemas/request.schema.json";
import preprocessorResponseSchemaJSON from "./schemas/preprocessor-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";

const app = express();
const port = 8080;
const ajv = new Ajv({
    "schemas": [querySchemaJSON, definitionsJSON, preprocessorResponseSchemaJSON]
});

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/preprocessor", (req, res) => {
    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.debug("Request validated");
        const response = {
            "request_uuid": req.body.request_uuid,
            "timestamp": Math.round(Date.now() / 1000),
            "name": "ca.mcgill.a11y.image.hello.preprocessor",
            "data": {
                "message": "Hello, World!"
            }
        };
        if (ajv.validate("https://image.a11y.mcgill.ca/preprocessor-response.schema.json", response)) {
            console.debug("Valid response generated.");
            res.json(response);
        } else {
            console.debug("Failed to generate a valid response (did the schema change?)");
            res.status(500).send(ajv.errors);
        }
    } else {
        console.debug("Request did not pass the schema.");
        res.status(400).send(ajv.errors);
    }
});

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
