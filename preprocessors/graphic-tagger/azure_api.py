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

import requests  # pip3 install requests
from re import search
import operator

# import numpy as np
import json
import time
import jsonschema
import logging
import base64
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# extract the required results from the API returned values


def process_results(response, labels):
    if not response["categories"]:
        return labels[0]
    else:
        category_dict = {i["name"]: i["score"] for i in response["categories"]}

        label = max(category_dict.items(), key=operator.itemgetter(1))[0]
        if any(search(i, label) for i in labels):
            for i in labels:
                if i in label:
                    return i
        else:
            return labels[0]

# this function takes in the image and send the image to Azure to get the
# output


def process_image(image, labels):

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
    # params = {'visualFeatures': 'Color,Categories,
    # Tags,Description,ImageType,Faces,Adult,Objects'}
    """Only query categories"""
    params = {'visualFeatures': 'Categories'}

    # Make request and process response
    response = requests.request(
        'post',
        "https://{}.api.cognitive.microsoft.com/vision/v1.0/analyze".format(
            region),
        data=image,
        headers=headers,
        params=params
    )

    if response.status_code == 200 or response.status_code == 201:

        if 'content-length' in response.headers and \
                int(response.headers['content-length']) == 0:
            return "Invalid response from azure", 500
        elif 'content-type' in response.headers and \
                isinstance(response.headers['content-type'], str):
            if 'application/json' in response.headers['content-type'].lower():
                if response.content:
                    result = response.json()
                    label = process_results(response=result, labels=labels)
                else:
                    return "Response content missing", 500
            elif 'image' in response.headers['content-type'].lower():
                return "Azure response not in json format", 500

    else:
        return response.status_code

    return label


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    logging.debug("Received request")
    # load the schema
    labels = ["other", "indoor", "outdoor", "people"]
    with open('./schemas/preprocessors/graphic-tagger.schema.json') \
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
    name = "ca.mcgill.a11y.image.preprocessor.graphicTagger"
    preprocess_output = content["preprocessors"]
    content_classifier\
        = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
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
                pred = process_image(image=binary, labels=labels)
                type = {"category": pred}
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
            pred = process_image(image=binary, labels=labels)
            type = {"category": pred}
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
        # validate the results to check if they are in correct format
        try:
            validator = jsonschema.Draft7Validator(schema,
                                                   resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug(type)
        return response


@app.route('/health', methods=['GET'])
def health():
    """
    health check endpoint to verify if the service is up.
    """
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)