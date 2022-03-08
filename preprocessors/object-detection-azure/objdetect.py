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

import requests  # pip3 install requests
import json
import time
import jsonschema

import logging
import base64
import os
from flask import Flask, request, jsonify

app = Flask(__name__)


def process_results(result):
    send = []
    image_height = result["metadata"]["height"]
    image_width = result["metadata"]["width"]
    for item in range(len(result['objects'])):
        dims = result["objects"][item]['rectangle']
        x_left = dims['x'] / image_width
        x_right = (dims['x'] + dims['w']) / image_width
        y_left = dims['y'] / image_height
        y_right = (dims['y'] + dims['h']) / image_height
        centre = [abs((x_left + x_right) / 2),
                  abs((y_left + y_right) / 2)]
        area = abs((dims['w'] * dims['h']) / (image_height * image_width))
        class_prob = float(result['objects'][item]['confidence'])
        normalised_dims = [x_left, y_left, x_right, y_right]
        dictionary = {"ID": item,
                      "type": result['objects'][item]['object'],
                      "dimensions": normalised_dims,
                      "confidence": class_prob,
                      "centroid": centre,
                      "area": area
                      }
        send.append(dictionary)
    return send


def process_image(image):

    region = "canadacentral"  # For example, "westus"

    try:
        api_key = os.environ["AZURE_API_KEY"]
    except Exception as e:
        logging.error(e)
        return "", 500

    # Set request headers
    headers = dict()
    headers['Ocp-Apim-Subscription-Key'] = api_key
    headers['Content-Type'] = 'application/octet-stream'

    # Set request querystring parameters
    """Only query categories"""
    params = {'visualFeatures': 'Objects'}

    # Make request and process response
    add = "https://{}.api.cognitive.microsoft.com/vision/v1.0/analyze"
    response = requests.request(
        'post',
        add.format(region),
        data=image,
        headers=headers,
        params=params
    )
    if response.status_code == 200 or response.status_code == 201:

        if 'content-length' in response.headers and \
                int(response.headers['content-length']) == 0:
            return "", 204
        elif 'content-type' in response.headers and \
                isinstance(response.headers['content-type'], str):
            if 'application/json' in response.headers['content-type'].lower():
                if response.content:
                    result = response.json()
                    label = process_results(result)
                else:
                    return "", 204
            else:
                return "", 204

    else:
        return "", 204

    return label


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    logging.debug("Received request")
    # load the schema
    with open('./schemas/preprocessors/object-detection.schema.json') \
            as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') \
            as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)

    content = request.get_json()
    try:
        validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 400
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.objectDetection"
    preprocess_output = content["preprocessors"]
    content_classifier = \
        "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
    # convert the uri to processable image
    if "graphic" not in content.keys():
        return "", 204
    else:
        if content_classifier in preprocess_output:
            content_classifier_output = \
                preprocess_output[content_classifier]
            content_label = \
                content_classifier_output["category"]
            if content_label == "photograph":
                source = content["graphic"]
                image_b64 = source.split(",")[1]
                binary = base64.b64decode(image_b64)
                pred = process_image(image=binary)
                type = {"objects": pred}
            else:
                """If the first classifier does not detect a photograph
                the second classifier should not process the request"""
                return "", 204
        else:
            """We are providing the user the ability to process a photograph
            even when the first classifier is absent, however it is
            recommended that the second classifier be used in conjunction
            with the first classifier."""
            source = content["graphic"]
            image_b64 = source.split(",")[1]
            binary = base64.b64decode(image_b64)
            pred = process_image(image=binary)
            type = {"objects": pred}
        try:
            validator = jsonschema.Draft7Validator(data_schema)
            validator.validate(type)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": name,
            "data": type
        }
        try:
            validator = jsonschema.Draft7Validator(schema,
                                                   resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
