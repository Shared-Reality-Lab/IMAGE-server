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
# import torch
# from torch import nn
# import pytorch_lightning as pl
# from torchvision import models
from flask import Flask, request, jsonify
import requests
import re
import json
import time
import jsonschema
import logging
import base64

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    logging.debug("Received request")
    # load the schema
    labels_dict = {"0": "photograph", "1": "chart", "2": "other", "3": "text"}
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
    binary_img = binary.decode('utf-8')

    logging.debug("Running LLaVa 7b")

    import os
    api_url = "https://ollama.unicorn.cim.mcgill.ca/ollama/api/generate"
    api_key = os.environ['ollama_api']

    payload = {
        "model": "llava:7b",
        "prompt": "Which one of these 4 categories does this photo belong: '0':'photograph', " \
                "'1':'chart',  '2':'other', '3':'text'?",
        "images": [binary_img],
        "stream": False
    }

    logging.debug("Decoding!")
    json_payload = json.dumps(payload)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.post(api_url, headers=headers, data=json_payload)

    if response.status_code == 200:
        response_text = response.text
        data = json.loads(response_text)
        answer = data['response']
        print("Request successful!")
    else:
        print("Error: {response.text}")
    pred = re.findall('"([^"]*)"', answer)[0]
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

    logging.debug(type)
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    categorise()
