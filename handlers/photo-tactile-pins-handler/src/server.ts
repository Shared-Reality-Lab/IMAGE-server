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
import Ajv from "ajv";
import express from "express";
import fetch from "node-fetch";
import { v4 as uuidv4 } from "uuid";
import fs from "fs/promises";
import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
import ttsRequestJSON from "./schemas/services/tts/segment.request.json";
import ttsResponseJSON from "./schemas/services/tts/segment.response.json";
import descriptionJSON from "./schemas/services/supercollider/tts-description.schema.json";
import segmentJSON from "./schemas/services/supercollider/tts-segment.schema.json";
import rendererDefJSON from "./schemas/renderers/definitions.json";
import photoTactilePinsJSON from "./schemas/renderers/tactilepinarray.schema.json";

import * as utils from "./utils";

const ajv = new Ajv({
    "schemas": [querySchemaJSON,
        handlerResponseJSON,
        definitionsJSON,
        ttsRequestJSON,
        ttsResponseJSON,
        descriptionJSON,
        segmentJSON,
        rendererDefJSON,
        photoTactilePinsJSON]
});

const app = express();
const port = 80;
const scPort = 57120;
const filePrefix = "/tmp/sc-store/photo-audio-haptics-handler-";
const padWidth = 60;
const padHeight = 60;

app.use(express.json({ limit: process.env.MAX_BODY }));

app.post("/handler", async (req, res) => {
    console.debug("Received request");
    // Validate the request data (just in case)
    if (!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        console.warn("Request did not pass the schema!");
        res.status(400).json(ajv.errors);
        return;
    }

    const renderings: any = [];

    // *******************************************************
    // Check for preprocessor data
    // *******************************************************
    const preprocessors = req.body["preprocessors"];
    const preSecondCat = preprocessors["ca.mcgill.a11y.image.preprocessor.graphicTagger"];
    const preSemSeg = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]
    const preObjDet = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]
    const preGroupData = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"];

    if (!preObjDet && !preSemSeg && !preGroupData) {
        console.debug("No preprocessor data available: can't render!");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);

        if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid empty response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
        return;
    }

    // *******************************************************
    // Check for renderer availability
    // *******************************************************
    const hasPinArray = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.tactilepinarray");
    if (!hasAudioHaptic) {
        console.warn("Photo audio-haptic renderer not supported!");
        const response = utils.generateEmptyResponse(req.body["request_uuid"]);
        if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
            res.json(response);
        } else {
            console.error("Failed to generate a valid empty response!");
            console.error(ajv.errors);
            res.status(500).json(ajv.errors);
        }
        return;
    }

    // *******************************************************
    // Audio TTS
    // *******************************************************
    // Begin forming text and grab coordinate information for each segment and object.
    // This is variable depending on which preprocessor data is available.
    const ttsData: utils.TTSSegment[] = [];
    const segGeometryData: utils.segGeometryInfo[] = [];
    const objGeometryData: utils.objGeometryInfo[] = [];
   
    ttsData.push({ "value": utils.generateIntro(preSecondCat), "type": "text" });
   
  
   
   
    // Generate rendering title
    const renderingTitle = utils.renderingTitle(preSemSeg, preObjDet, preGroupData);

    if (hasPinArray) {

        // generate bitmap     
        let bitmap = Array(padWidth).fill(null).map(() => Array(padHeight).fill(0)); 
           
    }

    const response = utils.generateEmptyResponse(req.body["request_uuid"]);
    response["renderings"] = renderings;
    console.debug("Sending response");
    if (ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
        res.json(response);
    } else {
        console.error("Failed to generate a valid response.");
        console.error(ajv.errors);
        res.status(500).json(ajv.errors);
    }
});

// Run the server
app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
