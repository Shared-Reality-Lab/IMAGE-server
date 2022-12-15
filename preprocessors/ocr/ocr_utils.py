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

import time
import logging
import os
import requests
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes # noqa
from msrest.authentication import CognitiveServicesCredentials
from google.cloud import vision

# Pull key value and declare endpoint for Azure OCR API
azure_subscr_key = os.environ["AZURE_API_KEY"]
azure_endpoint = "https://image-cv.cognitiveservices.azure.com/"

# Pull key value and declare endpoint for Free OCR API
freeocr_subscription_key = os.environ["FREEOCR_API_KEY"]
freeocr_endpoint = "https://api.ocr.space/parse/image"


def process_azure_read(stream, width, height):
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
                bg_bx = [bbx[0], bbx[1], bbx[4], bbx[5]]
                bounding_box = normalize_bdg_box(bg_bx, width, height)
                ocr_results.append({
                    'text': line_text,
                    'bounding_box': bounding_box
                })
        return ocr_results
    else:
        logging.error("OCR text: {}".format(read_result.status))
        return None


def process_azure_read_v4_preview(stream, width, height):
    headers = {
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': azure_subscr_key,
    }

    param = "features=Read&model-version=latest&api-version=2022-10-12-preview"
    ocr_url = azure_endpoint + "computervision/imageanalysis:analyze?" + param

    response = requests.post(ocr_url, headers=headers, data=stream)
    response.raise_for_status()

    read_result = response.json()

    # Check for success
    if (len(read_result['readResult']) == 0):
        logging.error("No READ response")
        return None
    else:
        ocr_results = []
        for page in read_result['readResult']['pages']:
            for line in page['lines']:
                line_text = line['content']
                # Get normalized bounding box for each line
                bbx = line['boundingBox']
                bg_bx = [bbx[0], bbx[1], bbx[4], bbx[5]]
                bounding_box = normalize_bdg_box(bg_bx, width, height)
                ocr_results.append({
                    'text': line_text,
                    'bounding_box': bounding_box
                })
        return ocr_results


def process_azure_ocr(stream, width, height):
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
        bb = region['boundingBox'].split(",")
        maxX = float(bb[0]) + float(bb[2])
        maxY = float(bb[1]) + float(bb[3])
        bndng_bx = [float(bb[0]), float(bb[1]), maxX, maxY]
        bounding_box = normalize_bdg_box(bndng_bx, width, height)
        ocr_results.append({
            'text': region_text,
            'bounding_box': bounding_box
        })
    if not ocr_results:
        return None
    return ocr_results


def process_free_ocr(source, width, height):
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
        maxY = line['MinTop'] + line['MaxHeight']
        maxX = line['Words'][-1]['Left'] + line['Words'][-1]['Width']
        bndng_bx = [line['Words'][0]['Left'], line['MinTop'],
                    maxX, maxY]
        bounding_box = normalize_bdg_box(bndng_bx, width, height)
        ocr_results.append({
            'text': line_text,
            'bounding_box': bounding_box
        })
    return ocr_results


def process_google_vision(image_b64, width, height):
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
        bndng_bx = [word.bounding_poly.vertices[0].x,
                    word.bounding_poly.vertices[0].y,
                    word.bounding_poly.vertices[2].x,
                    word.bounding_poly.vertices[2].y]
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


def find_obj_enclosing(prepr_name, list_data, ocr_lines):
    objs = [{key: obj[key] for key
             in ['ID', 'dimensions']} for
            obj in list_data['objects']]
    for line in ocr_lines:
        obj_enclosing = [
            obj for obj in objs if is_contained(get_dims(line), get_dims(obj))
        ]
        if len(obj_enclosing) > 0:
            oid_dim = {obj['ID']: get_area(obj) for obj in obj_enclosing}
            if 'enclosed_by' not in line.keys():
                line['enclosed_by'] = []
            line['enclosed_by'].append({
                'preprocessor': prepr_name,
                'ID': min(oid_dim, key=oid_dim.get)
            })
    return ocr_lines


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
        'ulx': obj[key][0],  # x - left edge
        'uly': obj[key][1],  # y - top edge
        'lrx': obj[key][2],  # x - right edge
        'lry': obj[key][3]   # y - bottom edge
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


def get_area(obj):
    """
    Returns the area
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
    return obj[key][2] * obj[key][3]
