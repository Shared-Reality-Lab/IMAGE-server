# YOLOv5 🚀 by Ultralytics, GPL-3.0 license
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
from pathlib import Path
from flask import Flask, jsonify, request
import cv2
import torch
import base64
import numpy as np
import jsonschema
import json
import logging
import os

from models.experimental import attempt_load
from datasetsChanged import LoadImages
from utils.general import check_img_size, non_max_suppression, \
    apply_classifier, scale_coords, set_logging
from utils.torch_utils import select_device, load_classifier


os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
app = Flask(__name__)


def detect_objects(send,
                   device,
                   weights,
                   imgsz,
                   half,
                   source,
                   augment,
                   width,
                   height,
                   conf_thres,
                   iou_thres,
                   classes,
                   agnostic_nms,
                   save_img,
                   save_crop,
                   view_img,
                   hide_labels,
                   hide_conf):
    model = attempt_load(weights, map_location=device)
    stride = int(model.stride.max())
    imgsz = check_img_size(imgsz, s=stride)
    names = model.module.names if hasattr(model, 'module') else model.names
    if half:
        model.half()
    classify = False
    if classify:
        modelc = load_classifier(name='resnet50', n=2)
        modelc.load_state_dict(
            torch.load(
                'resnet50.pt',
                map_location=device
            )['model']
        ).to(device).eval()
    # load images by converting them from base64 to readable format
    dataset = LoadImages(source, img_size=imgsz, stride=stride)
    # generate the predictions
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(
            device).type_as(next(model.parameters())))
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()
        img /= 255.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        # get predictions for the model
        pred = model(img, augment=augment)[0]
        # , max_det=max_det)
        pred = non_max_suppression(
            pred, conf_thres, iou_thres, classes, agnostic_nms)
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)
        # once the predictions are generated convert
        # the image to original size.
        for i, det in enumerate(pred):
            p, s, im0 = path, '', im0s.copy()
            p = Path(p)
            s += '%gx%g ' % img.shape[2:]
            if len(det):
                det[:, :4] = scale_coords(
                    img.shape[2:], det[:, :4], im0.shape).round()
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "
                i = 0
                # create a json output and validate the json
                for *xyxy, conf, cls in reversed(det):
                    if save_img or save_crop or view_img:
                        c = int(cls)
                        label = None if hide_labels else (
                            names[c] if hide_conf else
                            f'{names[c]} {conf:.2f}'
                        )
                        # normalise the image
                        xleft = int(xyxy[0]) / width
                        yleft = int(xyxy[1]) / height
                        xright = int(xyxy[2]) / width
                        yright = int(xyxy[3]) / height
                        centre = [abs((xleft + xright) / 2),
                                  abs((yleft + yright) / 2)]
                        area = abs(xleft - xright) * abs(yleft - yright)
                        dictionary = {
                            "ID": i,
                            "type": str(label[:-4]),
                            "dimensions": [xleft, yleft, xright, yright],
                            "confidence": np.float64(label[-4:]),
                            "centroid": centre, "area": area
                        }
                        send.append(dictionary)
                        """"plot_one_box(xyxy, im0, label=label,
                        color=colors(c, True),
                        line_thickness=line_thickness) # noqa"""
                        i = i + 1
            things = {"objects": send}
            return things


