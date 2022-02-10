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
# <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.


import json
import time
import logging
import jsonschema
import os
import io
import base64
from flask import Flask, request, jsonify
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes # noqa
from msrest.authentication import CognitiveServicesCredentials

app = Flask(__name__)


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_ocr_text():
    """
    Gets data on locations nearby a map from the Autour API
    """

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
    if 'image' not in content:
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
        logging.error(error)
        return jsonify("Invalid Request JSON format"), 400
    # Use response schema to validate response
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
    # Get OCR text response
    ocr_result = analyze_image(content['graphic'])

    if ocr_result is None:
        return jsonify("Could not retreive Azure results"), 400

    name = 'ca.mcgill.a11y.image.preprocessor.ocr'
    request_uuid = content['request_uuid']
    timestamp = int(time.time())
    data = {'lines': ocr_result}

    try:
        validator = jsonschema.Draft7Validator(data_schema, resolver=resolver)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as error:
        logging.error(error)
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
        logging.error(error)
        return jsonify("Invalid Preprocessor JSON format"), 500

    return response


def analyze_image(source):
    """
    Gets OCR text data from Azure API
    """

    # Convert URI to binary stream

    image_b64 = source.split(",")[1]
    binary = base64.b64decode(image_b64)
    stream = io.BytesIO(binary)

    subscription_key = os.environ["AZURE_API_KEY"]
    endpoint = "https://image-cv.cognitiveservices.azure.com/"

    computervision_client = ComputerVisionClient(
        endpoint, CognitiveServicesCredentials(subscription_key))

    read_response = computervision_client.read_in_stream(stream,  raw=True)

    read_operation_location = read_response.headers["Operation-Location"]
    # Grab the ID from the URL
    operation_id = read_operation_location.split("/")[-1]

    # Call the "GET" API and wait for it to
    # retrieve the results barring timeout

    start_time = time.time()

    while True:
        read_result = computervision_client.get_read_result(operation_id)
        if read_result.status not in ['notStarted', 'running']:
            break
        if time.time() - start_time > 3:
            logging.error("Azure request timed out")
            return None
        time.sleep(1)

    # Check for success
    if read_result.status == OperationStatusCodes.succeeded:
        ocr_results = []
        for analyzed_result in read_result.analyze_result.read_results:
            for line in analyzed_result.lines:
                line_data = {
                    "text": line.text,
                    "bounding_box": line.bounding_box
                }
                ocr_results.append(line_data)
        return ocr_results
    else:
        logging.error("OCR text: {}".format(read_result.status))
        return None


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
