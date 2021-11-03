import requests  # pip3 install requests
from re import search
import operator

# import numpy as np
import json
import time
import jsonschema
import logging
import base64
import os
from flask import Flask, request, jsonify

app = Flask(__name__)


def process_results(response, labels):
    if not response["categories"]:
        return labels[0]
    else:
        category_dict = {i["name"]: i["score"] for i in response["categories"]}

        label = max(category_dict.items(), key=operator.itemgetter(1))[0]
        if any(search(i, label) for i in labels):
            for i in labels:
                if i in label:
                    return(i)
        else:
            return labels[0]


def process_image(image, labels):

    region = "canadacentral"  # For example, "westus"
    api_key = os.environ["AZURE_API_KEY"]

    # Set request headers
    headers = dict()
    headers['Ocp-Apim-Subscription-Key'] = api_key
    headers['Content-Type'] = 'application/octet-stream'

    # Set request querystring parameters
    # params = {'visualFeatures': 'Color,Categories,
    # Tags,Description,ImageType,Faces,Adult,Objects'}
    """Only query categories"""
    params = {'visualFeatures': 'Categories'}

    # Make request and process response
    response = requests.request(
        'post',
        "https://{}.api.cognitive.microsoft.com/vision/v1.0/analyze".format(
                                    region),
        data=image,
        headers=headers,
        params=params
    )

    if response.status_code == 200 or response.status_code == 201:

        if 'content-length' in response.headers and \
                int(response.headers['content-length']) == 0:
            label = labels[0]
        elif 'content-type' in response.headers and \
                isinstance(response.headers['content-type'], str):
            if 'application/json' in response.headers['content-type'].lower():
                if response.content:
                    result = response.json()
                    label = process_results(response=result, labels=labels)
                else:
                    label = labels[0]
            elif 'image' in response.headers['content-type'].lower():
                result = response.content

    else:
        label = labels[0]
#         label = response.json()['message']
#         print("Error code: %d" % response.status_code)
#         print("Message: %s" % response.json())
#     category = process_results(result, labels)

    return label


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    # load the schema
    labels = ["other", "indoor", "outdoor", "people"]
    with open('./schemas/preprocessors/classifier-l2.schema.json') as jsonfile:
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
    name = "ca.mcgill.a11y.image.preprocessor.secondCategoriser"
    preprocess_output = content["preprocessors"]

    # convert the uri to processable image
    if content["image"] is None:
        return "", 204
    else:
        if "ca.mcgill.a11y.image.firstCategoriser" in preprocess_output:
            firstCat = \
                preprocess_output["ca.mcgill.a11y.image.firstCategoriser"]
            request_type = firstCat["category"]
            if request_type == "image":
                source = content["image"]
                image_b64 = source.split(",")[1]
                binary = base64.b64decode(image_b64)
                pred = process_image(image=binary, labels=labels)
                type = {"category": pred}
            else:
                """If the first classifier does not detect an image
                the second classifier should not process the request"""
                return "", 204
        else:
            """We are providing the user the ability to process an image
            even when the first classifier is absent, however it is
            recommended that the second classifier be used in conjunction
            with the first classifier."""
            source = content["image"]
            image_b64 = source.split(",")[1]
            binary = base64.b64decode(image_b64)
            pred = process_image(image=binary, labels=labels)
            type = {"category": pred}
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
            validator = jsonschema.Draft7Validator(schema,
                                                   resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(e)
            return jsonify("Invalid Preprocessor JSON format"), 500
        return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
