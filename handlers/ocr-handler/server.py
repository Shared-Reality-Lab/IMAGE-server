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
        logging.debug("No OCR preprocessor found")
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
        logging.debug("OCR lines empty")
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
    if 'ca.mcgill.a11y.image.renderer.Text' not in content['renderers']:
        logging.debug("Text renderer not supported")
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

    # Text to be returned
    text = ""

    # Object detection data is present
    od = 'ca.mcgill.a11y.image.preprocessor.objectDetection'
    if od in preprocessors and len(preprocessors[od]['objects']) > 0:
        object_data = preprocessors[od]
        retmaining_text = ocr_data['lines']
        remaining_objects = [{key: obj[key] for key
                              in ['type', 'dimensions']} for
                             obj in object_data['objects']]
        text += "The following objects were detected: "
        for obj in remaining_objects:
            obj_dims = get_dims(obj)
            obj_text = ""
            for i, line in enumerate(retmaining_text):
                lines_to_remove = []
                text_dims = get_dims(line)
                if is_contained(text_dims, obj_dims):
                    obj_text += line['text'] + ", "
                    lines_to_remove.append(i)
            # Add the appropraite article of the object
            # as well as the object type to the text
            text += get_article(obj['type']) + obj['type']
            if len(obj_text) > 0:
                obj_text = obj_text[:-2]
                text += "containing the text: " + obj_text + ". "
            # Remove lines already found
            for i in lines_to_remove:
                retmaining_text.pop(i)
        if len(retmaining_text) > 0:
            text += "The remaining text not contained in any detected object: "
            for line in retmaining_text:
                text += line['text'] + ", "
        text = text[:-1]

    else:
        # Get text renderer data
        text += 'The following ' + str(len(ocr_data['lines']))
        text += ' lines were found in the image: '
        for line in ocr_data['lines']:
            line_text = line['text'] + ', '
            text += line_text
        text = text[:-2]

    response = {
        "request_uuid": content["request_uuid"],
        "timestamp": int(time.time()),
        "renderings": [
            {
                "type_id": "ca.mcgill.a11y.image.renderer.Text",
                "description": "The text found in a graphic.",
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


def get_dims(obj):
    """
    Returns a dict with [ulx, uly, lrx, lry]
    of the object box
    """
    # If the object is not a region of text
    # its bounding box is called "dimensions"
    # so the key is set accordingly
    if "dimensions" in obj:
        key = "dimensions"
    # Otherwise, the key is "bounding_box"
    # for regions of text
    else:
        key = "bounding_box"
    obj_box = {
        'ulx': obj[key][0],
        'uly': obj[key][1],
        'lrx': obj[key][2],
        'lry': obj[key][3]
    }
    return obj_box


def is_contained(text_dims, obj_dims):
    """
    Checks if text is contained in object
    """
    if text_dims['ulx'] < obj_dims['ulx']:
        return False
    if text_dims['uly'] < obj_dims['uly']:
        return False
    if text_dims['lrx'] > obj_dims['lrx']:
        return False
    if text_dims['lry'] > obj_dims['lry']:
        return False
    return True


def get_article(word):
    """
    Returns the indefinite article of the word
    """
    if word[0] in ['a', 'e', 'i', 'o', 'u']:
        return 'an '
    return 'a '


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
