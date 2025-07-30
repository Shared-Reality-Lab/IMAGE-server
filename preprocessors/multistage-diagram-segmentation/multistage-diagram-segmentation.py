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

import cv2
from ultralytics import SAM
import jsonschema
from openai import OpenAI
from io import BytesIO
import json
from PIL import Image, UnidentifiedImageError
import numpy as np
import base64
import logging
import os
import time
import copy
from flask import Flask, request, jsonify
from datetime import datetime
from config.logging_utils import configure_logging
import sys
from qwen_vl_utils import smart_resize


configure_logging()

# Disable OpenAI debug logs
logging.getLogger("openai").setLevel(logging.WARNING)
# Also disable httpx logs which OpenAI uses
logging.getLogger("httpx").setLevel(logging.WARNING)

app = Flask(__name__)

# --- Configuration ---
ALLOWED_ORIGINS = [
    "https://image.a11y.mcgill.ca/pages/multistage_diagrams.html",
    "https://venissacarolquadros.github.io/",
    "https://unicorn.cim.mcgill.ca/",
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "qwen-vl-max"
BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY environment variable not set.")
    sys.exit(1)

# Initialize OpenAI Client
try:
    client = OpenAI(api_key=OPENAI_API_KEY,
                    base_url=BASE_URL)
    logging.debug("OpenAI client initialized")
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    client = None
    sys.exit(1)

SAM_MODEL_PATH = os.getenv('SAM_MODEL_PATH')

# Initialize SAM
try:
    sam_model = SAM(SAM_MODEL_PATH)
    logging.debug("SAM model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load SAM model: {e}", exc_info=True)

# Preprocessor Name
PREPROCESSOR_NAME = \
    "ca.mcgill.a11y.image.preprocessor.multistage-diagram-segmentation"

# Load schemas once at startup
with open('./schemas/preprocessors/multistage-diagram.schema.json') as f:
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

BASE_PROMPT = """
Look at the attached flow diagram and parse the information
about stages and their dependencies.
Determine phase names, phase descriptions, and connections between phases
(usually marked with arrows or clear from the diagram flow).
Return the response in the JSON format according to provided schema.
Do not include any additional text in your response.
Return only the JSON object.
If some of the properties can't be identified, assign empty value to them.
"""

# Schema Gemini should follow for the initial extraction
BASE_SCHEMA_PATH = os.getenv("BASE_SCHEMA")
with open(BASE_SCHEMA_PATH) as f:
    BASE_SCHEMA_GEMINI = json.load(f)


def decode_image(source: str) -> Image.Image | None:
    """
    Decode base64 image data to Pillow image for processing
    """
    try:
        # Remove header (e.g. 'data:image/jpeg;base64,')
        if not isinstance(source, str) or "," not in source:
            raise ValueError(
                "Invalid graphic format: expected data URI string."
                )
        graphic_b64 = source.split(',', 1)[1]
        img_data = base64.b64decode(graphic_b64)
        pil_image = Image.open(BytesIO(img_data))
        # Ensure image is in RGB or a format SAM/Gemini can handle
        pil_image = pil_image.convert("RGB")
        logging.debug(
            f"Decoded image successfully. Format: {pil_image.format}, \
                Size: {pil_image.size}"
            )
        return pil_image
    except (ValueError, TypeError) as e:
        logging.error(f"Failed to decode base64 image data: {e}")
        return jsonify({"error": "Invalid base64 image data"}), 400
    except UnidentifiedImageError:
        logging.error("Cannot identify image file format from decoded data.")
        return jsonify({"error": "Invalid or unsupported image format"}), 400
    except Exception as e:
        logging.error(
            f"Unexpected error during image decoding: {e}", exc_info=True
            )
        return jsonify(
            {"error": "Internal server error during image processing"}
            ), 500


def validate_openai_response(response) -> str | None:
    """
    Validates the OpenAI API response and extracts the content.
    """
    try:
        if not response.choices:
            logging.error("OpenAI response missing choices")
            return None

        choice = response.choices[0]

        if choice.finish_reason not in ["stop", "length"]:
            logging.error(
                f"Generation stopped with reason: {choice.finish_reason}"
            )
            return None

        if not choice.message or not choice.message.content:
            logging.error("OpenAI response missing message content")
            return None

        logging.debug("OpenAI response validation successful.")
        return choice.message.content

    except Exception as e:
        logging.error(f"Error validating OpenAI response: {e}")
        return None


def extract(base64_image: str) -> dict | None:
    """
    Sends an image to OpenAI to extract structured information
    (stages and links) based on the schema.
    """
    if not client:
        logging.error("OpenAI client not initialized.")
        return None

    logging.info("Requesting base diagram information from OpenAI...")
    try:
        # Prepare the messages with schema in the prompt
        schema_prompt = f'''{BASE_PROMPT}\n\n
        Return the response according to this JSON schema:\n
        {json.dumps(BASE_SCHEMA_GEMINI, indent=2)}'''

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": schema_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )

        response_text = validate_openai_response(response)
        if response_text is None:
            return None

        logging.info("OpenAI request successful. Parsing JSON response.")
        logging.pii(f"Response text to parse: {response_text}")
        parsed_json = json.loads(response_text)
        logging.info("Successfully parsed OpenAI JSON response.")
        return parsed_json

    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON response from OpenAI: {e}")
        return None
    except Exception as e:
        logging.error(
            f"Unexpected error during OpenAI extraction: {e}", exc_info=True
        )
        return None


def point(stages: list[str], base64_image: str) -> str | None:
    """
    Sends an image and stage labels to OpenAI to get bounding boxes.
    """
    if not client:
        logging.error("OpenAI client not initialized.")
        return None
    if not stages:
        logging.warning(
            "No stages provided. Skipping bounding box request."
        )
        return "{}"

    logging.pii(f"Requesting bounding boxes for stages: {stages}")

    BBOX_PROMPT = f'''Give the bounding boxes for the illustrations
of the following stages: {stages}.
Output a only JSON list of bounding boxes where each entry contains
the 2D bounding box in the key "box_2d",
and the stage name in the key "label".
'''

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": BBOX_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            # response_format={"type": "json_object"}
        )

        response_text = validate_openai_response(response)
        if response_text is None:
            return None

        logging.pii(f"Bounding box response text: {response_text}")
        return response_text

    except Exception as e:
        logging.error(
            f"Unexpected error during OpenAI point request: {e}", exc_info=True
        )
        return None


