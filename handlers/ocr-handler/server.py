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
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/handler', methods=['POST', 'GET'])
def render_ocr():
    """
    Creates a rendering for text found in images
    """

    logging.debug("Received request")
    # Load schemas
    with open('./schemas/handler-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definition_schema = json.load(jsonfile)
    schema_store = {
        schema['$id']: schema,
        definition_schema['$id']: definition_schema
    }
    
    # Get request data
    content = request.get_json()
    
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
    
    # Check preprocessor data
    preprocessors = content['preprocessors']
    
    # No OCR preprocessor
    if 'ca.mcgill.a11y.image.preprocessor.ocr' not in preprocessors:
        logging.error("No OCR preprocessor found")
        response = {
            "request_uuid": content["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response
    
    ocr_data = preprocessors['ca.mcgill.a11y.image.preprocessor.ocr']
    
    # OCR lines empty
    if len(ocr_data['lines']) == 0:
        logging.error("OCR lines empty")
        response = {
            "request_uuid": content["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    # Text renderer not supported
    if 'ca.mcgill.a11y.image.renderer.Tsext' not in content['renderers']:
        logging.error("Text renderer not supported")
        response = {
            "request_uuid": content["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response
    
    # Get text renderer data
    text = 'This following lines of text were found in the image: '
    for i, line in enumerate(ocr_data['lines']):
        line_text = 'start of ' + str(i+1) + 'th line :' + line['text'] + '. End of ' + str(i+1) + 'th line. '
        text += line_text
    
    response = {
        "request_uuid": content["request_uuid"],
        "timestamp": int(time.time()),
        "renderings": [
            {
                "type_id": "ca.mcgill.a11y.image.renderer.Text",
                "confidence": 50,
                "description": "The text found in an image.",
                "data": {
                    "text": text
                }
            }
        ]
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as error:
        logging.error(error)
        return jsonify("Invalid Preprocessor JSON format"), 500
    logging.debug("Sending response")
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
