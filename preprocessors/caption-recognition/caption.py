import torch
from PIL import Image
import requests
from flask import Flask, request, jsonify
from lavis.models import load_model_and_preprocess
import base64
import cv2
import logging
import numpy as np
import time
import json
import jsonschema


device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

logging.basicConfig(level=logging.NOTSET)
app = Flask(__name__)

@app.route("/preprocessor", methods=['POST', 'GET'])

def captions():
    content = request.get_json()
    with open('./schemas/preprocessors/caption.schema.json') \
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
    image = content["graphic"]
    image_b64 = image.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    pil_image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(pil_image, cv2.COLOR_BGR2RGB)
    pil_img =  Image.fromarray(img)
    model, vis_processors, _ = load_model_and_preprocess(name="blip_caption", model_type="base_coco", is_eval=True, device=device)
    image = vis_processors["eval"](pil_img).unsqueeze(0).to(device)
    image = vis_processors["eval"](pil_img).unsqueeze(0).to(device)
    # generate caption
    caption = model.generate({"image": image})
    data = {"caption":caption[0]}
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.caption"
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": data
    }

    try:
        validator = jsonschema.Draft7Validator(
            schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    logging.debug(data)
    return jsonify(caption)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)