def convert_to_sam_coordinates(
        bbox: list[int], width: int, height: int
        ) -> list[int]:
    """
    Converts Gemini's normalized bbox [x1, y1, x2, y2] (0-1000) to SAM's
    absolute pixel [x1, y1, x2, y2].
    """
    try:
        # Check if bbox has 4 numeric elements
        if not (isinstance(bbox, list)
                and len(bbox) == 4
                and all(isinstance(n, (int, float)) for n in bbox)):
            logging.warning(
                f"Invalid bbox format received: {bbox}. \
                    Expected list of 4 numbers."
            )
            return None

        # Graphics size used by Qwen
        min_pixels = 512 * 28 * 28
        max_pixels = 1024 * 28 * 28
        # Qwen splits images into 28x28 patches
        factor = 28

        # Input size
        input_height, input_width = smart_resize(
            height,
            width,
            factor=factor,
            min_pixels=min_pixels,
            max_pixels=max_pixels
        )
        print(f"Model input size: {input_width, input_height}")

        abs_x1 = int(bbox[0] / input_width * width)
        abs_y1 = int(bbox[1] / input_height * height)
        abs_x2 = int(bbox[2] / input_width * width)
        abs_y2 = int(bbox[3] / input_height * height)

        # Ensure coordinates are within image bounds and valid order
        abs_x1 = max(0, min(width - 1, abs_x1))
        abs_y1 = max(0, min(height - 1, abs_y1))
        abs_x2 = max(0, min(width - 1, abs_x2))
        abs_y2 = max(0, min(height - 1, abs_y2))

        # Swap if order is wrong
        if abs_x1 > abs_x2:
            abs_x1, abs_x2 = abs_x2, abs_x1
        if abs_y1 > abs_y2:
            abs_y1, abs_y2 = abs_y2, abs_y1

        # Ensure non-zero width/height for SAM bbox
        if abs_x1 >= abs_x2 or abs_y1 >= abs_y2:
            logging.warning(
                f"Converted SAM bbox has zero width/height: \
                    [{abs_x1}, {abs_y1}, {abs_x2}, {abs_y2}] from {bbox}. \
                        Skipping."
            )
            return None

        sam_coords = [abs_x1, abs_y1, abs_x2, abs_y2]
        return sam_coords

    except (TypeError, IndexError, ValueError) as e:
        logging.error(f"Error converting bbox {bbox} to SAM coordinates: {e}")
        return None


