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
import time
import logging
import os
import traceback
from flask import Flask, request, jsonify
import base64
import io
from PIL import Image
from ultralytics import YOLO
import torch
from config.logging_utils import configure_logging
from utils.validation import Validator

# Create Flask app
app = Flask(__name__)

configure_logging()

# Environment variables and constants
MODEL_PATH = os.environ.get('YOLO_MODEL_PATH')
CONF_THRESHOLD = float(os.environ.get('CONF_THRESHOLD', '0.75'))
# Resizing handled upstream
# MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', '640'))

# Load the model
model = YOLO(MODEL_PATH)

# Choose GPU for processing if available
if torch.cuda.is_available():
    device = 'cuda:0'
    device_name = torch.cuda.get_device_name()
else:
    device, device_name = 'cpu', 'CPU'

VALIDATOR = Validator(
    data_schema='./schemas/preprocessors/object-detection.schema.json'
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
    # request schema validation
    ok, err = VALIDATOR.check_request(content)
    if not ok:
        logging.error("Request validation failed.")
        logging.debug(f"[request.validation] {err}")
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
    # Resizing handled upstream
    # logging.debug(f"Max image size: {MAX_IMAGE_SIZE}")

    # Perform object detection with YOLOv11
    # Disable gradient tracking for speed/memory optimization
    # `verbose` is a boolean argument which controls detailed log output
    # It needs to be turned off in production to avoid logging PII
    with torch.no_grad():
        results = model.predict(
            image,
            device=device,
            conf=CONF_THRESHOLD,
            # Resizing handled upstream
            # imgsz=MAX_IMAGE_SIZE,
            verbose=False
        )

    # Format results according to schema
    objects = format_detection_results(results)

    # Check if any objects were detected
    # If no objects are detected, return 204 No Content
    if len(objects["objects"]) == 0:
        logging.info("No objects detected")
        return "", 204

    # Validate YOLO output against the object detection data schema
    ok, err = VALIDATOR.check_data(objects)
    if not ok:
        logging.error("Validation failed for detection data.")
        logging.debug(f"[data.validation] {err}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    # Create full response following preprocessor response schema
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": objects
    }
    # response schema validation
    ok, err = VALIDATOR.check_response(response)
    if not ok:
        logging.error("Response validation failed. Are schemas out of date?")
        logging.debug(f"[response.validation] {err}")
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


@app.route("/warmup", methods=["GET"])
def warmup():
    try:
        # create a blank dummy image (640x640)
        dummy_image = Image.new("RGB", (8, 8), color=(0, 0, 0))

        # Run YOLO inference with dummy image
        with torch.no_grad():
            _ = model.predict(
                dummy_image,
                device=device,
                conf=CONF_THRESHOLD,
                # imgsz=MAX_IMAGE_SIZE,
                verbose=False
            )

        logging.info("YOLO warmup completed successfully with 8x8 image.")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.error(f"YOLO warmup failed: {str(e)}")
        logging.pii(traceback.format_exc())
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
