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
import requests
from flask import Flask, request, jsonify
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes # noqa
from msrest.authentication import CognitiveServicesCredentials
from google.cloud import vision

app = Flask(__name__)


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
        logging.error(error)
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

    name = 'ca.mcgill.a11y.image.preprocessor.ocrClouds'
    request_uuid = content['request_uuid']
    timestamp = int(time.time())
    data = {'lines': ocr_result, 'cloud_service': cld_srv_optn}

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

    # Pull key value and declare endpoint for Azure OCR API
    azure_subscr_key = os.environ["AZURE_API_KEY"]
    azure_endpoint = "https://image-cv.cognitiveservices.azure.com/"

    # Pull key value and declare endpoint for Free OCR API
    freeocr_subscription_key = os.environ["FREEOCR_API_KEY"]
    freeocr_endpoint = "https://api.ocr.space/parse/image"

    if cld_srv_optn == "READ_AZURE":
        computervision_client = ComputerVisionClient(
            azure_endpoint, CognitiveServicesCredentials(azure_subscr_key))
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
            for region in read_result.analyze_result.read_results:
                for line in region.lines:
                    line_text = line.text
                    # Get normalized bounding box for each line
                    bbx = line.bounding_box
                    bg_bx = [bbx[0], bbx[7], (bbx[2]-bbx[0]), (bbx[5]-bbx[3])]
                    bounding_box = normalize_bdg_box(bg_bx, width, height)
                    ocr_results.append({
                        'text': line_text,
                        'bounding_box': bounding_box
                    })
            return ocr_results
        else:
            logging.error("OCR text: {}".format(read_result.status))
            return None

    elif cld_srv_optn == "OCR_AZURE":
        headers = {
            'Content-Type': 'application/octet-stream',
            'Ocp-Apim-Subscription-Key': azure_subscr_key,
        }

        ocr_url = azure_endpoint + "vision/v3.2/ocr"

        response = requests.post(ocr_url, headers=headers, data=stream)
        response.raise_for_status()

        read_result = response.json()

        ocr_results = []
        for region in read_result['regions']:
            region_text = ""
            for line in region['lines']:
                for word in line['words']:
                    region_text += word['text'] + " "
            region_text = region_text[:-1]
            # Get normalized bounding box for each region
            bndng_bx = region['boundingBox'].split(",")
            bounding_box = normalize_bdg_box(bndng_bx, width, height)
            ocr_results.append({
                'text': region_text,
                'bounding_box': bounding_box
            })
        if not ocr_results:
            return None
        return ocr_results

    elif cld_srv_optn == "OCR_FREE":
        payload = {
            'base64Image': source,
            'apikey': freeocr_subscription_key,
            'isOverlayRequired': True
        }
        response = requests.post(freeocr_endpoint, data=payload)
        read_result = response.json()

        # Check for success
        if not read_result['ParsedResults']:
            return None

        ocr_results = []
        for line in read_result['ParsedResults'][0]['TextOverlay']['Lines']:
            line_text = line['LineText']
            # Get normalized bounding box for each line
            lnDown = line['MaxHeight'] + line['MinTop']
            lnWidth = line['Words'][-1]['Left'] - line['Words'][0]['Left']
            bndng_bx = [line['Words'][0]['Left'], lnDown,
                        lnWidth, line['MaxHeight']]
            bounding_box = normalize_bdg_box(bndng_bx, width, height)
            ocr_results.append({
                'text': line_text,
                'bounding_box': bounding_box
            })
        return ocr_results

    elif cld_srv_optn == "VISION_GOOGLE":
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_b64)
        response = client.text_detection(image=image)

        # Check for success
        if response.error.message:
            logging.error(response.error.message)
            return None

        ocr_results = []

        for word in response.text_annotations[1:]:
            text = word.description
            # Get normalized bounding box for each word
            wordWidth = (
                word.bounding_poly.vertices[1].x
                - word.bounding_poly.vertices[0].x
            )
            wordHeight = (
                word.bounding_poly.vertices[2].y
                - word.bounding_poly.vertices[1].y
            )
            bndng_bx = [word.bounding_poly.vertices[0].x,
                        word.bounding_poly.vertices[3].y,
                        wordWidth, wordHeight]
            bounding_box = normalize_bdg_box(bndng_bx, width, height)
            ocr_results.append({
                'text': text,
                'bounding_box': bounding_box
            })
        return ocr_results


def normalize_bdg_box(bndng_bx, width, height):
    for i, val in enumerate(bndng_bx):
        if i % 2 == 0:
            bndng_bx[i] = int(val) / width
        else:
            bndng_bx[i] = int(val) / height
    return bndng_bx


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