def extract_normalized_contours(
        results: list, img_width: int, img_height: int
        ) -> list[list[list[float]]]:
    """
    Extracts and normalizes contours from SAM results.
    """
    if not results or len(results) == 0 or not results[0].masks:
        logging.info("No masks found in SAM results.")
        return []

    try:
        # Get masks from results
        masks = results[0].masks.data.cpu().numpy()
        normalized_contours_list = []

        for i, mask in enumerate(masks):
            mask_uint8 = (mask * 255).astype(np.uint8)
            contours, hierarchy = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

            if contours:
                for contour in contours:
                    if len(contour) < 3:
                        # Need 3+ points
                        continue

                    # Ensure division by zero doesn't happen
                    if img_width <= 0 or img_height <= 0:
                        logging.error(
                            "Image width or height is zero, cannot normalize."
                        )
                        continue

                    normalized_contour = []
                    for point in contour.reshape(-1, 2):
                        x_norm = float(point[0] / img_width)
                        y_norm = float(point[1] / img_height)
                        x_norm = max(0.0, min(1.0, x_norm))
                        y_norm = max(0.0, min(1.0, y_norm))
                        normalized_contour.append([x_norm, y_norm])

                    if normalized_contour:
                        normalized_contours_list.append(normalized_contour)
            else:
                logging.debug(f"No contours found for mask with index {i}.")

        return normalized_contours_list
    except Exception as e:
        logging.error(
            f"Error extracting normalized contours: {e}", exc_info=True
            )
        return []


def segment_stages(
        bounding_box_json_str: str, im: Image.Image
        ) -> dict[str, list[list[list[float]]]]:
    """
    Processes bounding box JSON, runs SAM, aggregates contours.
    """

    if not bounding_box_json_str:
        logging.warning(
            "Received empty or None bounding_box_json_str for segmentation."
            )
        return {}

    # Clean the JSON string (remove potential markdown backticks)
    cleaned_json_str = bounding_box_json_str.strip()
    if cleaned_json_str.startswith('```json'):
        cleaned_json_str = cleaned_json_str[7:]
    if cleaned_json_str.endswith('```'):
        cleaned_json_str = cleaned_json_str[:-3]
    cleaned_json_str = cleaned_json_str.strip()

    try:
        # Handle potential empty string after cleaning
        if not cleaned_json_str:
            logging.warning("Bounding box string is empty after cleaning.")
            return {}
        bounding_boxes_data = json.loads(cleaned_json_str)
        if not isinstance(bounding_boxes_data, list):
            raise ValueError("Expected a list of bounding box objects.")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding bounding box JSON: {e}")
        logging.pii(
            f"Received string for segmentation: '{bounding_box_json_str}'"
            )
        return {}
    except ValueError as e:
        logging.error(f"Bounding box JSON structure incorrect: {e}")
        logging.pii(
            f"Received string for segmentation: '{bounding_box_json_str}'"
            )
        return {}

    bboxes = []
    labels = []

    width, height = im.size
    logging.pii(f"Image dimensions: {width}x{height} =================")

    if width <= 0 or height <= 0:
        logging.error(
            f"Invalid image dimensions: {width}x{height}. \
                Cannot perform segmentation."
            )
        return {}

    # Process each detected bounding box
    for item in bounding_boxes_data:
        if not isinstance(item, dict):
            logging.pii(
                f"Skipping non-dictionary item in bounding box list: {item}"
                )
            continue

        label = item.get("label")
        bbox_norm = item.get("box_2d")

        if not label or not isinstance(label, str):
            logging.pii(
                f"Skipping item with missing or invalid label: {item}"
                )
            continue
        if not bbox_norm:
            logging.pii(f"Skipping item with missing 'box_2d': {item}")
            continue

        logging.pii(f"Processing bounding box for label: '{label}'")
        sam_bbox = convert_to_sam_coordinates(bbox_norm, width, height)

        if sam_bbox is None:
            logging.pii(
                f"Skipping label '{label}' due to \
                    invalid bounding box conversion from {bbox_norm}."
                )
            continue

        # After all checks add data to respective lists
        bboxes.append(sam_bbox)
        labels.append(label)

        logging.debug(f"Input Norm BBox (0-1000): {bbox_norm}")
        logging.debug(f"Converted SAM BBox (pixels): {sam_bbox}")

    # Run SAM model for this all bounding boxes at once
    try:
        # Ensure image is in a format SAM expects (PIL is usually fine)
        results = sam_model(im, bboxes=bboxes)

        aggregated_contour_data = {label: [] for label in labels}

        # Process results paired with their labels
        for result, label in zip(results[0], labels):
            normalized_contours = extract_normalized_contours(
                result, width, height
                )
            aggregated_contour_data[label].extend(normalized_contours)

    except Exception as e:
        logging.pii(
            f"Error during SAM processing for label '{label}' \
                with bbox {sam_bbox}: {e}", exc_info=True
            )
        # Continue processing other boxes

    logging.pii("--- Aggregated Contour Data Summary ---")
    for lbl, contours in aggregated_contour_data.items():
        logging.pii(f"Label: '{lbl}', Number of Contours: {len(contours)}")
    logging.pii("---------------------------------------")
    return aggregated_contour_data


