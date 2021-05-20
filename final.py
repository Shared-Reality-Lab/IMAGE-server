
    
from flask import Flask,jsonify,redirect, url_for, request,make_response
import urllib
#from flask_ngrok import run_with_ngrok
app = Flask(__name__)
import os
#from imageai.Detection import ObjectDetection
import torchvision.models as models
import json
import io
from PIL import Image
import requests
import os
import torch
from torchvision import models

import os, sys, time, datetime, random
import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torch.autograd import Variable
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import math
import time

#run_with_ngrok(app)
pred = []
execution_path = os.getcwd()



import torchvision
from torchvision import datasets, transforms as T 
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True) 
model.eval()

COCO_INSTANCE_CATEGORY_NAMES = ['__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table', 'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush']
data = []

@app.route("/",methods = ['POST','GET'])
def home():
    def get_prediction(img_path, threshold):
        img = Image.open(img_path)
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
    #for file in os.listdir(r"C:\Users\91966\Desktop\Assignments\labWork\test-images"):
    if request.method == 'POST':
        content = request.get_json()
        request_uuid = content["request_uuid"]
        timestamp = time.time()
        name = "ca.mcgill.cim.bach.atp.first.preprocessor"
        print(content["URL"],time)
        url  = content["URL"]
        resource = urllib.request.urlopen(url)
        with open("test.jpg", "wb") as f:
            f.write(resource.read())
        #output.close()
        print(os.path.abspath("test.jpg"))
        path = os.path.abspath("test.jpg")
        #detected_image_array, detections = detector.detectObjectsFromImage(  input_image=path,output_type="array")
        boxes, pred_cls = get_prediction(path, 0.5)
        for i in range(len(pred_cls)):
            dictionary = {"name:":str(pred_cls[i]),"box_points:":str(boxes[i])}
            pred.append(dictionary)
        things = {"objects":pred}
        pred1 = json.dumps(pred)
        print(type(pred))
        response = jsonify({"request_uuid":request_uuid,"timestamp":timestamp,"name":name,"data":things})
#        with open( "test.json","w") as f:
#            json.dump({"request_uuid":request_uuid,"timestamp":timestamp,"name":name,"data":things},f,indent=2)
        return response
        return "<h1>Hello here</h1>"
      #user = request.form['nm']
    return "<h1>Hello </h1>"




    
app.run(host='0.0.0.0',port=5000, debug = True)
