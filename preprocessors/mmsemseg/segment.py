# Copyright (c) 2023 IMAGE Project, Shared Reality Lab, McGill University
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
#
# This was built using the MMsegmentation library that can be found at
# https://github.com/open-mmlab/mmsegmentation

from flask import Flask, request, jsonify
import gc
import json
import jsonschema
import base64

import torch
from mmseg.apis import inference_segmentor, init_segmentor
import mmseg
import mmcv
import numpy as np
import cv2

from utils import visualize_result, findContour

from time import time
import logging
from config.logging_utils import configure_logging
from datetime import datetime
import subprocess

configure_logging()
# configuration and checkpoint files
BEIT_CONFIG = "/app/config/upernet_beit-base_8x2_640x640_160k_ade20k.py"
BEIT_CHECKPOINT = "/app/upernet_beit-base_8x2_640x640_160k_ade20k-eead221d.pth"

# get the color palette used and class names
COLORS = mmseg.core.evaluation.get_palette("ade20k")
CLASS_NAMES = mmseg.core.evaluation.get_classes("ade20k")

app = Flask(__name__)


def run_segmentation(url, model, dictionary):
    # convert an image from base64 format
    # Following 4 lines refered from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    logging.info("converting base64 to numpy array")

    try:
        image_b64 = url.split(",")[1]
        binary = base64.b64decode(image_b64)
        image = np.asarray(bytearray(binary), dtype="uint8")
        image_np = cv2.imdecode(image, cv2.IMREAD_COLOR)
    except Exception as e:
        logging.error("Error decoding base64 image: {}".format(e))
        raise e

    # rescale the image
    height, width, channels = image_np.shape
    scale_factor = float(1500.0 / float(max(height, width)))

    logging.info("graphic original dimension {}".format(image_np.shape))

    if scale_factor <= 1.0:
        logging.info("scaling down an image")
        image_np = mmcv.imrescale(image_np, scale_factor)
        logging.info("graphic scaled dimension: {}".format(image_np.shape))

    height, width, channels = image_np.shape

    # infer the segmentation
    logging.info("running segmentation model")
    try:
        result = inference_segmentor(model, image_np)
    except Exception as e:
        logging.error("error while running segmentation model : {}".format(e))
        raise e

    logging.info("run finished")

    # extracting contours
    pred = result[0].astype(np.int32)
    predicted_classes = np.bincount(pred.flatten()).argsort()[::-1]
    logging.info("main classes detected : {}".format(predicted_classes[:5]))

    for class_id in predicted_classes[:5]:
        logging.info("extracting contours for class: {}".format(str(class_id)))

        pred_color, class_name = visualize_result(pred, index=class_id)
        contour, center, area = findContour(pred_color, width, height)

        logging.info("contour extraction finished")

        if area == 0:
            continue
        dictionary.append({
            "name": class_name,
            "area": area,
            "centroid": center,
            "contours": contour
        })

    logging.info("segmentation finished")
    return {'segments': dictionary}