def update_json_with_contours(
        base_json: dict, aggregated_contour_data: dict
        ) -> dict:
    """
    Adds contours from SAM results to the base JSON structure.
    """
    updated_json = copy.deepcopy(base_json)

    stages_by_label = {stage.get("label"): stage
                       for stage in updated_json["stages"]
                       if isinstance(stage, dict) and "label" in stage}

    for label, contours_list in aggregated_contour_data.items():
        if label in stages_by_label:
            stage = stages_by_label[label]
            if (
                "segments" not in stage
                or not isinstance(stage["segments"], list)
            ):
                stage["segments"] = []

            for i, contour_coords in enumerate(contours_list):
                if not contour_coords or len(contour_coords) < 3:
                    logging.pii(
                        f"Skipping invalid contour {i+1} for label '{label}' \
                            (too few points)"
                        )
                    continue

                try:
                    contour_np = np.array(contour_coords, dtype=np.float32)

                    # Centroid
                    moments = cv2.moments(contour_np)
                    contour_centroid = [0.0, 0.0]
                    if moments['m00'] != 0:
                        cx = float(moments['m10'] / moments['m00'])
                        cy = float(moments['m01'] / moments['m00'])
                        # Clamp centroid to be within [0, 1]
                    else:
                        # Fallback geometric center
                        cx = float(np.mean(contour_np[:, 0]))
                        cy = float(np.mean(contour_np[:, 1]))
                    contour_centroid = [
                        max(0.0, min(1.0, cx)), max(0.0, min(1.0, cy))
                        ]

                    # Area (normalized 0-1)
                    contour_area = float(cv2.contourArea(contour_np))
                    contour_area = max(0.0, min(1.0, contour_area))

                    # Format coordinates
                    formatted_coordinates = [
                        [float(p[0]), float(p[1])] for p in contour_coords
                        ]

                    contour_object = {
                        "coordinates": formatted_coordinates,
                        "centroid": contour_centroid,
                        "area": contour_area
                    }

                    segment_name = f"{label} Part {i + 1}" \
                        if len(contours_list) > 1 else label
                    segment = {
                        "name": segment_name,
                        "contours": [contour_object],
                        "centroid": contour_centroid,
                        "area": contour_area
                    }

                    stage["segments"].append(segment)
                except Exception as e:
                    logging.pii(f"Error processing contour {i+1} for \
                                  label '{label}': {e}", exc_info=True)

        else:
            logging.pii(f"Found contours for label '{label}', \
                        but no matching stage found in base_json.")

    # Ensure all stages have a 'segments' key
    for stage in updated_json["stages"]:
        if isinstance(stage, dict) and "segments" not in stage:
            stage["segments"] = []

    return updated_json


