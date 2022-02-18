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
# <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.
#
# This was adapted from CSAIL's Semantic Segmentation library at
# <https://github.com/CSAILVision/semantic-segmentation-pytorch>
# Lines 99-102 are refered form
# https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47

import csv
import torch
import numpy
import scipy.io
import torchvision.transforms
from flask import Flask, request, jsonify
import json
import time
import jsonschema
import logging
import base64
import cv2
import numpy as np
from mit_semseg.models import ModelBuilder, SegmentationModule
from mit_semseg.utils import colorEncode
import gc


app = Flask(__name__)

# assigns different colors to different segments. This helps in
# determining contour or different segments. Refer Line 136 to see how
# unique color helps in contour determination
colors = scipy.io.loadmat('data/color150.mat')['colors']
names = {}
with open('data/object150_info.csv') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        names[int(row[0])] = row[5].split(";")[0]


# Removes the remaining segments and only highlights the segment of
# interest with a particular color.
def visualize_result(img, pred, index=None):
    if index is not None:
        pred = pred.copy()
        pred[pred != index] = -1
    pred_color = colorEncode(pred, colors).astype(numpy.uint8)
    nameofobj = names[index + 1]
    return pred_color, nameofobj

# takes the colored segment(determined in visualise_reslt function and
# compressed the segment to 100 pixels


