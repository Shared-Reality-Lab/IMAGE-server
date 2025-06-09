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
#
# This was built using the AdelaiDepth library that can be found at
# https://github.com/aim-uofa/AdelaiDepth

import cv2
import argparse
import numpy as np
import torch
import torchvision.transforms as transforms
from flask import Flask, request, jsonify
from collections import OrderedDict
import json
import time
import jsonschema
import logging
import base64
from lib.multi_depth_model_woauxi import RelDepthModel
from datetime import datetime
from config.logging_utils import configure_logging

configure_logging()

app = Flask(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Configs for LeReS')
    parser.add_argument('--load_ckpt', default='./res50.pth',
                        help='Checkpoint path to load')
    parser.add_argument('--backbone', default='resnext101',
                        help='Checkpoint path to load')

    args = parser.parse_args()
    return args


def strip_prefix_if_present(state_dict, prefix):
    keys = sorted(state_dict.keys())
    if not all(key.startswith(prefix) for key in keys):
        return state_dict
    stripped_state_dict = OrderedDict()
    for key, value in state_dict.items():
        stripped_state_dict[key.replace(prefix, "")] = value
    return stripped_state_dict


def scale_torch(img):
    """
    Scale the image and output it in torch.tensor.
    :param img: input rgb is in shape [H, W, C],
    input depth/disp is in shape [H, W]
    :param scale: the scale factor. float
    :return: img. [C, H, W]
    """
    if len(img.shape) == 2:
        img = img[np.newaxis, :, :]
    if img.shape[2] == 3:
        transform = transforms.Compose([transforms.ToTensor(),
                                        transforms.Normalize(
                                        (0.485, 0.456, 0.406),
                                        (0.229, 0.224, 0.225))])
        img = transform(img)
    else:
        img = img.astype(np.float32)
        img = torch.from_numpy(img)
    return img


@app.route("/preprocessor", methods=['POST', ])
def depthgenerator():
    logging.debug("Received request")
    # load the schema
    with open('./schemas/preprocessors/depth-map-generator.schema.json') \
            as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') \
            as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    # Following 6 lines of code
    # refered from
    # https://stackoverflow.com/questions/42159346/jsonschema-refresolver-to-resolve-multiple-refs-in-python
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
        logging.error("Validation failed for incoming request")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid Preprocessor JSON format"), 400

    # check content category from contentCategoriser
    preprocess_output = content.get("preprocessors", {})
    classifier_1 = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
    if classifier_1 in preprocess_output:
        classifier_1_output = preprocess_output[classifier_1]
        classifier_1_label = classifier_1_output.get("category", "")
        if classifier_1_label != "photograph":
            logging.info("Not photograph content. Skipping...")
            return "", 204
    else:
        logging.info("Content categorizer output missing. Skipping...")
        return "", 204

    # check for image
    if "graphic" not in content:
        logging.info("Request is not a graphic. Skipping...")
        return "", 204  # No content
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.depth-map-gen"

    # convert the uri to processable image
    # Following 4 lines of code
    # refered form
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = content["graphic"]
    image_b64 = source.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)

    # create depth model
    depth_model = RelDepthModel(backbone='resnext101')
    depth_model.eval()

    # load checkpoint
    try:
        checkpoint = torch.load("/app/res101.pth")
        depth_model.load_state_dict(strip_prefix_if_present(
                                    checkpoint['depth_model'], "module."),
                                    strict=True)
    except Exception as e:
        logging.error("Error loading model checkpoint")
        logging.pii(f"Checkpoint load error: {e}")
        return jsonify("Depth Model cannot complete"), 500
    finally:
        del checkpoint
        torch.cuda.empty_cache()

    depth_model.cuda()

    rgb_c = img[:, :, ::-1].copy()
    A_resize = cv2.resize(rgb_c, (448, 448))
    try:
        img_torch = scale_torch(A_resize)[None, :, :, :]
        pred_depth = depth_model.inference(img_torch).cpu().numpy().squeeze()
        pred_depth_ori = cv2.resize(pred_depth, (img.shape[1], img.shape[0]))
        pred_depth_ori = pred_depth_ori/np.max(pred_depth_ori) * 255

        _, pred_depth_jpg = cv2.imencode('.JPG', pred_depth_ori)

        # convert output image to base64
        depthgraphic = base64.b64encode(pred_depth_jpg).decode("utf-8")
        jsondepth = "data:image/jpeg;base64," + depthgraphic
        depth = {"depth-map": jsondepth, "scaling": 0}
    except Exception as e:
        logging.error("Depth model inference error")
        logging.pii(f"Inference error: {e}")
        return jsonify("Depth Model cannot complete"), 500

    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(depth)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for depth data")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": depth
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for final response")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    torch.cuda.empty_cache()
    logging.debug("Sending response")
    return response


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint to verify if the service is running
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/warmup", methods=["GET"])
def warmup():
    try:
        logging.pii("[WARMUP] Initializing RelDepthModel with resnext101 \
                    and loading weights from /app/res101.pth")
        model = RelDepthModel(backbone='resnext101').eval().cuda()
        model.load_state_dict(
            strip_prefix_if_present(
                torch.load("/app/res101.pth")['depth_model'], "module."),
            strict=True
        )

        # simulating a single RGB image input to the model
        # 1: one image; 3: RGB; 448 and 448: height and width
        dummy = torch.ones((1, 3, 448, 448), dtype=torch.float32).cuda()
        _ = model.inference(dummy)
        return jsonify({"status": "warmed"}), 200

    except Exception as e:
        logging.error("Warmup failed")
        logging.pii(f"Warmup error: {e}")
        return jsonify({"status": "warmup failed"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    depthgenerator()