@app.route("/preprocessor", methods=['POST'])
def process_diagram():
    """
    Main endpoint to process multi-stage textbook diagrams.
    """
    logging.debug("Received request for multi-stage diagram processing.")

    # Get JSON content from the request
    content = request.get_json()

    # 0. Check the URL of the request to avoid processing PII in production
    # until the Google API is approved for use
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
        # Validate input against REQUEST_SCHEMA
        validator = jsonschema.Draft7Validator(
            REQUEST_SCHEMA, resolver=RESOLVER
            )
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for incoming request")
        logging.pii(f"Validation error: {e.message} | Data: {content}")
        return jsonify({"error": "Invalid Preprocessor JSON format"}), 400

    request_uuid = content["request_uuid"]
    timestamp = time.time()

    # 2. Decode Base64 Image
    source = content["graphic"]
    base64_image = source.split(',', 1)[1]
    pil_image = decode_image(source)

    try:
        # 3. Extract Base stages and Links using Gemini
        base_json = extract(base64_image)
        if base_json is None:
            logging.error("Failed to extract base diagram info from Gemini.")
            return jsonify(
                {"error": "Failed to get initial analysis from vision model"}
                ), 503

        # Validate the structure received from 'extract'
        if (
            not isinstance(base_json, dict)
            or "stages" not in base_json
            or "links" not in base_json
        ):
            logging.pii(
                f"Invalid structure received from Gemini: {base_json}"
                )
            return jsonify(
                {"error": "Received invalid initial analysis structure"}
                ), 500

        # 4. Get Stage Labels for Bounding Box Request
        # Ensure stages is a list and items have 'label'
        stages = [
            stage["label"]
            for stage in base_json.get("stages", [])
            if isinstance(stage, dict) and "label" in stage
            ]
        if not stages:
            logging.warning(
                "No stage labels found. Cannot request bounding boxes."
                )
            aggregated_contour_data = {}
            final_data_json = update_json_with_contours(
                base_json, aggregated_contour_data
                )

        else:
            logging.pii(f"Identified stages: {stages}")

            # 5. Get Bounding Box Suggestions using Gemini ('point')
            bounding_box_json_str = point(stages, base64_image)
            if bounding_box_json_str is None:
                logging.error("Failed to get bounding boxes from Gemini.")
                aggregated_contour_data = {}
                final_data_json = update_json_with_contours(
                    base_json, aggregated_contour_data
                    )

            else:
                # 6. Segment Stages using SAM
                aggregated_contour_data = segment_stages(
                    bounding_box_json_str, pil_image
                    )
                if not aggregated_contour_data:
                    logging.warning(
                        "Segmentation process did not yield any contour data."
                        )
                    # Continue with base_json, contours will be empty

                # 7. Combine Base JSON with Contour Data
                final_data_json = update_json_with_contours(
                    base_json, aggregated_contour_data
                    )

        # 8. Validate the Generated Data against its specific schema
        try:
            validator = jsonschema.Draft7Validator(DATA_SCHEMA)
            validator.validate(final_data_json)
        except jsonschema.exceptions.ValidationError as e:
            logging.error("Validation failed for detection data")
            logging.pii(
                f"Validation error: {e.message} | Data: {final_data_json}"
                )
            return jsonify("Invalid Preprocessor JSON format"), 500

        # 9. Construct the Final Response
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": PREPROCESSOR_NAME,
            "data": final_data_json
        }

        # 10. Validate Final Response against System Schema
        try:
            validator = jsonschema.Draft7Validator(
                RESPONSE_SCHEMA, resolver=RESOLVER
                )
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as e:
            logging.error("Validation failed for full response")
            logging.pii(
                f"Validation error: {e.message} | Response: {response}"
                )
            return jsonify("Invalid Preprocessor JSON format"), 500

        logging.info(
            f"Successfully processed diagram for request {request_uuid}."
            )
        # logging.pii(response)
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
    try:
        logging.info("Warming up Gemini and SAM...")

        # OpenAI: dummy image + prompt
        dummy_img = Image.new("RGB", (512, 512), color="white")
        # Convert dummy image to base64
        buffered = BytesIO()
        dummy_img.save(buffered, format="PNG")
        dummy_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "{}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{dummy_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        _ = validate_openai_response(response)

        # SAM: dummy box
        dummy_cv2 = np.zeros((512, 512, 3), dtype=np.uint8)
        dummy_pil = Image.fromarray(dummy_cv2)
        _ = sam_model(dummy_pil, bboxes=[[100, 100, 200, 200]])

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.pii(f"Warmup failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
