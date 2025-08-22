# Copyright (c) 2021 IMAGE Project, Shared Reality Lab, McGill University
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


import time
import logging
import os
import io
import base64
from flask import Flask, request, jsonify
from datetime import datetime
from ocr_utils import (
    process_azure_read,
    process_azure_ocr,
    process_free_ocr,
    process_google_vision,
    find_obj_enclosing,
    process_azure_read_v4_preview
)
from config.logging_utils import configure_logging
from utils.validation import Validator

configure_logging()

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

VALIDATOR = Validator(data_schema='./schemas/preprocessors/ocr.schema.json')


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_ocr_text():
    """
    Gets data on locations nearby a map from the Autour API
    """

    logging.debug("Received request")
    content = request.get_json()

    # Check if request is for a map
    if 'graphic' not in content:
        logging.info("Map request. Skipping...")
        return "", 204

    # Validate incoming request
    ok, _ = VALIDATOR.check_request(content)
    if not ok:
        return jsonify("Invalid Request JSON format"), 400

    # Get OCR text response
    width = content['dimensions'][0]
    height = content['dimensions'][1]

    cld_srv_optn = os.environ["CLOUD_SERVICE"]

    ocr_result = analyze_image(content['graphic'], width, height, cld_srv_optn)

    if ocr_result is None:
        return jsonify("Could not retreive Azure results"), 500

    od = 'ca.mcgill.a11y.image.preprocessor.objectDetection'
    preprocessors = content['preprocessors']
    if od in preprocessors and len(preprocessors[od]['objects']) > 0:
        ocr_result = find_obj_enclosing(od, preprocessors[od], ocr_result)

    name = 'ca.mcgill.a11y.image.preprocessor.ocrClouds'
    request_uuid = content['request_uuid']
    timestamp = int(time.time())
    data = {'lines': ocr_result, 'cloud_service': cld_srv_optn}

    # data schema validation
    ok, _ = VALIDATOR.check_data(data)
    if not ok:
        return jsonify("Invalid Preprocessor JSON format"), 500

    response = {
        'request_uuid': request_uuid,
        'timestamp': timestamp,
        'name': name,
        'data': data
    }

    # full response validation
    ok, _ = VALIDATOR.check_response(response)
    if not ok:
        return jsonify("Invalid Preprocessor JSON format"), 500

    logging.debug("Sending response")
    return response


def analyze_image(source, width, height, cld_srv_optn):
    """
    Gets OCR text data from desired API
    """

    # Convert URI to binary stream
    image_b64 = source.split(",")[1]
    binary = base64.b64decode(image_b64)
    stream = io.BytesIO(binary)

    try:
        if cld_srv_optn == "AZURE_READ":
            return process_azure_read(stream, width, height)

        elif cld_srv_optn == "AZURE_READ_v4_PREVIEW":
            return process_azure_read_v4_preview(stream, width, height)

        elif cld_srv_optn == "AZURE_OCR":
            return process_azure_ocr(stream, width, height)

        elif cld_srv_optn == "FREE_OCR":
            return process_free_ocr(source, width, height)

        elif cld_srv_optn == "GOOGLE_VISION":
            return process_google_vision(image_b64, width, height)
    except Exception as e:
        logging.error("Error during OCR analysis")
        logging.pii(f"OCR analysis error: {e}")
        return None


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
    app.run(host='0.0.0.0', port=5000, debug=True)
