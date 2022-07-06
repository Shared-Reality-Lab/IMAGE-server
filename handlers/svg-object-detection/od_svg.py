# Copyright (c) 2022 IMAGE Project, Shared Reality Lab, McGill University
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

from flask import Flask, jsonify, request
import json
import jsonschema
from jsonschema.exceptions import ValidationError
import logging
import time
import drawSvg as draw
import base64
import numpy as np
import cv2
# import cairosvg

app = Flask(__name__)


@app.route("/handler", methods=["POST"])
def handle():
    logging.debug("Received request")
    # Load necessary schema files
    with open("../../schemas/definitions.json") as f:
        definitions_schema = json.load(f)
    with open("../../schemas/request.schema.json") as f:
        request_schema = json.load(f)
    with open("../../schemas/handler-response.schema.json") as f:
        response_schema = json.load(f)
    with open("../../schemas/renderers/svglayers.schema.json") as f:
        renderer_schema = json.load(f)
    store = {
            definitions_schema["$id"]: definitions_schema,
            request_schema["$id"]: request_schema,
            response_schema["$id"]: response_schema,
            renderer_schema["$id"]: renderer_schema,
    }
    resolver = jsonschema.RefResolver.from_schema(
            request_schema, store=store
    )
    # Get and validate request contents
    contents = request.get_json()
    image_b64 = contents["graphic"].split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    img0 = cv2.imdecode(image, cv2.IMREAD_COLOR)
    cv2.imwrite('test.png', img0)
    # try:
    #     validator = jsonschema.Draft7Validator(
    #             request_schema, resolver=resolver
    #     )
    #     validator.validate(contents)
    # except ValidationError as e:
    #     logging.error(e)
    #     return jsonify("Invalid request received!"), 400

    # Check preprocessor data
    preprocessors = contents['preprocessors']

    # No Object Detector found
    if "ca.mcgill.a11y.image.preprocessor.objectDetection" not in preprocessors:
        logging.debug("No Object Detector found")
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(renderer_schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response
    if "dimensions" in contents:
        # If an existing graphic exists, often it is
        # best to use that for convenience.
        # see the following for SVG coordinate info:
        # developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Positions
        dimensions = contents["dimensions"]

    print(dimensions)
    objects = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]["objects"]
    grouped = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"]["grouped"]
    ungrouped = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"]["ungrouped"]
    svg = draw.Drawing(dimensions[0], dimensions[1])
    svg_layers = []
    if(len(grouped)>0):
        for i in range(len(grouped)):
            ids = grouped[i]["IDs"]
            category = objects[ids[0]]["type"]
            for j in range(len(ids)):
                
                width = int(objects[j]['dimensions'][2]*dimensions[0] - objects[j]['dimensions'][0]*dimensions[0])
                height = int((objects[j]['dimensions'][3]*dimensions[1]) - (objects[j]['dimensions'][1]*dimensions[1]))
                y = dimensions[1] - int(objects[j]['dimensions'][1]*dimensions[1])
                svg.append(draw.Rectangle(int(objects[j]['dimensions'][0]*dimensions[0]),y,width,height,stroke="#ff4477",fill_opacity=0))
                # svg.append(draw.Rectangle((objects[j]['dimensions'][0]),(objects[j]['dimensions'][1]),(objects[j]['dimensions'][2]),(objects[j]['dimensions'][3]),fill='#eeee00',stroke='black'))
                #svg.append(draw.Text(category,fontSize=8,x = int(objects[j]['dimensions'][2]*dimensions[0]),y = y,fill='black'))
            svg_layers.append({"label":category,"svg":svg.asDataUri()})
            # break
    if(len(ungrouped)>0):
        for i in range(len(ungrouped)):
            svg.append(draw.Rectangle((objects[i]['dimensions'][0]*dimensions[0]),(dimensions[1] - objects[i]['dimensions'][1]*dimensions[1]),(objects[i]['dimensions'][2]*dimensions[0]),(dimensions[1] - objects[i]['dimensions'][3]*dimensions[1])))
            svg.append(draw.Text(objects[i]["type"],8, 0, 0,fill='black'))
        svg_layers.append({"label":category,"svg":svg.asDataUri()})
            
    svg.saveSvg('example.svg')
    data = {
            "layers": svg_layers
    }
    rendering = {
            "type_id": "ca.mcgill.a11y.image.renderer.SVGLayers",
            "description": "An example SVG visualization",
            "data": data
    }
    try:
        validator = jsonschema.Draft7Validator(
                renderer_schema, resolver=resolver
        )
        validator.validate(data)
    except ValidationError as e:
        logging.error(e)
        logging.error("Failed to validate the response renderer!")
        return jsonify("Failed to validate the response renderer"), 500
    response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": [rendering]
    }
    try:
        validator = jsonschema.Draft7Validator(
                response_schema, resolver=resolver
        )
        validator.validate(response)
    except ValidationError as e:
        logging.error("Failed to generate a valid response")
        logging.error(e)
        return jsonify("Failed to generate a valid response"), 500
    logging.debug("Sending response")
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
