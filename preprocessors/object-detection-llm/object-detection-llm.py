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

import logging
import time
from flask import Flask, request, jsonify
from datetime import datetime
from config.logging_utils import configure_logging
import sys
from utils.image_processing import decode_and_resize_image
from utils.llm import (
    LLMClient, OBJECT_DETECTION_PROMPT
    )
from utils.validation import Validator
import json
import os

configure_logging()

logging.debug("Starting Object Detection LLM Preprocessor...")

app = Flask(__name__)

CONF_THRESHOLD = float(os.environ.get('CONF_THRESHOLD', '0.9'))

PREPROCESSOR_NAME = \
    "ca.mcgill.a11y.image.preprocessor.objectDetection"

DATA_SCHEMA = './schemas/preprocessors/object-detection.schema.json'

BBOX_SCHEMA = 'object-detection.schema.json'
with open(BBOX_SCHEMA, 'r') as f:
    BBOX_RESPONSE_SCHEMA = json.load(f)

try:
    llm_client = LLMClient()
    validator = Validator(data_schema=DATA_SCHEMA)
    logging.debug("LLM client and validator initialized")
except Exception as e:
    logging.error(f"Failed to initialize clients: {e}")
    sys.exit(1)


def normalize_bbox(bbox, width, height):
    """
    Normalize bounding box coordinates to [0,1] range
    """
    x1, y1, x2, y2 = bbox
    return [
        x1 / width,
        y1 / height,
        x2 / width,
        y2 / height
    ]


def filter_objects_by_confidence(objects, threshold):
    """
    Filter objects based on confidence score threshold
    and replace underscores in labels with spaces.

    Args:
        objects (list): List of detected objects with confidence scores
        threshold (float): Minimum confidence score (0-1)

    Returns:
        list: Filtered list of objects meeting the confidence threshold
    """
    filtered = []
    for obj in objects:
        if obj.get("confidence", 0) >= threshold:
            obj['type'] = obj['type'].replace('_', ' ')
            filtered.append(obj)

    # Renumber IDs sequentially after filtering
    for idx, obj in enumerate(filtered):
        obj['ID'] = idx

    logging.debug(
        f"Filtered {len(objects)} objects to {len(filtered)} "
        f"objects with confidence >= {threshold}"
    )
    return filtered


@app.route("/preprocessor", methods=['POST'])
def detect_objects():
    """
    Main endpoint to detect objects in graphics.
    """
    logging.debug("Received request for object detection.")

    # Get JSON content from the request
    content = request.get_json()

    # Check if there is graphic content to process
    if "graphic" not in content:
        logging.info("No graphic content. Skipping...")
        return jsonify({"error": "No graphic content"}), 204

    # Validate Incoming Request via shared Validator
    ok, _ = validator.check_request(content)
    if not ok:
        return jsonify({"error": "Invalid Preprocessor JSON format"}), 400

    # Determine if the content is a photo, collage, or illustration
    # based on the categoriser output
    preprocess_output = content["preprocessors"]
    categoriser = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
    if categoriser in preprocess_output:
        categoriser_output = preprocess_output[categoriser]
        categoriser_tags = categoriser_output["categories"]
        if not categoriser_tags["photo"] and not categoriser_tags["collage"] \
           and not categoriser_tags["illustration"]:
            logging.info("Not a photo, collage, or illustration. Skipping...")
            return "", 204

    request_uuid = content["request_uuid"]
    timestamp = time.time()

    # Resize Base64 Image + create PIL Image
    source = content["graphic"]
    base64_image, pil_image, error = decode_and_resize_image(source)
    if error:
        return jsonify(error), error["code"]

    try:
        # Get object info
        object_json = llm_client.chat_completion(
            prompt=OBJECT_DETECTION_PROMPT,
            image_base64=base64_image,
            json_schema=BBOX_RESPONSE_SCHEMA,
            temperature=0.0,
            parse_json=True
        )

        logging.pii(f"LLM object detection output: {object_json}")

        if object_json is None or len(object_json.get("objects", [])) == 0:
            logging.error("Failed to extract objects from the graphic.")
            return jsonify({"error": "No objects extracted"}), 204

        # Normalize bounding boxes
        width, height = pil_image.size
        for obj in object_json["objects"]:
            # Normalize bounding boxes
            obj["dimensions"] = normalize_bbox(
                obj["dimensions"], width, height
            )

        # Filter objects by confidence threshold
        object_json["objects"] = filter_objects_by_confidence(
            object_json["objects"],
            CONF_THRESHOLD
        )

        logging.pii(f"Normalized output: {object_json}")

        # Data schema validation
        ok, _ = validator.check_data(object_json)
        if not ok:
            return jsonify("Invalid Preprocessor JSON format"), 500

        # Construct the Final Response
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": PREPROCESSOR_NAME,
            "data": object_json
        }

        # Validate Final Response against System Schema
        ok, _ = validator.check_response(response)
        if not ok:
            return jsonify("Invalid Preprocessor JSON format"), 500

        logging.info(
            f"Successfully processed object detection \
                for request {request_uuid}."
            )

        return jsonify(response), 200

    except Exception as e:
        # Catch-all for unexpected errors during the core processing
        logging.error(
            f"An unexpected error occurred during object detection\
                for {request_uuid}: {e}", exc_info=True
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
        logging.info("Warming up LLM...")

        llm_success = llm_client.warmup()

        if not llm_success:
            logging.error("LLM warmup failed.")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.error(f"Warmup failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