@torch.no_grad()
@app.route("/preprocessor", methods=['POST', 'GET'])
# The parameters in run function were generated by the author of the code.
# Do not interfere with this as this breaks the code in some other file
def run(weights='yolov5x.pt',
        source='data/images',
        imgsz=640,
        conf_thres=0.25,
        iou_thres=0.45,
        max_det=1000,
        device='',
        view_img=False,
        save_crop=False,
        nosave=False,
        classes=None,
        agnostic_nms=False,
        augment=False,
        update=False,
        name='exp',
        line_thickness=3,
        hide_labels=False,
        hide_conf=False,
        half=False,
        ):
    logging.debug("Received request")
    save_img = not nosave and not source.endswith('.txt')
    set_logging()
    device = select_device(device)
    send = []
    half &= device.type != 'cpu'

    # Accept the input and load the schemas
    if request.method == 'POST':
        with open('./schemas/preprocessors/object-detection.schema.json') \
                as jsonfile:
            data_schema = json.load(jsonfile)
        with open('./schemas/preprocessor-response.schema.json') \
                as jsonfile:
            schema = json.load(jsonfile)
        with open('./schemas/definitions.json') as jsonfile:
            definitionSchema = json.load(jsonfile)
        with open('./schemas/request.schema.json') as jsonfile:
            first_schema = json.load(jsonfile)
        # Following 6 lines of code are referred from
        # https://stackoverflow.com/questions/42159346/jsonschema-refresolver-to-resolve-multiple-refs-in-python
        schema_store = {
            schema['$id']: schema,
            definitionSchema['$id']: definitionSchema
        }
        resolver = jsonschema.RefResolver.from_schema(
            schema, store=schema_store)
        content = request.get_json()
        try:
            validator = jsonschema.Draft7Validator(
                first_schema, resolver=resolver)
            validator.validate(content)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 400
        if "graphic" not in content:
            logging.info("No image content. Skipping...")
            return "", 204
        preprocess_output = content["preprocessors"]
        request_uuid = content["request_uuid"]
        timestamp = time.time()
        name = "ca.mcgill.a11y.image.preprocessor.objectDetection"
        # Following 4 lines are refered from
        # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
        source = content["graphic"]
        image_b64 = source.split(",")[1]
        binary = base64.b64decode(image_b64)
        image = np.asarray(bytearray(binary), dtype="uint8")
        imgDim = cv2.imdecode(image, cv2.IMREAD_COLOR)
        height, width, channels = imgDim.shape
        classifier_1 = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
        classifier_2 = "ca.mcgill.a11y.image.preprocessor.graphicTagger"
        if classifier_1 in preprocess_output:
            classifier_1_output = preprocess_output[classifier_1]
            classifier_1_label = classifier_1_output["category"]
            if classifier_1_label != "photograph":
                logging.info("Not image content. Skipping...")
                return "", 204
            if classifier_2 in preprocess_output:
                # classifier_2_output = preprocess_output[classifier_2]
                # classifier_2_label = classifier_2_output["category"]
                # if classifier_2_label == "other":
                #     logging.info("Cannot process image")
                #     return "", 204
                things = detect_objects(send,
                                        device,
                                        weights,
                                        imgsz,
                                        half,
                                        source,
                                        augment,
                                        width,
                                        height,
                                        conf_thres,
                                        iou_thres,
                                        classes,
                                        agnostic_nms,
                                        save_img,
                                        save_crop,
                                        view_img,
                                        hide_labels,
                                        hide_conf)
            else:
                """We are providing the user the ability to process an image
                even when the second classifier is absent, however it is
                recommended to the run objection detection model
                in conjunction with the second classifier."""
                things = detect_objects(send,
                                        device,
                                        weights,
                                        imgsz,
                                        half,
                                        source,
                                        augment,
                                        width,
                                        height,
                                        conf_thres,
                                        iou_thres,
                                        classes,
                                        agnostic_nms,
                                        save_img,
                                        save_crop,
                                        view_img,
                                        hide_labels,
                                        hide_conf)
        else:
            """We are providing the user the ability to process an image
            even when the first classifier is absent, however it is
            recommended to the run objection detection model
            in conjunction with the first classifier."""
            things = detect_objects(send,
                                    device,
                                    weights,
                                    imgsz,
                                    half,
                                    source,
                                    augment,
                                    width,
                                    height,
                                    conf_thres,
                                    iou_thres,
                                    classes,
                                    agnostic_nms,
                                    save_img,
                                    save_crop,
                                    view_img,
                                    hide_labels,
                                    hide_conf)
        try:
            validator = jsonschema.Draft7Validator(data_schema)
            validator.validate(things)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": name,
            "data": things
        }
        try:
            validator = jsonschema.Draft7Validator(
                schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response


def main():
    run()


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    main()
