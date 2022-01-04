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
# <https://github.com/Shared-Reality-Lab/auditory-haptic-graphics-server/LICENSE>.
#
# This was adapted from CSAIL's Places365 project
# <https://github.com/CSAILVision/places365>
# by Bolei Zhou, sep 2, 2017

import torch
from torch.autograd import Variable as V
from torchvision import transforms as trn
from torch.nn import functional as F
import numpy as np
import cv2
from PIL import Image
from flask import Flask, jsonify, request
from urllib.request import urlopen
from io import BytesIO
import time
import jsonschema
import logging
import json
import wideresnet


app = Flask(__name__)


def recursion_change_bn(module):
    if isinstance(module, torch.nn.BatchNorm2d):
        module.track_running_stats = 1
    else:
        for i, (name, module1) in enumerate(module._modules.items()):
            module1 = recursion_change_bn(module1)
    return module


def load_labels():
    file_name_category = 'categories_places365.txt'
    classes = list()
    with open(file_name_category) as class_file:
        for line in class_file:
            classes.append(line.strip().split(' ')[0][3:])
    classes = tuple(classes)
    file_name_IO = 'IO_places365.txt'
    with open(file_name_IO) as f:
        lines = f.readlines()
        labels_IO = []
        for line in lines:
            items = line.rstrip().split()
            labels_IO.append(int(items[-1]) - 1)
    labels_IO = np.array(labels_IO)
    file_name_attribute = 'labels_sunattribute.txt'
    with open(file_name_attribute) as f:
        lines = f.readlines()
        labels_attribute = [item.rstrip() for item in lines]
    file_name_W = 'W_sceneattribute_wideresnet18.npy'
    W_attribute = np.load(file_name_W)
    return classes, labels_IO, labels_attribute, W_attribute


def hook_feature(module, input, output):
    features_blobs.append(np.squeeze(output.data.cpu().numpy()))


def returnCAM(feature_conv, weight_softmax, class_idx):
    size_upsample = (256, 256)
    nc, h, w = feature_conv.shape
    output_cam = []
    for idx in class_idx:
        cam = weight_softmax[class_idx].dot(feature_conv.reshape((nc, h * w)))
        cam = cam.reshape(h, w)
        cam = cam - np.min(cam)
        cam_img = cam / np.max(cam)
        cam_img = np.uint8(255 * cam_img)
        output_cam.append(cv2.resize(cam_img, size_upsample))
    return output_cam


def returnTF():
    tf = trn.Compose([
        trn.Resize((224, 224)),
        trn.ToTensor(),
        trn.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    return tf


def load_model():
    model_file = 'wideresnet18_places365.pth.tar'
    model = wideresnet.resnet18(num_classes=365)
    checkpoint = torch.load(
        model_file,
        map_location=lambda storage,
        loc: storage)
    state_dict = {
        str.replace(
            k,
            'module.',
            ''): v for k,
        v in checkpoint['state_dict'].items()}
    model.load_state_dict(state_dict)
    for i, (name, module) in enumerate(model._modules.items()):
        module = recursion_change_bn(model) # noqa
    model.avgpool = torch.nn.AvgPool2d(kernel_size=14, stride=1, padding=0)
    model.eval()
    model.eval()
    features_names = ['layer4', 'avgpool']
    for name in features_names:
        model._modules.get(name).register_forward_hook(hook_feature)
    return model


classes, labels_IO, labels_attribute, W_attribute = load_labels()
features_blobs = []
model = load_model()
tf = returnTF()
params = list(model.parameters())
weight_softmax = params[-2].data.numpy()
weight_softmax[weight_softmax < 0] = 0


@app.route("/preprocessor", methods=['POST', 'GET'])
def scenePredictor():
    pred = []
    attributes = []
    with open('./schemas/preprocessors/scene-detection.schema.json') \
            as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
    content = request.get_json()
    if "image" not in content:
        logging.info("Not image content! Skipping...")
        return "", 204
    img_url = content["image"]
    with urlopen(img_url) as response:
        data = response.read()
    stream = BytesIO(data)
    image = Image.open(stream).convert("RGB")
    stream.close()
    input_img = V(tf(image).unsqueeze(0))
    logit = model.forward(input_img)
    h_x = F.softmax(logit, 1).data.squeeze()
    probs, idx = h_x.sort(0, True)
    probs = probs.numpy()
    idx = idx.numpy()
    io_image = np.mean(labels_IO[idx[:10]])
    # randomly selected thresholding parameter which was created
    # by the owners of this model. On testing it was concluded that
    # 0.5 works the best for indoor outdoor segregation
    if io_image < 0.5:
        type = "indoor"
    else:
        type = "outdoor"
    # taking the first five predictions
    for i in range(0, 5):
        dictionary = {"name": classes[idx[i]],
                      "confidence": int(probs[i] * 100)}
    pred.append(dictionary)
    responses_attribute = W_attribute.dot(features_blobs[1])
    idx_a = np.argsort(responses_attribute)
    for i in range(-1, -10, -1):
        attributes.append(labels_attribute[idx_a[i]])
    timestamp = time.time()
    request_uuid = content["request_uuid"]
    name = "ca.mcgill.a11y.image.preprocessor.sceneRecognition"
    data = {
        "type": type,
        "categories": pred,
        "attributes": attributes
    }
    try:
        validator = jsonschema.Draft7Validator(data_schema, resolver=resolver)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": data
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
