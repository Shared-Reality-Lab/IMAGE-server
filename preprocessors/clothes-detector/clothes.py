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
import jsonschema
import logging
import base64
from flask import Flask, request, jsonify
import cv2
import numpy as np
from PIL import Image
import torch
from webcolors import (
    CSS3_HEX_TO_NAMES,
    hex_to_rgb,
)
import io
from scipy.spatial import KDTree

from colorthief import ColorThief
from yolo.utils.utils import load_classes
from predictors.YOLOv3 import YOLOv3Predictor

app = Flask(__name__)
logging.basicConfig(level=logging.NOTSET)

# code referred from
# https://medium.com/codex/rgb-to-color-names-in-python-the-robust-way-ec4a9d97a01f


def convert_rgb_to_names(rgb_tuple):
    # a dictionary of all the hex and their respective names in css3
    css3_db = CSS3_HEX_TO_NAMES
    names = []
    rgb_values = []
    for color_hex, color_name in css3_db.items():
        names.append(color_name)
        rgb_values.append(hex_to_rgb(color_hex))
    kdt_db = KDTree(rgb_values)
    distance, index = kdt_db.query(rgb_tuple)
    return names[index]


def get_clothes(img):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.cuda.empty_cache()

    # YOLO PARAMS
    yolo_params = {"model_def": "yolo/df2cfg/yolov3-df2.cfg",
                   "weights_path": "yolo/weights/yolov3-df2_15000.weights",
                   "class_path": "yolo/df2cfg/df2.names",
                   "conf_thres": 0.5,
                   "nms_thres": 0.4,
                   "img_size": 416,
                   "device": device}
    logging.info("loading YOLO")
    classes = load_classes(yolo_params["class_path"])
    detectron = YOLOv3Predictor(params=yolo_params)
    logging.info("getting clothes information")
    detections = detectron.get_detections(img)
    logging.info("retrieved clothes information")
    clothes = []
    for x1, y1, x2, y2, cls_conf, cls_pred in detections:
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        y1 = 0 if y1 < 0 else y1
        x1 = 0 if x1 < 0 else x1
        logging.info("Cropping clothes to get dominant color")
        img_crop = img[y1:y2][x1:x2]
        try:
            image = Image.fromarray(img_crop)
            byte_object = io.BytesIO()
            image.save(byte_object, 'JPEG')
            color_thief = ColorThief(byte_object)
            logging.info("Getting dominant color")
            dominant_color = color_thief.get_color(quality=1)
            closest_name = convert_rgb_to_names(dominant_color)
        except ValueError:
            closest_name = None
        print("Item: %s, Conf: %.5f" % (classes[int(cls_pred)], cls_conf))
        clothes.append({"article": classes[int(
            cls_pred)], "confidence": cls_conf, "color": closest_name})
        break
    return clothes


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    final_data = []
    logging.debug("Received request")
    with open('./schemas/preprocessors/clothes.schema.json') \
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
    preprocessor_name = "ca.mcgill.a11y.image.preprocessor.clothesDetector"
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
        logging.info("Image decoded")
        height, width, channels = img_original.shape
        for i in range(len(objects)):
            # print(objects[i]["type"])
            if ("person" in objects[i]["type"]):
                dimx = int(objects[i]["dimensions"][0] * width)
                dimx1 = int(objects[i]["dimensions"][2] * width)
                dimy = int(objects[i]["dimensions"][1] * height)
                dimy1 = int(objects[i]["dimensions"][3] * height)
                img = img_original[dimy:dimy1, dimx:dimx1]
                logging.info("Person detected, getting clothes information")
                cloth_list = get_clothes(img)
                if (len(cloth_list) == 0):

                    cloth_list = [
                        {"article": "None", "confidence": 0, "color": None}]

                clothes = {
                    "personID": objects[i]["ID"],
                    "attire": cloth_list
                    # "confidence": conf
                }
                final_data.append(clothes)
                logging.info(final_data)
        data = {"clothes": final_data}
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


@app.route('/health', methods=['GET'])
def health():
    """
    health check endpoint to verify if the service is up.
    """
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
