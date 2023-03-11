import cv2
import argparse
import numpy as np
import torch
import torchvision.transforms as transforms
import sys
from flask import Flask, request, jsonify
from collections import OrderedDict
import json
import time
import jsonschema
import logging
import base64

sys.path.append('./AdelaiDepth/LeReS/Minist_Test/')

from lib.multi_depth_model_woauxi import RelDepthModel

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
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 400
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
    checkpoint = torch.load("/app/res101.pth")
    depth_model.load_state_dict(strip_prefix_if_present(
                                checkpoint['depth_model'], "module."),
                                strict=True)
    del checkpoint
    torch.cuda.empty_cache()

    depth_model.cuda()

    rgb_c = img[:, :, ::-1].copy()
    A_resize = cv2.resize(rgb_c, (448, 448))

    img_torch = scale_torch(A_resize)[None, :, :, :]
    pred_depth = depth_model.inference(img_torch).cpu().numpy().squeeze()
    pred_depth_ori = cv2.resize(pred_depth, (img.shape[1], img.shape[0]))
    pred_depth_ori = pred_depth_ori/np.max(pred_depth_ori)

    _, pred_depth_jpg = cv2.imencode('.JPG', pred_depth_ori)

    # convert output image to base64
    depthgraphic = base64.b64encode(pred_depth_jpg).decode("utf-8")
    jsondepth = "data:image/jpeg;base64," + depthgraphic
    depth = {"depth-map": jsondepth, "scaling": 0}

    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(depth)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
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
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    torch.cuda.empty_cache()
    logging.debug("Sending response")
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    depthgenerator()
