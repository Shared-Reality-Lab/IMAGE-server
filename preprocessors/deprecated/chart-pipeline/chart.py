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
# If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.

import torch
from flask import Flask, request, jsonify
import json
import time
import jsonschema
import logging
import numpy as np
import base64
import cv2
from threading import Thread
from argparse import ArgumentParser

from pipeline import get_data_from_chart, pre_load_nets

"""
MODE 1: 'Cls' model permanent (switch between CPU and GPU), others temporary and directly loaded on GPU
MODE 2: All models permanent (switch all models between CPU and GPU) - Cls on GPU, others on CPU - without torch.empty_cache()
MODE 3: All models permanently on GPU
"""
class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
# Create app
app = Flask(__name__)

# Args
# parser = ArgumentParser()
# parser.add_argument("--mode", dest="mode", help="Mode of operation", default=1, type=int)
# parser.add_argument("--empty_cache", dest="empty_cache", help="Clear GPU cache after use", default=True, type=bool)
# parser.add_argument("--debug", dest="debug", help="Show intermediate results for debugging", default=False, type=bool)
# args = parser.parse_args()
args = Namespace(mode=1,empty_cache=True,debug=False)
print("-----------------------------------------------")
print("Mode: {}".format(args.mode))
print("Empty GPU cache: {}".format(args.empty_cache))
print("Debug: {}".format(args.debug))
print("------------------------------------------------\n")


# Setup and load models
methods = {}
if args.mode == 1:
    methods = pre_load_nets([1], methods)
if args.mode == 2:
    methods = pre_load_nets([2, 3, 4, 5], methods)
    for model in methods:
        methods[model][1].cpu()
    methods = pre_load_nets([1], methods)
if args.mode == 3:
    methods = pre_load_nets([1, 2, 3, 4, 5])
if args.empty_cache == True:
    torch.cuda.empty_cache()


# Function to restore models to the right place after exec
def ResetApp():
    if args.mode == 1:
        del methods[list(methods.keys())[-1]]
    if args.mode == 2:
        methods[list(methods.keys())[-1]][1].cpu()
    if args.empty_cache:
        torch.cuda.empty_cache()
    methods['Cls'][1].cuda(0)

def processImage(content):
    # Store reqd parameters for output json
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.chart"
    
    # Extraxt image from URI
    url = content["graphic"]
    image_b64 = url.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)
    return img, request_uuid, timestamp, name

def loadSchemas():
    with open('./schemas/preprocessors/chart-information.schema.json') as jsonfile:
                data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definition_schema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    
    schema_store = {
        schema['$id']: schema,
        definition_schema['$id']: definition_schema,
        data_schema['$id']: data_schema
    }

    resolver = jsonschema.RefResolver.from_schema(
            schema, store=schema_store)
    return data_schema, schema, definition_schema, schema_store, resolver,first_schema

@app.route("/preprocessor", methods=['POST', 'GET'])
def readImage():
    if request.method == 'POST':

        # Get request.json
        content = request.get_json()
        data_schema, schema, definition_schema, schema_store, resolver,first_schema = loadSchemas()
        try:
            validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
            validator.validate(content)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 400
        preprocess_output = content["preprocessors"]
        classifier_1 = \
            "ca.mcgill.a11y.image.preprocessor.firstCategoriser"
        if classifier_1 in preprocess_output:
            classifier_1_output\
                = preprocess_output[classifier_1]
            classifier_1_label = classifier_1_output["category"]
            if classifier_1_label=="chart":
                # Store reqd parameters for output json
                img, request_uuid, timestamp, name = processImage(content)

                # Process image using the model to get output json
                output = get_data_from_chart(img, methods, args)
                
                # Load schemas
               # data_schema, schema, definition_schema, schema_store, resolver = loadSchemas()

                # Validate model output with schema
                try:
                    validator = jsonschema.Draft7Validator(data_schema, resolver=resolver)
                    validator.validate(output)
                except jsonschema.exceptions.ValidationError as e:
                    logging.error(e)
                    return jsonify("Invalid Preprocessor JSON format"), 500

                # Format and create response json obj using output
                response = {
                    "title": "Chart Data",
                    "description": "Data extracted from the given chart",
                        "request_uuid": request_uuid,
                        "timestamp": int(timestamp),
                        "name": name,
                        "data": output
                        }
                
                # Validate final response
                try:
                    validator = jsonschema.Draft7Validator(schema, resolver=resolver)
                    validator.validate(response)
                except jsonschema.exceptions.ValidationError as e:
                    logging.error(e)
                    return jsonify("Invalid Preprocessor JSON format"), 500

                # Start thread to reset models            
                Thread(target=ResetApp).start()
                return jsonify(response)
            else:
                return (''), 204
        else:
            img, request_uuid, timestamp, name = processImage(content)
            # Process image using the model to get output json
            output = get_data_from_chart(img, methods, args)
            
            # Load schemas
            data_schema, schema, definition_schema, schema_store, resolver = loadSchemas()
            # Validate model output with schema
            try:
                validator = jsonschema.Draft7Validator(data_schema, resolver=resolver)
                validator.validate(output)
            except jsonschema.exceptions.ValidationError as e:
                logging.error(e)
                return jsonify("Invalid Preprocessor JSON format"), 500

            # Format and create response json obj using output
            response = {
                "title": "Chart Data",
                "description": "Data extracted from the given chart",
                    "request_uuid": request_uuid,
                    "timestamp": int(timestamp),
                    "name": name,
                    "data": output
                    }
            
            # Validate final response
            try:
                validator = jsonschema.Draft7Validator(schema, resolver=resolver)
                validator.validate(response)
            except jsonschema.exceptions.ValidationError as e:
                logging.error(e)
                return jsonify("Invalid Preprocessor JSON format"), 500

            # Start thread to reset models            
            Thread(target=ResetApp).start()
            return jsonify(response)

    return "Expected POST request, got GET request instead."


if __name__ == '__main__':

    # Run app
    app.run(host='0.0.0.0', port=5000)
