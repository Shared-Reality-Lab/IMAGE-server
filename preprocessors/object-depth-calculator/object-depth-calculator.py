# Copyright (c) 2023 IMAGE Project, Shared Reality Lab, McGill University
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

import cv2
import numpy as np
from flask import Flask, request, jsonify
import json
import time
import jsonschema
import base64

app = Flask(__name__)


@app.route("/preprocessor", methods=['POST', ])
def objectdepth():
    app.logger.debug("Received request")
    # load the schema
    with open('./schemas/preprocessors/object-depth-calculator.schema.json') \
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
        app.logger.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 400
    # check for depth-map
    if ("ca.mcgill.a11y.image.preprocessor.depth-map-gen"
            not in content["preprocessors"]):
        app.logger.info("Request does not contain a depth-map. Skipping...")
        return "", 204  # No content
    app.logger.debug("passed depth-map check")
    if ("ca.mcgill.a11y.image.preprocessor.objectDetection"
            not in content["preprocessors"]):
        app.logger.info("Request does not contain objects. Skipping...")
        return "", 204  # No content
    app.logger.debug("passed objects check")

    if "dimensions" in content:
        # If an existing graphic exists, often it is
        # best to use that for convenience.
        # see the following for SVG coordinate info:
        # developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Positions
        dimensions = content["dimensions"]
    else:
        app.logger.debug("Dimensions are not defined")
        response = {
            "request_uuid": content["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(
                schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            app.logger.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        app.logger.debug("Sending response")
        return response

    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.object-depth-calculator"
    preprocessors = content["preprocessors"]

    # convert the uri to processable image
    # Following 4 lines of code
    # refered form
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = (preprocessors["ca.mcgill.a11y.image.preprocessor.depth-map-gen"]
              ["depth-map"])
    image_b64 = source.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    img = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)/255

    o = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]
    objects = o["objects"]
    print(dimensions[0], dimensions[1])
    obj_depth = []

    app.logger.debug("number of objects")
    if (len(objects) > 0):
        for i in range(len(objects)):
            x1 = int(objects[i]['dimensions'][0] * dimensions[0])
            x2 = int(objects[i]['dimensions'][2] * dimensions[0])
            y1 = int(objects[i]['dimensions'][1] * dimensions[1])
            y2 = int(objects[i]['dimensions'][3] * dimensions[1])
            #h_extrema = np.percentile(img[x1:x2, y1:y2],90)
            #l_extrema = np.percentile(img[x1:x2, y1:y2],10)
            depthcomp = img[y1:y2, x1:x2]
            #depthcomp = np.where(depthcomp > h_extrema, np.nan, np.where(depthcomp < l_extrema, np.nan, depthcomp))
            depth = np.nanmedian(depthcomp)
            if np.isnan(depth):
                app.logger.error("NAN depth value")
                app.logger.debug("Ojbect #")
                app.logger.debug(str(i))
                app.logger.debug(str(x1))
                app.logger.debug(str(x2))
                depth = 1

            dictionary = {"ID": objects[i]["ID"],
                          "depth": depth
                          }
            obj_depth.append(dictionary)
        obj_depth_output = {"objects": obj_depth}

    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(obj_depth_output)
    except jsonschema.exceptions.ValidationError as e:
        app.logger.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": {"objects": obj_depth}
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        app.logger.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    app.logger.debug("Sending response")
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    objectdepth()
