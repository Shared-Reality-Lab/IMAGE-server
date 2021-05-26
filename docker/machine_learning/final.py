from flask import Flask, jsonify, request
from flask_api import status
import json
import  time
from torchvision import transforms as T
import torchvision
import jsonschema
import numpy as np
import base64
import cv2

app = Flask(__name__)
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
model.eval()

COCO_INSTANCE_CATEGORY_NAMES = ['__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table', 'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush']

def get_prediction(img, threshold):
    transform = T.Compose([T.ToTensor()])
    img = transform(img)
    pred = model([img])
    pred_class = [COCO_INSTANCE_CATEGORY_NAMES[i] for i in list(pred[0]['labels'].numpy())]
    pred_boxes = [[(i[0], i[1]), (i[2], i[3])] for i in list(pred[0]['boxes'].detach().numpy())]
    pred_score = list(pred[0]['scores'].detach().numpy())
    pred_t = [pred_score.index(x) for x in pred_score if x>threshold][-1]
    pred_boxes = pred_boxes[:pred_t+1]
    pred_class = pred_class[:pred_t+1]
    return pred_boxes, pred_class

@app.route("/atp/preprocessor",methods = ['POST','GET'])
def readImage():
    if request.method == 'POST':
        pred = []
        data = []
        with open('./schemas/preprocessor-response.schema.json') as jsonfile:
            schema = json.load(jsonfile)
        with open('./schemas/definitions.json') as jsonfile:
            definitionSchema = json.load(jsonfile)
        schema_store={
            schema['$id'] : schema,
            definitionSchema['$id'] : definitionSchema
        }
        resolver = jsonschema.RefResolver.from_schema(schema, store=schema_store)
        
        content = request.get_json()
        request_uuid = content["request_uuid"]
        timestamp = time.time()
        name = "ca.mcgill.cim.bach.atp.objectDetection.preprocessor"
        url  =content["image"]
        image_b64 = url.split(",")[1]
        binary = base64.b64decode(image_b64)
        image = np.asarray(bytearray(binary), dtype="uint8")
        im = cv2.imdecode(image, cv2.IMREAD_COLOR)
        boxes, pred_cls = get_prediction(im, 0.5)
        for i in range(len(pred_cls)):
            dictionary = {"name:":str(pred_cls[i]),"box_points:":str(boxes[i])}
            pred.append(dictionary)
        things = {"objects":pred}
        response = jsonify({"request_uuid":request_uuid,"timestamp":timestamp,"name":name,"data":things})
        try:
            jsonschema.Draft7Validator(response, resolver=resolver)
        except jsonschema.exceptions.ValidationError as e:
            return "Invalid JSON format",status.HTTP_500_BAD_REQUEST
        return response
    return "<h1>Get Request found. Try to send a POST request to get a response</h1>"




if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000)
