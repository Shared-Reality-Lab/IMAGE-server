# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
# (Combining new module and original system structure)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# and our Additional Terms along with this program.
# If not, see
# <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.

import jsonschema
import logging
import time
from flask import Flask, request, jsonify
from datetime import datetime
from config.logging_utils import configure_logging
import sys
from utils.image_processing import decode_and_resize_image
from utils.llm import (
    LLMClient,
    MULTISTAGE_DIAGRAM_BASE_PROMPT,
    BOUNDING_BOX_PROMPT_TEMPLATE,
    BOUNDING_BOX_PROMPT_EXAMPLE
    )
from utils.segmentation import SAMClient
from utils.validation import Validator
# from utils.llm.response_schemas import (
#     STAGE_RESPONSE_SCHEMA,
#     BBOX_RESPONSE_SCHEMA
#     )
import json

configure_logging()

app = Flask(__name__)

PREPROCESSOR_NAME = \
    "ca.mcgill.a11y.image.preprocessor.multistage-diagram-segmentation"

ALLOWED_ORIGINS = [
    "https://image.a11y.mcgill.ca/pages/multistage_diagrams.html",
    "https://venissacarolquadros.github.io/",
    "https://unicorn.cim.mcgill.ca/",
]

DATA_SCHEMA = './schemas/preprocessors/multistage-diagram.schema.json'

STAGE_SCHEMA = 'stages.schema.json'
BBOX_SCHEMA = 'bboxes.schema.json'
with open(STAGE_SCHEMA, 'r') as f:
    STAGE_RESPONSE_SCHEMA = json.load(f)
with open(BBOX_SCHEMA, 'r') as f:
    BBOX_RESPONSE_SCHEMA = json.load(f)

try:
    llm_client = LLMClient()
    sam_client = SAMClient()
    validator = Validator(data_schema=DATA_SCHEMA)
    logging.debug("LLM, SAM clients and validator initialized")
except Exception as e:
    logging.error(f"Failed to initialize clients: {e}")
    sys.exit(1)


@app.route("/preprocessor", methods=['POST'])
def process_diagram():
    """
    Main endpoint to process multi-stage textbook diagrams.
    """
    logging.debug("Received request for multi-stage diagram processing.")

    # Get JSON content from the request
    content = request.get_json()

    # 0. Check the URL of the request to avoid processing PII in production
    # Check if there is graphic content to process
    if "graphic" not in content:
        logging.info("No graphic content. Skipping...")
        return jsonify({"error": "No graphic content"}), 204
    if not any(
        content["URL"].startswith(origin) for origin in ALLOWED_ORIGINS
            ):

        logging.info(
            "Request URL does not match expected endpoint. Skipping."
            )
        return jsonify({"error": "Invalid request URL"}), 403

    # 1. Validate Incoming Request
    try:
        validator.validate_request(content)
    except jsonschema.exceptions.ValidationError:
        return jsonify({"error": "Invalid Preprocessor JSON format"}), 400

    request_uuid = content["request_uuid"]
    timestamp = time.time()

    # 2. Resize Base64 Image + create PIL Image
    source = content["graphic"]
    base64_image, pil_image, error = decode_and_resize_image(source)
    if error:
        return jsonify(error), error["code"]

    try:
        # 3. Get base diagram info
        base_json = llm_client.chat_completion(
            prompt=MULTISTAGE_DIAGRAM_BASE_PROMPT,
            image_base64=base64_image,
            json_schema=STAGE_RESPONSE_SCHEMA,
            temperature=0.0,
            parse_json=True
        )

        if base_json is None:
            logging.error("Failed to extract base diagram info from LLM.")
            return jsonify(
                {"error": "Failed to get initial analysis from vision model"}
            ), 503

        # 4. Get Stage Labels for Bounding Box Request
        # Ensure stages is a list and items have 'label'
        stages = [
            stage["label"]
            for stage in base_json.get("stages", [])
            if isinstance(stage, dict) and "label" in stage
            ]
        if not stages or len(stages) == 0:
            logging.info(
                "No stage labels found. Cannot request bounding boxes."
                )
            return jsonify(
                {"error": "No valid stage labels found in the diagram"}
                ), 204

        else:
            logging.pii(f"Identified stages: {stages}")

        bbox_prompt = BOUNDING_BOX_PROMPT_TEMPLATE.format(stages=stages)
        bbox_prompt += BOUNDING_BOX_PROMPT_EXAMPLE

        # 5. Get Bounding Boxes from LLM
        bounding_boxes_data = llm_client.chat_completion(
            prompt=bbox_prompt,
            image_base64=base64_image,
            json_schema=BBOX_RESPONSE_SCHEMA,
            temperature=0.0,
            parse_json=True
        )

        if bounding_boxes_data is None:
            logging.info("Failed to get bounding boxes from LLM.")

        # 6.Segment the graphic and return contours
        final_data_json = sam_client.segment_with_boxes(
            pil_image,
            bounding_boxes_data,
            use_prompts=True,  # Set to True to enable prompted segmentation
            aggregate_by_label=True,
            return_structured=True,  # Return data in schema-compatible format
            base_data=base_json
            )

        if not final_data_json:
            logging.info("Segmentation process did not yield any data.")
            final_data_json = base_json

        # 7. Validate the Generated Data against its specific schema
        try:
            validator.validate_data(final_data_json)
        except jsonschema.exceptions.ValidationError:
            return jsonify("Invalid Preprocessor JSON format"), 500

        # 8. Construct the Final Response
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": PREPROCESSOR_NAME,
            "data": final_data_json
        }

        # 9. Validate Final Response against System Schema
        try:
            validator.validate_response(response)
        except jsonschema.exceptions.ValidationError:
            return jsonify("Invalid Preprocessor JSON format"), 500

        logging.info(
            f"Successfully processed diagram for request {request_uuid}."
            )

        return jsonify(response), 200

    except Exception as e:
        # Catch-all for unexpected errors during the core processing
        logging.error(
            f"An unexpected error occurred during diagram \
                processing for {request_uuid}: {e}", exc_info=True
            )
        return jsonify(
            {"error": "An unexpected internal server error occurred"}
            ), 500


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint to verify if the service is running
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/warmup", methods=["GET"])
def warmup():
    """
    vLLM loads and keeps the specified model in memory on container startup,
    but we keep this endpoint as a health check.
    """
    try:
        logging.info("Warming up LLM and SAM...")

        llm_success = llm_client.warmup()
        sam_success = sam_client.warmup()

        if not llm_success:
            logging.error("LLM warmup failed.")

        if not sam_success:
            logging.error("SAM warmup failed.")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.error(f"Warmup failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
