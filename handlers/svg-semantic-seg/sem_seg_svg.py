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

    # No Object Detector found
    if "ca.mcgill.a11y.image.preprocessor.semanticSegmentation" not in preprocessors:
        logging.debug("No Semantic Segmenter found")
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


    segments = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]["segments"]
    svg = draw.Drawing(dimensions[0], dimensions[1])
    svg_layers = []
    colors = ["red","blue","yellow","green"]
    new_contour = []
    if(len(segments)>0):
        for j in range(len(segments)):
            contour = segments[j]["contours"]
            svg_lines = []
            p = draw.Path(stroke=colors[j], stroke_width=2, fill='none',)
            for k in range(len(contour)):
                coord = contour[k]["coordinates"]
                for i in range(len(coord)):
                    if(i==0):
                        continue
                    if(i==1):
                        p.M(coord[i][0]*dimensions[0], (dimensions[1] - coord[i][1]*dimensions[1]))
                    p.L(coord[i][0]*dimensions[0],dimensions[1] - coord[i][1]*dimensions[1])
                    # svg_lines.append(coord[i][0]*dimensions[0])
                    # svg_lines.append(dimensions[1] - coord[i][1]*dimensions[1])
                # new_contour.append(i)
            # p = draw.Path(stroke=colors[j], stroke_width=2, fill='none',)  # Add an arrow to the end of a path
            # p.M(svg_lines[0], svg_lines[1])
            # l=2
            # while(l<(len(svg_lines)-1)):
            #     p.L(svg_lines[l],svg_lines[l+1])
            #     l = l+2
            svg.append(p)
            svg_layers.append({"label":segments[j]["name"],"svg":svg.asDataUri()})
            break
            
    svg.saveSvg('/Users/rohanakut/Desktop/labWork/docker_here2/handlers/svg-semantic-seg/example.svg')
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
