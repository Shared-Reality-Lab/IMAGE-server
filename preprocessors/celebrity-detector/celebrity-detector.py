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

import os
import json
import time
import jsonschema
import logging
import base64
from flask import Flask, request, jsonify
import cv2
import numpy as np

app = Flask(__name__)

# extract the required results from the API returned values


def process_results(response, labels):
    logging.debug(response)
    if not response["categories"]:
        return labels[0], []
    else:
        category_dict = {i["name"]: i["score"] for i in response["categories"]}
        celeb = response["categories"]
        celeb_list = []
        for i in range(len(celeb)):
            if ("detail" in celeb[i]):
                if ("celebrities" in celeb[i]["detail"]):
                    if (len(celeb[i]["detail"]["celebrities"]) != 0):
                        celeb_list.append(*celeb[i]["detail"]["celebrities"])
        celeb_sorted = sorted(celeb_list, key=lambda d: d['confidence'])
        logging.debug(celeb_sorted)
        label = max(category_dict.items(), key=operator.itemgetter(1))[0]
        if any(search(i, label) for i in labels):
            for i in labels:
                if i in label:
                    return i, celeb_sorted
        else:
            return labels[0], celeb_sorted


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
    params = {'visualFeatures': 'Categories',
              'details': 'Celebrities'
              }

    # Make request and process response
    response = requests.request(
        'post',
        "https://{}.api.cognitive.microsoft.com/vision/v1.0/analyze".format(
            region),
        data=image,
        headers=headers,
        params=params
    )
    if response.status_code == 400:
        logging.debug(response)
    if response.status_code == 200 or response.status_code == 201:

        if 'content-length' in response.headers and \
                int(response.headers['content-length']) == 0:
            return [], []
        elif 'content-type' in response.headers and \
                isinstance(response.headers['content-type'], str):
            if 'application/json' in response.headers['content-type'].lower():
                if response.content:
                    result = response.json()
                    label, celeb = process_results(
                        response=result, labels=labels)
                else:
                    return [], []
            elif 'image' in response.headers['content-type'].lower():
                return [], []

    else:
        return [], []

    return label, celeb


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    final_data = []
    logging.debug("Received request")
    # load the schema
    labels = ["other", "indoor", "outdoor", "people"]
    with open('./schemas/preprocessors/celebrity.schema.json') \
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
    preprocessor_name = "ca.mcgill.a11y.image.preprocessor.celebrityDetector"
    preprocessor = content["preprocessors"]
    # convert the uri to processable image
    if "graphic" not in content.keys():
        return "", 204
    if "ca.mcgill.a11y.image.preprocessor.objectDetection" \
            not in preprocessor:
        logging.info("Object detection output not "
                     "available. Skipping...")
        return "", 204
    else:
        oDpreprocessor = \
            preprocessor["ca.mcgill.a11y.image.preprocessor.objectDetection"]
        objects = oDpreprocessor["objects"]
        image_b64 = content["graphic"].split(",")[1]
        binary = base64.b64decode(image_b64)
        image = np.asarray(bytearray(binary), dtype="uint8")
        pil_image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        img_original = np.array(pil_image)
        height, width, channels = img_original.shape
        for i in range(len(objects)):
            # print(objects[i]["type"])
            if ("person" in objects[i]["type"]):
                # object_type.append(objects[i]["type"])
                # dimensions.append(objects[i]["dimensions"])
                # area.append(objects[i]["area"])
                dimx = int(objects[i]["dimensions"][0] * width)
                dimx1 = int(objects[i]["dimensions"][2] * width)
                dimy = int(objects[i]["dimensions"][1] * height)
                dimy1 = int(objects[i]["dimensions"][3] * height)
                img = img_original[dimy:dimy1, dimx:dimx1]
                buffer = cv2.imencode('.jpg', img)[1].tostring()
                pred, celeb = process_image(image=buffer, labels=labels)
                print(celeb)
                if (len(celeb) == 0):
                    name = "None"
                    conf = 0
                else:
                    celeb = celeb[0]
                    conf = celeb["confidence"]
                    name = celeb["name"]

                celebrities = {
                    "personID": objects[i]["ID"],
                    "name": name,
                    "confidence": conf
                }
                final_data.append(celebrities)
        data = {"celebrities": final_data}
        try:
            validator = jsonschema.Draft7Validator(data_schema)
            validator.validate(data)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": preprocessor_name,
            "data": data
        }
        # validate the results to check if they are in correct format
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
    app.run(host='0.0.0.0', port=5001, debug=True)
