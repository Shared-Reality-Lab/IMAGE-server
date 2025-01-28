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


import json
import time
import logging
import jsonschema
import os
import io
import base64
from flask import Flask, request, jsonify
from ocr_utils import (
    process_azure_read,
    process_azure_ocr,
    process_free_ocr,
    process_google_vision,
    find_obj_enclosing,
    process_azure_read_v4_preview
)
from config.logging_utils import configure_logging

configure_logging()

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_ocr_text():
    """
    Gets data on locations nearby a map from the Autour API
    """

    logging.debug("Received request")
    # Load schemas
    with open('./schemas/preprocessors/ocr.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definition_schema = json.load(jsonfile)
    schema_store = {
        data_schema['$id']: data_schema,
        schema['$id']: schema,
        definition_schema['$id']: definition_schema
    }
    content = request.get_json()

    # Check if request is for a map
    if 'graphic' not in content:
        logging.info("Map request. Skipping...")
        return "", 204

    with open('./schemas/request.schema.json') as jsonfile:
        request_schema = json.load(jsonfile)
    # Validate incoming request
    resolver = jsonschema.RefResolver.from_schema(
        request_schema, store=schema_store)
    try:
        validator = jsonschema.Draft7Validator(
            request_schema,
            resolver=resolver
        )
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as error:
        logging.error("Validation failed for incoming request")
        logging.pii(f"Validation error: {error.message}")
        return jsonify("Invalid Request JSON format"), 400
    # Use response schema to validate response
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
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

    try:
        validator = jsonschema.Draft7Validator(data_schema, resolver=resolver)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as error:
        logging.error("Validation failed for processed OCR data")
        logging.pii(f"Validation error: {error.message}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    response = {
        'request_uuid': request_uuid,
        'timestamp': timestamp,
        'name': name,
        'data': data
    }

    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as error:
        logging.error("Validation failed for final response")
        logging.pii(f"Validation error: {error.message}")
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


@app.route('/health', methods=['GET'])
def health():
    """
    health check endpoint to verify if the service is up.
    """
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
