import torch
from torch import nn
import pytorch_lightning as pl
from torchvision import models
import numpy as np
from pathlib import Path
import cv2
from flask import Flask, request, jsonify
import json
import time
import jsonschema
import logging
import base64
import os

app = Flask(__name__)


class Net(pl.LightningModule):
    # initial initialisation if architecture. It  is needed to load the weights
    def __init__(self, num_classes=10, lr=1e-3):
        super().__init__()
        self.save_hyperparameters()
        self.model = models.densenet121(pretrained=True)
        for param in self.model.parameters():
            param.requires_grad = False
        self.model.classifier = nn.Linear(self.model.classifier.in_features, 4)

    # the main loop used for prediction.
    def forward(self, x):
        logits = self.model(x)
        preds = torch.argmax(logits, 1)
        pred_int = preds.int()
        pred_int = pred_int.detach().numpy()
        return str(pred_int[0])


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    # load the schema
    labels_dict = {"0": "chart", "1": "image", "2": "other", "3": "text"}
    with open('./schemas/preprocessors/categoriser.json') as jsonfile:
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
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.firstCategoriser"

    # convert the uri to processable image
    source = content["image"]
    image_b64 = source.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)

    # download the weights and test the input image. The input image passed to
    # the "forward" function to get the predictions.
    net = Net.load_from_checkpoint('./latest-0.ckpt')
    img = cv2.resize(img, (224, 224))
    image = img.reshape(1, 3, 224, 224)
    inputs = torch.FloatTensor(image)
    net.eval()
    pred = net(inputs)
    type = {"category": labels_dict[pred]}
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(type)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": type
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    torch.cuda.empty_cache()
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    categorise()
