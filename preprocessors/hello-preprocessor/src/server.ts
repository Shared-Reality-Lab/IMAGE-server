import express from "express";
import Ajv from "ajv/dist/2020";

import querySchemaJSON from "./schemas/request.schema.json";
import preprocessorResponseSchemaJSON from "./schemas/preprocessor-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";

const app = express();
const port = 8080;
const ajv = new Ajv({
    "schemas": [querySchemaJSON, definitionsJSON, preprocessorResponseSchemaJSON]
});

app.use(express.json({limit: process.env.MAX_BODY}));

app.post("/atp/preprocessor", (req, res) => {
    if (ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
        // tslint:disable-next-line:no-console
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
            // tslint:disable-next-line:no-console
            console.debug("Valid response generated.");
            res.json(response);
        } else {
            // tslint:disable-next-line:no-console
            console.debug("Failed to generate a valid response (did the schema change?)");
            res.status(500).send(ajv.errors);
        }
    } else {
        // tslint:disable-next-line:no-console
        console.debug("Request did not pass the schema.");
        res.status(400).send(ajv.errors);
    }
});

app.listen(port, () => {
    // tslint:disable-next-line:no-console
    console.log(`Started server on port ${port}`);
});
