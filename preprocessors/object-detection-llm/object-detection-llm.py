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
from utils.llm.coordinate_convention import (
    get_model_family, get_bbox_format
)
from utils.validation import Validator
import json
import os

configure_logging()

logging.debug("Starting Object Detection LLM Preprocessor...")

app = Flask(__name__)

CONF_THRESHOLD = float(os.environ.get('CONF_THRESHOLD', '0.9'))

# Get model name from environment variable
LLM_MODEL = os.environ.get('LLM_MODEL', '').lower()
MODEL_NAME = get_model_family(LLM_MODEL)
logging.debug(f"Using LLM model: {LLM_MODEL}, interpreted as {MODEL_NAME}")

# Get bounding box format based on model
BBOX_FORMAT = get_bbox_format(MODEL_NAME)

# Set bounding box key based on model
BBOX_KEY = BBOX_FORMAT["bbox_key"]

# Set coordinate order based on model
COORD_ORDER = BBOX_FORMAT["coord_order"]
bbox_order = f"[{', '.join(COORD_ORDER)}]"

FORMATTED_PROMPT = OBJECT_DETECTION_PROMPT.format(
    bbox_key=BBOX_KEY,
    bbox_order=bbox_order
)

PREPROCESSOR_NAME = \
    "ca.mcgill.a11y.image.preprocessor.objectDetection"

DATA_SCHEMA = './schemas/preprocessors/object-detection.schema.json'

BBOX_SCHEMA = 'object-detection.schema.json'
with open(BBOX_SCHEMA, 'r') as f:
    BBOX_RESPONSE_SCHEMA = json.load(f)

# Swap the bounding box key to match the active model's convention
# Note: if schema is loaded twice, this might raise a key error
prop = BBOX_RESPONSE_SCHEMA["items"]["properties"]
prop[BBOX_KEY] = prop.pop("bbox_2d")
prop[BBOX_KEY]["description"] = f"Bounding box coordinates {bbox_order}."
BBOX_RESPONSE_SCHEMA["items"]["required"] = [
    BBOX_KEY if k == "bbox_2d" else k
    for k in BBOX_RESPONSE_SCHEMA["items"]["required"]
]

try:
    llm_client = LLMClient()
    validator = Validator(data_schema=DATA_SCHEMA)
    logging.debug("LLM client and validator initialized")
except Exception as e:
    logging.error(f"Failed to initialize clients: {e}")
    sys.exit(1)


def normalize_bbox(bbox, width, height, coord_order):
    """
    Normalize bounding box coordinates to [0,1] range.
    Handles differing coordinate orders between LLMs.
    """
    coords = dict(zip(coord_order, bbox))
    x1, y1, x2, y2 = coords["x1"], coords["y1"], coords["x2"], coords["y2"]
    return [
        max(0.0, min(x1 / 1000, 1.0)),
        max(0.0, min(y1 / 1000, 1.0)),
        max(0.0, min(x2 / 1000, 1.0)),
        max(0.0, min(y2 / 1000, 1.0))
    ]


def process_objects(llm_output, width, height, threshold, coord_order):
    """
    Transform LLM object detection output to IMAGE schema format.

    - Transforms from LLM format (bbox_2d, label) to IMAGE format
    - Normalizes bounding boxes to [0,1] range
    - Assigns confidence threshold to all objects
    - Normalizes labels (replaces underscores with spaces)
    - Calculates geometric properties (area, centroid)
    - Filters objects by confidence threshold

    Args:
        llm_output (list): LLM detection output with bbox_2d and label
        width (int): Image width in pixels for normalization
        height (int): Image height in pixels for normalization
        threshold (float): Minimum confidence score (0-1)
        coord_order (tuple): Coordinate order for the active model (e.g. ("x1","y1","x2","y2"))

    Returns:
        list: Processed objects with computed properties
    """
    processed = []
    for idx, item in enumerate(llm_output):
        # Normalize bounding box
        x1, y1, x2, y2 = normalize_bbox(
            item[BBOX_KEY], width, height, coord_order
        )

        # Calculate area (width * height)
        area = (x2 - x1) * (y2 - y1)

        # Calculate centroid
        centroid_x = (x1 + x2) / 2
        centroid_y = (y1 + y2) / 2

        # Create object entry according to IMAGE schema
        obj = {
            "ID": idx,
            "type": item["label"].replace('_', ' '),
            "dimensions": [x1, y1, x2, y2],
            "confidence": threshold,
            "area": area,
            "centroid": [centroid_x, centroid_y]
        }

        processed.append(obj)

    logging.debug(
        f"Processed {len(llm_output)} objects from LLM output"
    )
    return processed


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

    # leaving list here since not sure which one(s) might be useful for
    # preventing endless responses, but when enabled, these definitely
    # prevented Qwen from generating valid return messages.
    stop_tokens = [
        # "<|im_end|>",           # Qwen's end token
        # "<|endoftext|>",        # Alternative end token
        # "\n\n\n",               # Triple newline
        # "```",                  # Code block end
    ]

    try:
        # Get object info
        llm_output = llm_client.chat_completion(
            prompt=FORMATTED_PROMPT,
            image_base64=base64_image,
            json_schema=BBOX_RESPONSE_SCHEMA,
            temperature=0.5,
            parse_json=True,
            stop=stop_tokens
        )

        logging.debug(f"LLM output received: {llm_output}")

        if llm_output is None or len(llm_output) == 0:
            logging.error("Failed to extract objects from the graphic.")
            return jsonify({"error": "No objects extracted"}), 204

        # Transform LLM format to IMAGE schema format
        width, height = pil_image.size
        processed_objects = process_objects(
            llm_output,
            width,
            height,
            CONF_THRESHOLD,
            COORD_ORDER
        )

        # Wrap in "objects" for schema compliance
        object_json = {"objects": processed_objects}

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