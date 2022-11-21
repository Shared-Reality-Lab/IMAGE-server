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

app = Flask(__name__)


@app.route("/handler", methods=["POST"])
def handle():
    logging.debug("Received request")
    # Load necessary schema files
    with open("./schemas/definitions.json") as f:
        definitions_schema = json.load(f)
    with open("./schemas/request.schema.json") as f:
        request_schema = json.load(f)
    with open("./schemas/handler-response.schema.json") as f:
        response_schema = json.load(f)
    with open("./schemas/renderers/svglayers.schema.json") as f:
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
    try:
        validator = jsonschema.Draft7Validator(
            request_schema, resolver=resolver
        )
        validator.validate(contents)
    except ValidationError as e:
        logging.error(e)
        return jsonify("Invalid request received!"), 400

    # Check preprocessor data
    preprocessors = contents['preprocessors']
    if "ca.mcgill.a11y.image.capability.DebugMode" \
            not in contents['capabilities']:
        logging.debug("Debug mode inactive")
        print("debug inactive")
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(
                response_schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    # No Object Detector found
    if "ca.mcgill.a11y.image.preprocessor.objectDetection"\
            not in preprocessors:
        logging.debug("No Object Detector found")
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(
                response_schema, resolver=resolver)
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
    else:
        logging.debug("Dimensions are not defined")
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        try:
            validator = jsonschema.Draft7Validator(
                response_schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    o = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]
    g = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"]
    u = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"]
    objects = o["objects"]
    grouped = g["grouped"]
    ungrouped = u["ungrouped"]
    svg = draw.Drawing(dimensions[0], dimensions[1])
    print(dimensions[0], dimensions[1])
    svg_layers = []
    if (len(grouped) > 0):
        for i in range(len(grouped)):
            ids = grouped[i]["IDs"]
            category = objects[ids[0]]["type"]
            for j in range(len(ids)):
                print(ids[j])
                x1 = int(objects[ids[j]]['dimensions'][0] * dimensions[0])
                x2 = int(objects[ids[j]]['dimensions'][2] * dimensions[0])
                y1 = int(objects[ids[j]]['dimensions'][1] * dimensions[1])
                y2 = int(objects[ids[j]]['dimensions'][3] * dimensions[1])
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                start_y1 = abs(dimensions[1] - y1 - height)
                svg.append(
                    draw.Rectangle(
                        x1,
                        start_y1,
                        width,
                        height,
                        stroke="#ff4477",
                        fill_opacity=0))
            svg_layers.append({"label": category, "svg": svg.asDataUri()})
            # break

    if (len(ungrouped) > 0):
        for i in range(len(ungrouped)):
            category = objects[ungrouped[i]]["type"]
            print(category)
            x1 = int(objects[ungrouped[i]]['dimensions'][0] * dimensions[0])
            x2 = int(objects[ungrouped[i]]['dimensions'][2] * dimensions[0])
            y1 = int(objects[ungrouped[i]]['dimensions'][1] * dimensions[1])
            y2 = int(objects[ungrouped[i]]['dimensions'][3] * dimensions[1])
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            start_y1 = abs(dimensions[1] - y1)
            svg.append(
                draw.Rectangle(
                    x1,
                    start_y1,
                    width,
                    height,
                    stroke="#dd4477",
                    fill_opacity=0))
            svg_layers.append({"label": category, "svg": svg.asDataUri()})
    data = {
        "layers": svg_layers
    }
    rendering = {
        "type_id": "ca.mcgill.a11y.image.renderer.ODSVGLayers",
        "description": "Object Detection SVG visualization",
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
