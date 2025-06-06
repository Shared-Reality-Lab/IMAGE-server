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

import jsonschema
from io import BytesIO
import base64
import json
import logging
import time
from flask import Flask, request, jsonify
from datetime import datetime
from config.logging_utils import configure_logging

configure_logging()

app = Flask(__name__)

# Preprocessor Name
PREPROCESSOR_NAME = "ca.mcgill.a11y.image.request"  # Required for pseudo

# Load schemas once at startup
with open('./schemas/preprocessors/modify-request.schema.json') as f:
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


@app.route("/preprocessor", methods=['POST'])
def resize_graphic():
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
        return jsonify({"message": "No graphic content"}), 204

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
        return jsonify({"error": "Request not in the appropriate format"}), 400

    request_uuid = content["request_uuid"]
    timestamp = time.time()

    # 2. TODO resizing
    new_b64_graphic = None  # this should be Something
    data = {
            "graphic": new_b64_graphic
    }

    # 3. Check modification
    try:
        validator = jsonschema.Draft7Validator(DATA_SCHEMA)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for request modification")
        logging.pii(
            f"Validation error: {e.message} | Data: {data}"
            )
        return jsonify("Failed to modify graphic (this shouldn't happen)"), 500

    # 4. Construct and check response
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": PREPROCESSOR_NAME,
        "data": data
    }

    try:
        validator = jsonschema.Draft7Validator(
            RESPONSE_SCHEMA, resolver=RESOLVER
            )
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed. Are schemas out of date?")
        logging.pii(
            f"Validation error: {e.message} | Response: {response}"
            )
        return jsonify("Failed to create response (shouldn't happen)"), 500

    logging.info(
        f"Modified 'graphic' in request {request_uuid}."
        )
    # logging.pii(response)
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
    app.run(host='0.0.0.0', port=80, debug=True)
