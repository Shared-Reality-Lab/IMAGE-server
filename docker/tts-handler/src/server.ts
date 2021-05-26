import express from "express";
import Ajv from "ajv/dist/2020";

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

app.post("/atp/handler", (req, res) => {
    if (ajv.validate("https://bach.cim.mcgill.ca/atp/request.schema.json", req.body)) {
        // TODO generate the actual response
        const response = {};
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
