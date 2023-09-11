# Copyright (c) 2023 IMAGE Project, Shared Reality Lab, McGill University
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
import gc
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

from utils import detect, Classifier

app = Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG,  # Set the desired logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional: Specify date and time format
)

assert torch.cuda.is_available(), "CUDA not available, failing early"

WEIGHTS = "/app/model.pth"
assert os.path.isfile(WEIGHTS), "Model weights not found, failing early"

MODEL = Classifier()
MODEL.load_state_dict(torch.load(WEIGHTS)['model'])


@app.route("/preprocessor", methods=['POST'])
def run():
    conf_thres = 0.7
    imgsz = 224
    padding = 0.3
    mean = [0.5397, 0.5037, 0.4667]
    std = [0.2916, 0.2850, 0.2944]
    data = []

    global MODEL

    logging.info("Received request")
    gc.collect()
    torch.cuda.empty_cache()

    # load schemas
    logging.info("Validating schemas")
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
    logging.info("Schemas validated")

    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.actionRecognition"
    preprocessor = content["preprocessors"]
    # convert the uri to processable image
    if "graphic" not in content.keys():
        logging.info("Not image content. Skipping ...")
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
        pil_image = Image.open(BytesIO(image)).convert("RGB")
        people = [person for person in objects if "person" in person["type"]]
        try:
            try:
                MODEL = MODEL.to("cuda")
            except Exception as e:
                logging.error("Error while loading model on GPU: {}".format(e))
                return jsonify("Error while loading model on GPU"), 500

            if len(people) == 1:
                # don't crop if only one person detected
                logging.info("Running action detection on the person found")
                person_id = int(people[0]["ID"])
                img = pil_image.resize((imgsz, imgsz))
                img = transforms.ToTensor()(img)
                img = transforms.Normalize(mean=mean, std=std)(img)
                action = detect(img, person_id, conf_thres, MODEL)
                if action:
                    data.append(action)

            else:
                logging.info("Running action detection on each person found")
                img_original = np.array(pil_image)
                height, width, channels = img_original.shape
                for person in people:
                    person_id = int(person["ID"])
                    xleft = int(person["dimensions"][0] * width)
                    xright = int(person["dimensions"][2] * width)
                    ybottom = int(person["dimensions"][1] * height)
                    ytop = int(person["dimensions"][3] * height)
                    # preprocess
                    h = ytop - ybottom
                    w = xright - xleft
                    dim = int(max(h, w) * (1 + padding))
                    img = transforms.ToTensor()(img_original)
                    top = (h - dim) + ytop
                    left = xleft - (w - dim)
                    img = transforms.functional.crop(
                        img, top=top, left=left, height=dim, width=dim)
                    img = transforms.Resize(
                        size=[imgsz, ], antialias=True)(img)
                    img = transforms.Normalize(mean=mean, std=std)(img)
                    action = detect(img, person_id, conf_thres, MODEL)
                    if action:
                        data.append(action)

            MODEL.to("cpu")

        except Exception as e:
            logging.error(f"Error while predicting actions: {e}")
            return jsonify("Error while predicting actions"), 500

        final = {"actions": data}
        logging.info("Validating results schema")
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
        logging.info("Schema validated")
        logging.info("Returning response")
        return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
