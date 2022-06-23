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

    # Check for dimensions
    if "dimensions" in contents:
        # If an existing graphic exists, often it is
        # best to use that for convenience.
        # see the following for SVG coordinate info:
        # developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Positions
        dimensions = contents["dimensions"]
    else:
        # otherwise, pick something sensible for the task.
        # 200x200 is arbitrary in this case.
        dimensions = 200, 200
    # Create dummy hello world SVG
    svg = draw.Drawing(dimensions[0], dimensions[1], origin='center')
    svg.append(draw.Text("Hello, world", 8, 0, 0, fill='black'))
    data = {
            "layers": [
                {
                    "label": "The example SVG",
                    "svg": svg.asDataUri(),
                }
            ],
            "description": "An example SVG that conveys nothing useful,"
                           + " but says hello."
    }
    rendering = {
            "type_id": "ca.mcgill.a11y.image.renderer.SVGLayers",
            "description": "An example SVG visualization",
            "data": data
    }
    # Validate response and return
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
    app.run(host="0.0.0.0", port=80, debug=False)
