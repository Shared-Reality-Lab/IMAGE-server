# YOLOv11 🚀 by Ultralytics, AGPL-3.0 license
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

from datetime import datetime
import json
import time
import logging
import os
import traceback
from flask import Flask, request, jsonify
import jsonschema
import base64
import io
from PIL import Image
from ultralytics import YOLO
import torch
from config.logging_utils import configure_logging

# Create Flask app
app = Flask(__name__)

configure_logging()

# Environment variables and constants
MODEL_PATH = os.environ.get('YOLO_MODEL_PATH')
CONF_THRESHOLD = float(os.environ.get('CONF_THRESHOLD', '0.75'))
MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', '640'))

# Load the model
model = YOLO(MODEL_PATH)

# Choose GPU for processing if available
if torch.cuda.is_available():
    device = 'cuda:0'
    device_name = torch.cuda.get_device_name()
else:
    device, device_name = 'cpu', 'CPU'

# Load schemas once at startup
with open('./schemas/preprocessors/object-detection.schema.json') as f:
    DATA_SCHEMA = json.load(f)
with open('./schemas/preprocessor-response.schema.json') as f:
    RESPONSE_SCHEMA = json.load(f)
with open('./schemas/definitions.json') as f:
    DEFINITIONS_SCHEMA = json.load(f)
with open('./schemas/request.schema.json') as f:
    REQUEST_SCHEMA = json.load(f)

# Build resolver store using loaded schemas
# Following 7 lines of code are referred from
# https://stackoverflow.com/questions/42159346/jsonschema-refresolver-to-resolve-multiple-refs-in-python
SCHEMA_STORE = {
    RESPONSE_SCHEMA['$id']: RESPONSE_SCHEMA,
    DEFINITIONS_SCHEMA['$id']: DEFINITIONS_SCHEMA
    }
RESOLVER = jsonschema.RefResolver.from_schema(
    RESPONSE_SCHEMA, store=SCHEMA_STORE
    )


def decode_image(graphic_data):
    """
    Decode base64 image data to Pillow image for processing
    """
    try:
        # Remove header (e.g. 'data:image/jpeg;base64,')
        if ',' in graphic_data:
            graphic_data = graphic_data.split(',', 1)[1]

        # Decode base64 to bytes
        image_bytes = base64.b64decode(graphic_data)

        # Use PIL to pass the image to YOLO
        image = Image.open(io.BytesIO(image_bytes))

        return image
    except Exception as e:
        logging.error(f"Failed to decode image: {str(e)}")
        logging.pii(traceback.format_exc())
        return None


def format_detection_results(results):
    """
    Format YOLO detection results to match the preprocessor output schema
    """
    objects = []

    try:
        # Process each detection
        for result in results:
            boxes = result.boxes
            for i, box in enumerate(boxes):
                # Get class, confidence, and bounding box
                cls_id = int(box.cls.item())
                cls_name = result.names[cls_id]
                confidence = float(box.conf.item())

                # Get normalized bounding box coordinates [0,1]
                x1, y1, x2, y2 = box.xyxyn[0].tolist()

                # Calculate area (width * height)
                area = (x2 - x1) * (y2 - y1)

                # Calculate centroid
                centroid_x = (x1 + x2) / 2
                centroid_y = (y1 + y2) / 2

                # Create object entry according to schema
                obj = {
                    "ID": i,
                    "type": cls_name,
                    "dimensions": [x1, y1, x2, y2],
                    "confidence": confidence,
                    "area": area,
                    "centroid": [centroid_x, centroid_y]
                }
                objects.append(obj)
    except Exception as e:
        logging.error(f"Error formatting detection results: {str(e)}")
        logging.pii(traceback.format_exc())

    return {"objects": objects}


@app.route("/preprocessor", methods=['POST'])
def detect():
    # Get JSON content from the request
    content = request.get_json()
    try:
        # Validate input against REQUEST_SCHEMA
        validator = jsonschema.Draft7Validator(
            REQUEST_SCHEMA, resolver=RESOLVER
            )
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for incoming request")
        logging.pii(f"Validation error: {e.message} | Data: {content}")
        return jsonify("Invalid Preprocessor JSON format"), 400

    # Check if there is graphic content to process
    if "graphic" not in content:
        logging.info("No graphic content. Skipping...")
        return "", 204

    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.objectDetection"

    # Decode image
    image = decode_image(content["graphic"])
    if image is None:
        logging.error("Failed to decode image")
        return jsonify("Failed to decode image"), 400

    # Log settings for object detection
    logging.debug(f"Model path: {MODEL_PATH}")
    logging.debug(f"Using device: {device_name}")
    logging.debug(f"Confidence threshold: {CONF_THRESHOLD}")
    logging.debug(f"Max image size: {MAX_IMAGE_SIZE}")

    # Perform object detection with YOLOv11
    # Disable gradient tracking for speed/memory optimization
    # `verbose` is a boolean argument which controls detailed log output
    # It needs to be turned off in production to avoid logging PII
    with torch.no_grad():
        results = model.predict(
            image,
            device=device,
            conf=CONF_THRESHOLD,
            imgsz=MAX_IMAGE_SIZE,
            verbose=False
        )

    # Format results according to schema
    objects = format_detection_results(results)

    # Validate YOLO output against the object detection data schema
    try:
        validator = jsonschema.Draft7Validator(DATA_SCHEMA)
        validator.validate(objects)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for detection data")
        logging.pii(f"Validation error: {e.message} | Data: {objects}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    # Create full response following preprocessor response schema
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": objects
    }
    try:
        validator = jsonschema.Draft7Validator(
            RESPONSE_SCHEMA, resolver=RESOLVER
            )
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for full response")
        logging.pii(f"Validation error: {e.message} | Response: {response}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    logging.pii(response)
    return jsonify(response), 200


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint to verify if the service is running
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
