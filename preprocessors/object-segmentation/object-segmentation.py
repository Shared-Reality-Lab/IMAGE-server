# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
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

import base64
import logging
import os
import sys
import time
from io import BytesIO

from flask import Flask, request, jsonify
from datetime import datetime
from PIL import Image

from config.logging_utils import configure_logging
from utils.object_detection import LLM_OBJECT_DETECTION_NAME
from utils.segmentation import (
    SAMClient,
    create_segment_from_contours,
    filter_contours_by_area,
)
from utils.validation import Validator

configure_logging()

logging.debug("Starting Object Segmentation Preprocessor...")

app = Flask(__name__)

MIN_CONTOUR_AREA = float(os.environ.get('MIN_CONTOUR_AREA', '0.0001'))

PREPROCESSOR_NAME = \
    "ca.mcgill.a11y.image.preprocessor.objectSegmentation"

DATA_SCHEMA = './schemas/preprocessors/segmentation.schema.json'

try:
    sam_client = SAMClient()
    validator = Validator(data_schema=DATA_SCHEMA)
    logging.debug("SAM client and validator initialized")
except Exception as e:
    logging.error(f"Failed to initialize clients: {e}")
    sys.exit(1)


def decode_image(source):
    """
    Decode a base64 "graphic" data URI into a PIL Image, without any
    LLM-specific resizing. The upstream resize-graphic pseudo-preprocessor
    already caps every incoming graphic to a fixed maximum dimension
    (aspect-ratio preserved), so every preprocessor - including this one
    and object-detection-llm - sees the same image and shares a common
    pixel space.
    """
    image_b64 = source.split(",")[1] if "," in source else source
    binary = base64.b64decode(image_b64)
    return Image.open(BytesIO(binary)).convert("RGB")


@app.route("/preprocessor", methods=['POST'])
def segment_objects():
    """
    Main endpoint to segment objects found by object-detection-llm using
    SAM, producing precise per-object polygon outlines.
    """
    logging.debug("Received request for object segmentation.")

    content = request.get_json()

    if "graphic" not in content:
        logging.info("No graphic content. Skipping...")
        return jsonify({"error": "No graphic content"}), 204

    ok, _ = validator.check_request(content)
    if not ok:
        return jsonify({"error": "Invalid Preprocessor JSON format"}), 400

    preprocess_output = content["preprocessors"]
    categoriser = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
    if categoriser in preprocess_output:
        categoriser_output = preprocess_output[categoriser]
        categoriser_tags = categoriser_output["categories"]
        if not categoriser_tags["photo"] and not categoriser_tags["collage"] \
           and not categoriser_tags["illustration"]:
            logging.info("Not a photo, collage, or illustration. Skipping...")
            return "", 204

    # Deliberately read the LLM detector's key directly rather than the
    # generic objectDetection coalesce helper: this preprocessor only
    # makes sense on objects that came from object-detection-llm (SAM
    # is being applied specifically to LLM-detected boxes), not
    # whichever object detector happened to also be running.
    llm_detections = preprocess_output.get(LLM_OBJECT_DETECTION_NAME)
    if not llm_detections or not llm_detections.get("objects"):
        logging.info("No object-detection-llm output. Skipping...")
        return "", 204

    objects = llm_detections["objects"]

    request_uuid = content["request_uuid"]
    timestamp = time.time()

    try:
        pil_image = decode_image(content["graphic"])

        # Use the unique object ID (not the type string) as the SAM label:
        # SAMClient.segment_with_boxes(aggregate_by_label=True) merges
        # contours from boxes sharing the same label, so labelling by
        # type would silently merge contours from multiple same-type
        # objects (e.g. two different people) into a single entry.
        boxes = [
            {"bbox_2d": obj["dimensions"], "label": str(obj["ID"])}
            for obj in objects
        ]
        id_to_type = {str(obj["ID"]): obj["type"] for obj in objects}

        contours_by_id = sam_client.segment_with_boxes(
            pil_image,
            boxes,
            use_prompts=False,
            aggregate_by_label=True,
            return_structured=False,
            coord_scale=1.0,
        )

        segments = []
        for object_id, contours in contours_by_id.items():
            filtered = filter_contours_by_area(
                contours, min_area=MIN_CONTOUR_AREA
            )
            if not filtered:
                continue
            segment = create_segment_from_contours(
                filtered, name=id_to_type[object_id]
            )
            segment["objectID"] = int(object_id)
            segments.append(segment)

        data = {"segments": segments}

        ok, _ = validator.check_data(data)
        if not ok:
            return jsonify("Invalid Preprocessor JSON format"), 500

        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": PREPROCESSOR_NAME,
            "data": data
        }

        ok, _ = validator.check_response(response)
        if not ok:
            return jsonify("Invalid Preprocessor JSON format"), 500

        logging.info(
            f"Successfully segmented {len(segments)} objects "
            f"for request {request_uuid}."
        )

        return jsonify(response), 200

    except Exception as e:
        logging.error(
            f"An unexpected error occurred during object segmentation "
            f"for {request_uuid}: {e}", exc_info=True
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
    Warms up the SAM model by running a dummy inference.
    """
    try:
        logging.info("Warming up SAM...")

        sam_success = sam_client.warmup()

        if not sam_success:
            logging.error("SAM warmup failed.")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.error(f"Warmup failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
