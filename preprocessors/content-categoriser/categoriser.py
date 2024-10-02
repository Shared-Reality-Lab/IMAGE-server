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
import torch
from torch import nn
import pytorch_lightning as pl
from torchvision import models
import numpy as np
import cv2
from flask import Flask, request, jsonify
import json
import time
import jsonschema
import logging
import base64

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


class Net(pl.LightningModule):
    # initial initialisation if architecture. It  is needed to load the weights
    def __init__(self, num_classes=10, lr=1e-4):
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
    logging.debug("Received request")
    # load the schema
    labels_dict = {"0": "chart", "1": "photograph", "2": "other", "3": "text"}
    with open('./schemas/preprocessors/content-categoriser.schema.json') \
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
    name = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"

    # convert the uri to processable image
    # Following 4 lines of code
    # refered form
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = content["graphic"]
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
    logging.debug(type)
    return response


@app.route('/health', methods=['GET'])
def health():
    """
    health check endpoint to verify if the service is up.
    """
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    categorise()
