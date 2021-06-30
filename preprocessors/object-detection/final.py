from flask import Flask, jsonify, request
from flask_api import status
import json
import time
from torchvision import transforms as T
import torchvision
import jsonschema
import numpy as np
import base64
import cv2
import logging

app = Flask(__name__)
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
model.eval()

# The N/A jare just used to inrease the size of the array. Since I am
# running a pretrained model right now, the output array size is fixed for
# the model. Hence the label array(pred_class) has to match the output prediction(pred)
# array and hence the NA are used to make the size of both arrays same.
# This would change in future as i will not used a pretrained model and
# make a custom model. The N/A would not exist and the model would be custom made.


COCO_INSTANCE_CATEGORY_NAMES = [
    '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
    'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
    'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
    'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
    'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
    'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table',
    'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book',
    'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]


def get_prediction(img, threshold):
    transform = T.Compose([T.ToTensor()])
    img = transform(img)
    pred = model([img])
    pred_class = [COCO_INSTANCE_CATEGORY_NAMES[i]
                  for i in list(pred[0]['labels'].numpy())]
    pred_boxes = [[(i[0], i[1]), (i[2], i[3])]
                  for i in list(pred[0]['boxes'].detach().numpy())]
    pred_score = list(pred[0]['scores'].detach().numpy())
    pred_t = [pred_score.index(x) for x in pred_score if x > threshold][-1]
    pred_boxes = pred_boxes[:pred_t + 1]
    pred_class = pred_class[:pred_t + 1]
    return pred_boxes, pred_class, pred_score


@app.route("/preprocessor", methods=['POST', 'GET'])
def readImage():
    if request.method == 'POST':
        pred = []
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
        request_uuid = content["request_uuid"]
        timestamp = time.time()
        name = "ca.mcgill.a11y.image.preprocessor.objectDetection"
        url = content["image"]
        image_b64 = url.split(",")[1]
        binary = base64.b64decode(image_b64)
        image = np.asarray(bytearray(binary), dtype="uint8")
        im = cv2.imdecode(image, cv2.IMREAD_COLOR)
        boxes, pred_cls, score = get_prediction(im, 0.5)
        for i in range(len(boxes)):
            xmin = int(boxes[i][0][0])
            ymin = int(boxes[i][0][1])
            xmax = int(boxes[i][1][0])
            ymax = int(boxes[i][1][1])
            boxes[i][0] = (xmin, ymin)
            boxes[i][1] = (xmax, ymax)
            dimen = [xmin, ymin, xmax, ymax]
        for i in range(len(pred_cls)):
            dictionary = {
                "ID": i, "type": str(pred_cls[i]), "dimensions": dimen, "confidence": np.float64(score[i] * 100)
            }
            pred.append(dictionary)
        things = {"objects": pred}
        response = {
            "request_uuid": request_uuid,
            "timestamp": int(timestamp),
            "name": name,
            "data": things}
        try:
            validator = jsonschema.Draft7Validator(schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        return response
    return "<h1>Get Request found. Try to send a POST request to get a response</h1>"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
