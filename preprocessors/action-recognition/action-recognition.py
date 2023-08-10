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

import os
import json
import time
import jsonschema
import logging
import base64
from flask import Flask, request, jsonify
import numpy as np
from torchvision import transforms
import torch
from PIL import Image
from io import BytesIO

from utils import detect

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
app = Flask(__name__)


@app.route("/preprocessor", methods=['POST', ])
def run(weights="/app/model.pth",
        conf_thres=0.5,
        imgsz=224,
        padding=0.3,
        mean=[0.5397, 0.5037, 0.4667],
        std=[0.2916, 0.2850, 0.2944],
        device=torch.device("cuda:0")
        ):
    logging.debug("Received request")
    data = []

    # load schemas
    with open('./schemas/preprocessors/action.schema.json') \
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
    name = "ca.mcgill.a11y.image.preprocessor.actionRecognition"
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
        pil_image = Image.open(BytesIO(image))
        img_original = np.array(pil_image)
        height, width, channels = img_original.shape
        for i in range(len(objects)):
            if ("person" in objects[i]["type"]):
                person_id = int(objects[i]["ID"])
                xleft = int(objects[i]["dimensions"][0] * width)
                xright = int(objects[i]["dimensions"][2] * width)
                ybottom = int(objects[i]["dimensions"][1] * height)
                ytop = int(objects[i]["dimensions"][3] * height)

                # preprocess
                h = ytop - ybottom
                w = xright - xleft
                dim = int(max(h, w) * (1 + padding))
                img = transforms.ToTensor()(img_original)
                top = (h - dim) + ytop
                left = xleft - (w - dim)
                img = transforms.functional.crop(
                    img, top=top, left=left, height=dim, width=dim)
                img = transforms.Resize(size=[imgsz, ], antialias=True)(img)
                img = transforms.Normalize(mean=mean, std=std)(img)

                action = detect(img,
                                person_id,
                                conf_thres,
                                weights,
                                device)
                if action:
                    data.append(action)
        final = {"actions": data}
        try:
            validator = jsonschema.Draft7Validator(data_schema)
            validator.validate(final)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": name,
            "data": final
        }
        # validate results
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
    run()