@app.route("/preprocessor", methods=["POST", "GET"])
def segment():
    logging.debug("Received request")
    gc.collect()
    torch.cuda.empty_cache()
    dictionary = []

    # load the schemas
    with open('./schemas/preprocessors/segmentation.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    # Following 6 lines refered from
    # https://stackoverflow.com/questions/42159346/jsonschema-refresolver-to-resolve-multiple-refs-in-python
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
    logging.info("Schemas loaded")

    # load the model
    try:
        model = init_segmentor(BEIT_CONFIG, BEIT_CHECKPOINT, device='cuda:0')
    except RuntimeError as e:
        if 'out of memory' in str(e):
            logging.error('CUDA out of memory.')
            return jsonify({"error": "CUDA out of memory."}), 500
    logging.info("Model loaded")

    # get the request
    request_json = request.get_json()

    # validate the request
    try:
        validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
        validator.validate(request_json)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Request validation failed")
        logging.pii(f"Validation error: {e.message} | Data: {request_json}")
        return jsonify("Invalid Preprocessor JSON format"), 400

    if "graphic" not in request_json:
        logging.info("Not image content. Skipping ...")
        return '', 204

    request_uuid = request_json["request_uuid"]
    timestamp = time()

    preprocessor_name = \
        "ca.mcgill.a11y.image.preprocessor.semanticSegmentation"
    classifier_1 = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
    classifier_2 = "ca.mcgill.a11y.image.preprocessor.graphicTagger"
    preprocess_output = request_json["preprocessors"]

    # check if the first classifier and second classifier are present.
    # these steps could be skipped
    # if the architecture is modified appropriately
    if classifier_1 in preprocess_output:
        classifier_1_output = preprocess_output[classifier_1]
        classifier_1_label = classifier_1_output["category"]
        if classifier_1_label != "photograph":
            logging.info(
                "Not photograph content. Skipping...")

            return "", 204
        if classifier_2 in preprocess_output:
            # classifier_2_output = preprocess_output[classifier_2]
            # classifier_2_label = classifier_2_output["category"]
            # if classifier_2_label != "outdoor":
            #     logging.info("Cannot process image")
            #     return "", 204
            try:
                segment = run_segmentation(
                    request_json["graphic"], model, dictionary)
            except Exception as e:
                logging.pii(f"Segmentation error: {e}")
                return jsonify("Error while running segmentation"), 500
        else:
            """We are providing the user the ability to process an image
            even when the second classifier is absent, however it is
            recommended to the run the semantic segmentation
            model in conjunction with the second classifier."""
            try:
                segment = run_segmentation(
                    request_json["graphic"], model, dictionary)
            except Exception as e:
                logging.pii(f"Segmentation error: {e}")
                return jsonify("Error while running the segmentation"), 500
    else:
        """We are providing the user the ability to process an image
        even when the first classifier is absent, however it is
        recommended to the run the semantic segmentation
        model in conjunction with the first classifier."""
        try:
            segment = run_segmentation(
                request_json["graphic"], model, dictionary)
        except Exception as e:
            logging.pii(f"Segmentation error: {e}")
            return jsonify("Error while running the segmentation"), 500

    torch.cuda.empty_cache()

    # validate the data format for the output
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(segment)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Data validation failed")
        logging.pii(f"Validation error: {e.message} | Data: {segment}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": preprocessor_name,
        "data": segment
    }

    # validate the output format
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Response validation failed")
        logging.pii(f"Validation error: {e.message} | Response: {response}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    logging.info("Valid response generated")

    return response


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint to verify if the service is running
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/health/gpu", methods=["GET"])
def gpu_driver_health_check():
    """
    Enhanced health check:
    - Verifies CUDA & NVIDIA drivers are working
    - Detects if the loaded NVIDIA driver matches `nvidia-smi`
    - Ensures the container is using the correct GPU runtime
    """

    # Check if CUDA is available
    if not torch.cuda.is_available():
        return jsonify({
            "status": "unhealthy",
            "message": "CUDA not available inside the container",
            "recommendation": "Check if the container is running with GPU \
                access (--gpus all)"
        }), 500

    try:
        # Get installed NVIDIA driver version from nvidia-smi
        nvidia_smi_version = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version",
             "--format=csv,noheader"],
            text=True
        ).strip()

        # Get loaded driver version from /proc/driver/nvidia/version
        loaded_driver_version = subprocess.check_output(
            ["cat", "/proc/driver/nvidia/version"], text=True
        ).split("\n")[0]

        # Ensure they match
        if nvidia_smi_version not in loaded_driver_version:
            return jsonify({
                "status": "unhealthy",
                "message": "NVIDIA driver mismatch detected",
                "nvidia_smi_version": nvidia_smi_version,
                "loaded_driver_version": loaded_driver_version,
                "recommendation": "Reboot the system to ensure the correct \
                    driver is loaded?"
            }), 500

        return jsonify({
            "status": "healthy",
            "message": "NVIDIA drivers and CUDA are working correctly",
            "nvidia_smi_version": nvidia_smi_version,
            "loaded_driver_version": loaded_driver_version
        }), 200

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "message": f"NVIDIA driver check failed: {str(e)}",
            "recommendation": "Check driver installation and restart system"
        }), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