def findContour(pred_color, width, height):
    image = pred_color
    dummy = pred_color.copy()
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(gray_image, 10, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(image, contours, -1, (0, 255, 0), 2)
    image = image - dummy
    centres = []
    area = []
    totArea = 0
    send_contour = []
    flag = False
    for i in range(len(contours)):
        moments = cv2.moments(contours[i])
        if moments['m00'] == 0:
            continue
        # if contour area for a given class is very small then omit that
        if cv2.contourArea(contours[i]) < 2000:
            continue
        totArea = totArea + cv2.contourArea(contours[i])
        area.append(cv2.contourArea(contours[i]))
        centres.append(
            (int(moments['m10'] / moments['m00']),
             int(moments['m01'] / moments['m00'])))
        area_indi = cv2.contourArea(contours[i])
        centre_indi = (int(moments['m10'] / moments['m00']),
                       int(moments['m01'] / moments['m00']))
        contour_indi = [list(x) for x in contours[i]]
        contour_indi = np.squeeze(contour_indi)
        centre_down = [centre_indi[0] / width, centre_indi[1] / height]
        area_down = area_indi / (width * height)
        contour_indi = contour_indi.tolist()
        for j in range(len(contour_indi)):
            contour_indi[j][0] = float(float(contour_indi[j][0]) / width)
            contour_indi[j][1] = float(float(contour_indi[j][1]) / height)
        send_contour.append({"coordinates": contour_indi,
                            "centroid": centre_down, "area": area_down})
    if not area:
        flag = True
    else:
        max_value = max(area)
    if(flag is True):
        return ([0, 0], [0, 0], 0)
    centre1 = centres[area.index(max_value)][0] / width
    centre2 = centres[area.index(max_value)][1] / height
    centre = [centre1, centre2]
    totArea = totArea / (width * height)
    result = np.concatenate(contours, dtype=np.float32)
    if(totArea < 0.05):
        return ([0, 0], [0, 0], 0)
    result = np.squeeze(result)
    result = np.swapaxes(result, 0, 1)
    result[0] = result[0] / float(width)
    result[1] = result[1] / float(height)
#    send = np.swapaxes(result, 0, 1).tolist()
    return send_contour, centre, totArea


def run_segmentation(url,
                     segmentation_module,
                     dictionary,
                     pil_to_tensor):
    # Following 4 lines refered from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    image_b64 = url.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    pil_image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    height, width, channels = pil_image.shape
    scale_size = np.float(1500.0 / np.float(max(height, width)))
    if(scale_size <= 1.0):
        height = np.int(height * scale_size)
        width = np.int(width * scale_size)
        pil_image = cv2.resize(pil_image, (width, height),
                               interpolation=cv2.INTER_AREA)
    img = pil_image
    img_original = numpy.array(img)
    img_data = pil_to_tensor(img)
    try:
        img_data = img_data.cuda()
    except RuntimeError as e:
        if 'out of memory' in str(e):
            print("OOM detected")
            torch.cuda.empty_cache()
            return jsonify("OOM detected"), 500
    singleton_batch = {'img_data': img_data[None]}
    output_size = img_data.shape[1:]
    with torch.no_grad():
        scores = segmentation_module(singleton_batch,
                                     segSize=output_size)
    _, pred = torch.max(scores, dim=1)
    pred = pred.cpu()[0].numpy()
    color, name = visualize_result(img_original, pred, 0)
    predicted_classes = numpy.bincount(pred.flatten()).argsort()[::-1]
    for c in predicted_classes[:5]:
        color, name = visualize_result(img_original, pred, c)
        send, center, area = findContour(color, width, height)
        if(area == 0):
            continue
        dictionary.append(
            {"name": name, "contours": send,
             "centroid": center, "area": area})
    return {"segments": dictionary}


@app.route("/preprocessor", methods=['POST', 'GET'])
def segment():
    logging.debug("Received request")
    gc.collect()
    torch.cuda.empty_cache()
    dictionary = []
    with open('./schemas/preprocessors/segmentation.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    # Following 6 lines refered from
    # https://stackoverflow.com/questions/42159346/jsonschema-refresolver-to-resolve-multiple-refs-in-python
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
    net_encoder = ModelBuilder.build_encoder(
        arch='resnet50dilated',
        fc_dim=2048,
        weights='encoder_epoch_20.pth')
    net_decoder = ModelBuilder.build_decoder(
        arch='ppm_deepsup',
        fc_dim=2048,
        num_class=150,
        weights='decoder_epoch_20.pth',
        use_softmax=True)
    crit = torch.nn.NLLLoss(ignore_index=-1)
    segmentation_module = SegmentationModule(net_encoder, net_decoder, crit)
    segmentation_module.eval()
    try:
        segmentation_module.cuda()
    except RuntimeError as e:
        if 'out of memory' in str(e):
            print("OOM detected")
            torch.cuda.empty_cache()
            return jsonify("OOM detected"), 500
    pil_to_tensor = torchvision.transforms.Compose([
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225])
    ])
    content = request.get_json()
    try:
        validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 400
    if "graphic" not in content:
        logging.info("Not image content. Skipping...")
        return "", 204
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    preprocessorName = \
        "ca.mcgill.a11y.image.preprocessor.semanticSegmentation"
    classifier_1 = "ca.mcgill.a11y.image.preprocessor.firstCategoriser"
    classifier_2 = "ca.mcgill.a11y.image.preprocessor.secondCategoriser"
    preprocess_output = content["preprocessors"]
    if classifier_1 in preprocess_output:
        classifier_1_output = preprocess_output[classifier_1]
        classifier_1_label = classifier_1_output["category"]
        if classifier_1_label != "photograph":
            logging.info("Not photograph content. Skipping...")

            return "", 204
        if classifier_2 in preprocess_output:
            # classifier_2_output = preprocess_output[classifier_2]
            # classifier_2_label = classifier_2_output["category"]
            # if classifier_2_label != "outdoor":
            #     logging.info("Cannot process image")
            #     return "", 204
            segment = run_segmentation(content["graphic"],
                                       segmentation_module,
                                       dictionary,
                                       pil_to_tensor)
        else:
            """We are providing the user the ability to process an image
            even when the second classifier is absent, however it is
            recommended to the run the semantic segmentation
            model in conjunction with the second classifier."""
            segment = run_segmentation(content["graphic"],
                                       segmentation_module,
                                       dictionary,
                                       pil_to_tensor)
    else:
        """We are providing the user the ability to process an image
        even when the first classifier is absent, however it is
        recommended to the run the semantic segmentation
        model in conjunction with the first classifier."""
        segment = run_segmentation(content["graphic"],
                                   segmentation_module,
                                   dictionary,
                                   pil_to_tensor)
    torch.cuda.empty_cache()
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(segment)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": preprocessorName,
        "data": segment
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500

    logging.debug("Sending response")
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
