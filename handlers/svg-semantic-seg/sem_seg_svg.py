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
import random
from config.logging_utils import configure_logging

configure_logging()

app = Flask(__name__)


@app.route("/handler", methods=["POST"])
def handle():
    try:
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
    except Exception as e:
        logging.error("Error loading schema files")
        logging.pii(f"Schema loading error: {e}")
        return jsonify("Schema files could not be loaded"), 500

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
        logging.error("Validation error in request schema")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid request received!"), 400

    # Check preprocessor data
    preprocessors = contents['preprocessors']
    if ("ca.mcgill.a11y.image.capability.DebugMode"
        not in contents['capabilities']
            or "ca.mcgill.a11y.image.renderer.SVGLayers"
            not in contents["renderers"]):
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
            logging.pii(f"Renderer validation error: {error}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    # No Object Detector found
    if "ca.mcgill.a11y.image.preprocessor.semanticSegmentation"\
            not in preprocessors:
        logging.debug("No Semantic Segmenter found")
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
            logging.pii(f"Preprocessor validation error: {error}")
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
            logging.pii(f"Preprocessor validation error: {error}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    s = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]
    segments = s["segments"]
    svg = draw.Drawing(dimensions[0], dimensions[1])
    svg_layers = []
    colors = [
        "red",
        "blue",
        "yellow",
        "green",
        "pink",
        "orange",
        "purple",
        "cyan",
        "coral",
        "teal",
        "indigo",
        "lime",
        "chocolate"]
    if (len(segments) > 0):
        for j in range(len(segments)):
            contour = segments[j]["contours"]
            print(str(hex(random.randint(0, 0xFFFFFF))))
            try:
                p = draw.Path(stroke=colors[j], stroke_width=4, fill='none',)
            except BaseException:
                p = draw.Path(stroke="red", stroke_width=4, fill='none',)
            for k in range(len(contour)):
                coord = contour[k]["coordinates"]
                for i in range(len(coord)):
                    if (i == 0):
                        continue
                    if (i == 1):
                        p.M(coord[i][0] * dimensions[0],
                            (dimensions[1] - coord[i][1] * dimensions[1]))
                    p.L(coord[i][0] * dimensions[0],
                        dimensions[1] - coord[i][1] * dimensions[1])
            svg.append(p)
            svg_layers.append(
                {"label": segments[j]["name"], "svg": svg.asDataUri()})
            svg = draw.Drawing(dimensions[0], dimensions[1])
    data = {
        "layers": svg_layers
    }
    rendering = {
        "type_id": "ca.mcgill.a11y.image.renderer.SVGLayers",
        "description": "Semantic Segmentation Visualisation",
        "data": data
    }
    try:
        validator = jsonschema.Draft7Validator(
            renderer_schema, resolver=resolver
        )
        validator.validate(data)
    except ValidationError as e:
        logging.error("Failed to validate the response renderer!")
        logging.pii(f"Renderer validation error: {e}")
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
        logging.debug("Failed to generate a valid response")
        logging.pii(f"Response validation error: {e}")
        return jsonify("Failed to generate a valid response"), 500\

    logging.debug("Sending response")
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
