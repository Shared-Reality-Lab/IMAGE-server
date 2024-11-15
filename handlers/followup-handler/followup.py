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

from flask import Flask, jsonify, request
import json
import jsonschema
from jsonschema.exceptions import ValidationError
import logging
import time

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


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
    with open("./schemas/renderers/text.schema.json") as f:
        renderer_schema_text = json.load(f)
    with open("./schemas/renderers/tactilesvg.schema.json") as f:
        renderer_schema_tactile = json.load(f)

    store = {
        definitions_schema["$id"]: definitions_schema,
        request_schema["$id"]: request_schema,
        response_schema["$id"]: response_schema,
        renderer_schema_text["$id"]: renderer_schema_text,
        renderer_schema_tactile["$id"]: renderer_schema_tactile,
    }
    resolver = jsonschema.RefResolver.from_schema(
        request_schema, store=store
    )
    # Get and validate request contents
    contents = request.get_json()
    try:
        logging.debug("Validating request schema")
        validator = jsonschema.Draft7Validator(
            request_schema, resolver=resolver
        )
        validator.validate(contents)
    except ValidationError as e:
        logging.error(e)
        return jsonify("Invalid request received!"), 400

    # preprocessors = contents['preprocessors']
    # preprocessor_names = [] 
    logging.debug("Checking whether renderer is supported")
    if ("ca.mcgill.a11y.image.renderer.TactileSVG" not in contents["renderers"] 
       and "ca.mcgill.a11y.image.renderer.Text" not in contents["renderers"]):
        logging.debug("Neither Text nor TactileSVG Renderer are supported")
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
    # Currently has no preprocessor checks and none
    # current exist for followup
    # Checking for graphic and dimensions
    logging.debug("Checking whether graphic and"
                  " dimensions are available")
    if "graphic" in contents and "dimensions" in contents:
        # If an existing graphic exists, often it is
        # best to use that for convenience.
        # see the following for SVG coordinate info:
        # developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Positions
        logging.debug("Graphic has dimensions defined")
    else:
        logging.debug("Graphic and/or dimensions are not defined")
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
    # Checking whether this is an actual follow up query
    logging.debug("Checking whether this is "
                  "an actual follow up query")
    if "followup" in contents:
        # If an existing graphic exists, often it is
        # best to use that for convenience.
        # see the following for SVG coordinate info:
        # developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Positions
        followup = contents["followup"]
    else:
        logging.debug("Follow-up query is not defined")
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

    # Placeholder stuff to mock follow up responses here
    if "focus" in followup:
        data = {"text": ("The person is wearing a white t-shirt and a"
                            "dark grey blazer with stripes at the sleeves")}
        type = "ca.mcgill.a11y.image.renderer.Text"
        renderer_schema = renderer_schema_text
    else:
        if "show" in followup["query"]:
            svg = ('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOTYwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB4bWxuczpzdmc9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2ZXJzaW9uPSIxLjEiIHhtbDpzcGFjZT0icHJlc2VydmUiPgogPGcgY2xhc3M9ImxheWVyIiBhcmlhLWxhYmVsPSJab29tZWQgaW4gdmlldyBvZiB0aGUgc3RyaXBlcyIgZGF0YS1pbWFnZS1sYXllcj0iTGF5ZXIgMSI+CiAgCiAgPHJlY3QgZmlsbD0iI0ZGMDAwMCIgaGVpZ2h0PSI2OCIgaWQ9InN2Z18xIiBzdHJva2U9IiMwMDAwMDAiIHN0cm9rZS13aWR0aD0iNSIgd2lkdGg9Ijk4MiIgeD0iLTEyLjYiIHk9Ii00LjQiLz4KICA8cmVjdCBmaWxsPSIjRkYwMDAwIiBoZWlnaHQ9IjY4IiBpZD0ic3ZnXzIiIHN0cm9rZT0iIzAwMDAwMCIgc3Ryb2tlLXdpZHRoPSI1IiB3aWR0aD0iOTgyIiB4PSItMTEuMyIgeT0iMTE5LjciLz4KICA8cmVjdCBmaWxsPSIjRkYwMDAwIiBoZWlnaHQ9IjY4IiBpZD0ic3ZnXzMiIHN0cm9rZT0iIzAwMDAwMCIgc3Ryb2tlLXdpZHRoPSI1IiB3aWR0aD0iOTgyIiB4PSItOC4zIiB5PSIyNDcuNyIvPgogPC9nPgoKPC9zdmc+')
            data = {"graphic": svg}
            # "data:image/svg+xml;base64," +
            # base64.b64encode(bytes(svg, 'utf-8')).decode("utf-8")}
            type = "ca.mcgill.a11y.image.renderer.TactileSVG"
            renderer_schema = renderer_schema_tactile
        else:
            data = {"text": "The people are talking"}
            type = "ca.mcgill.a11y.image.renderer.Text"
            renderer_schema = renderer_schema_text

    rendering = {
        "type_id": type,
        "description": "Response to a follow-up query",
        "data": data
    }

    try:
        validator = jsonschema.Draft7Validator(
            renderer_schema, resolver=resolver
        )
        validator.validate(data)
    except ValidationError as e:
        logging.error(e)
        logging.debug("Failed to validate the response renderer!")
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
        logging.error(e)
        return jsonify("Failed to generate a valid response"), 500
    logging.debug("Sending response")
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
