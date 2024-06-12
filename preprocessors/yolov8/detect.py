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

from ultralytics.nn.tasks import attempt_load_weights
from ultralytics.yolo.utils import plt_settings
from ultralytics.yolo.utils.torch_utils import select_device
from ultralytics.yolo.utils.checks import check_imgsz
from ultralytics.yolo.utils.ops import scale_coords, non_max_suppression

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
app = Flask(__name__)

c_thres = 0.75


def load_image(path, img_size=640, stride=32):
    image_b64 = path.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    img0 = cv2.imdecode(image, cv2.IMREAD_COLOR)
    assert img0 is not None, 'Image Not Found ' + path

    # Padded resize
    img = letterbox(img0, img_size, stride=stride)[0]

    # Convert
    img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB and HWC to CHW
    img = np.ascontiguousarray(img)

    return path, img, img0


def letterbox(
        img,
        new_shape=(
            640,
            640),
        color=(
            114,
            114,
            114),
        auto=True,
        scaleFill=False,
        scaleup=True,
        stride=32):
    # Resize and pad image while meeting stride-multiple constraints
    shape = img.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # only scale down, do not scale up (for better test mAP)
        r = min(r, 1.0)

    # Compute padding
    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - \
        new_unpad[1]  # wh padding
    if auto:  # minimum rectangle
        dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
    elif scaleFill:  # stretch
        dw, dh = 0.0, 0.0
        new_unpad = (new_shape[1], new_shape[0])
        ratio = new_shape[1] / shape[1], new_shape[0] / \
            shape[0]  # width, height ratios

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(
        img,
        top,
        bottom,
        left,
        right,
        cv2.BORDER_CONSTANT,
        value=color)  # add border
    return img, ratio, (dw, dh)


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
    model = attempt_load_weights(weights, device=device)
    stride = int(model.stride.max())
    # may need to change min_dim, max_dim
    imgsz = check_imgsz(imgsz, stride=stride)
    names = model.module.names if hasattr(model, 'module') else model.names
    if half:
        model.half()
    # generate the predictions
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(
            device).type_as(next(model.parameters())))

    path, img, im0s = load_image(source, img_size=imgsz, stride=stride)
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
    # once the predictions are generated convert
    # the image to original size.
    for i, det in enumerate(pred):
        p, s, im0 = path, '', im0s.copy()
        p = Path(p)
        s += '%gx%g ' % img.shape[2:]
        if len(det):
            coords = torch.reshape(det[:, :4], (det.size()[0], 2, 2))
            det[:, :4] = scale_coords(
                img.shape[2:], coords, im0.shape, normalize=True
                ).flatten(1, -1).clone()
            for c in det[:, -1].unique():
                n = (det[:, -1] == c).sum()
                s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "
            i = 0
            # create a json output and validate the json
            for *xyxy, conf, cls in reversed(det):
                xyxy = torch.tensor(xyxy).tolist()
                if save_img or save_crop or view_img:
                    c = int(cls)
                    label = None if hide_labels else (
                        names[c] if hide_conf else
                        f'{names[c]} {conf:.2f}'
                    )
                    centre = [abs((xyxy[0] + xyxy[2]) / 2),
                              abs((xyxy[1] + xyxy[3]) / 2)]
                    area = abs(xyxy[0] - xyxy[1]) * abs(xyxy[1] - xyxy[3])
                    dictionary = {
                        "ID": i,
                        "type": str(label[:-4]),
                        "dimensions": xyxy,
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
def run(weights='yolov8x.pt',
        source='data/images',
        imgsz=640,
        conf_thres=c_thres,
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
    plt_settings()
    device = select_device(device, verbose=False)
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
        logging.debug("Object detection Response")
        logging.debug(response)
        return response


def main():
    run()


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    main()
