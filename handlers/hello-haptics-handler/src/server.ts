import express from "express";
import Ajv from "ajv";
import * as utils from "./utils";
import querySchemaJSON from "./schemas/request.schema.json";
import helloHapticsSchemaJSON from "./simplehaptics.schema.json"
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import definitionsJSON from "./schemas/definitions.json";
const app = express();
const port = 80;
const ajv = new Ajv({
	"schemas": [querySchemaJSON, definitionsJSON, handlerResponseSchemaJSON, helloHapticsSchemaJSON]
});

function generateRendering(objectData: object, image: string[]) {
	console.log(typeof(objectData));
	return {
		"type_id": "ca.mcgill.a11y.image.renderer.SimpleHaptics",
		"confidence": 0,
		"description": "Bounding box and centroid for haptic round trip example.",
		"metadata": {
			"description": "This was generated by the \"hello haptics handler\" container, to test a roundtrip for haptic renderings. It is not meant to be used in production."
		},
		"data": {
			"image": image,
			"data": objectData
		}
		
	}
}

app.use(express.json({
	limit: process.env.MAX_BODY
}));
app.post("/handler", async (req, res) => {
	// Validate the request data (just in case)
	if(!ajv.validate("https://image.a11y.mcgill.ca/request.schema.json", req.body)) {
		console.warn("Request did not pass the schema!");
		res.status(400).json(ajv.errors);
		return;
	}

	// Check for required preprocessor data
	const preprocessors = req.body["preprocessors"];
	if(!preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]) {
		console.warn("No object detection  data: can't render!");
		const response = utils.generateEmptyResponse(req.body["request_uuid"]);

		if(ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
			res.json(response);
		} else {
			console.error("Failed to generate a valid empty response!");
			console.error(ajv.errors);
			res.status(500).json(ajv.errors);
		}
		return;
	}

	// Check for a usable renderer
	// const hasHaply = req.body["renderers"].includes("ca.mcgill.a11y.image.renderer.SimpleHaptics");
	// if(!hasHaply) {
	// 	console.warn("Simple Haply renderer not supported!");
	// 	const response = utils.generateEmptyResponse(req.body["request_uuid"]);
	// 	if(ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) {
	// 		res.json(response);
	// 	} else {
	// 		console.error("Failed to generate a valid empty response!");
	// 		console.error(ajv.errors);
	// 		res.status(500).json(ajv.errors);
	// 	}
	// 	return;
	// }

	// Going ahead with simplehaptics
	const objects = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]["objects"];
	if(objects.length === 0) {
		console.warn("No objects were detected, so we can't do anything!");
		const response = utils.generateEmptyResponse(req.body["request_uuid"]);
		res.json(response);
		return;
	}

	const objs = [];
	for (const obj of objects) {
		const type: string = obj["type"]
		const centroid: number[] = obj["centroid"]
		const dimensions: number[] = obj["dimensions"]

		const data = {
			"text": type,
			"centroid": centroid,
			"dimensions": dimensions
		}
		objs.push(data)
	}

	const image = req.body.image;

	const rendering:Record<string,unknown>[] = [];
	rendering.push(generateRendering(objs, image));
	
	if(!ajv.validate(helloHapticsSchemaJSON, rendering[0]["data"])) {  
		console.error("Invalid JSON detected");
		console.error(ajv.errors);
		const response = utils.generateEmptyResponse(req.body["request_uuid"]);
		res.json(response);
		return;
	}

	const response = {
		"request_uuid": req.body.request_uuid,
		"timestamp": Math.round(Date.now() / 1000),
		"renderings": rendering
	};
	console.log(response);

	if(ajv.validate("https://image.a11y.mcgill.ca/handler-response.schema.json", response)) { // 
		res.json(response);
	} else {
		res.json(ajv.errors);
		console.error("Failed to generate a valid response.");
		console.error(ajv.errors);
		res.status(500).json(ajv.errors);
	}
});
app.listen(port, () => {
	console.log(`Started server on port ${port}`);
});
