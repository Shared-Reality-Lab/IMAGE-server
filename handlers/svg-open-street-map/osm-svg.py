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
    # Get and validate the request contents
    contents = request.get_json()
    try:
        validator = jsonschema.Draft7Validator(
            request_schema, resolver=resolver
        )
        validator.validate(contents)
    except ValidationError as e:
        logging.error(e)
        return jsonify("None"), 204

    # Check preprocessor data
    preprocessor = contents['preprocessors']

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
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    if "ca.mcgill.a11y.image.preprocessor.openstreetmap"\
            not in preprocessor:
        logging.info("Not for OSM preprocessor. Skipping ...")
        return "", 204
    dimensions = 500, 500
    svg = draw.Drawing(
        dimensions[0],
        dimensions[1])

    svg_layers = []
    data = preprocessor["ca.mcgill.a11y.image.preprocessor.openstreetmap"]
    if "streets" in data:
        streets = data["streets"]
        lat = data["bounds"]["latitude"]
        lon = data["bounds"]["longitude"]
        lon_min = lon["min"]
        lat_min = lat["min"]
        lon_max = lon["max"]
        lat_max = lat["max"]
        # Scale the lon/lat units to svg pixels equivalent.
        scaled_longitude = dimensions[0] / (lon_max - lon_min)
        scaled_latitude = dimensions[1] / (lat_max - lat_min)
        bounds = [[lon_min, lat_min],
                  [lon_min, lat_max],
                  [lon_max, lat_max],
                  [lon_max, lat_min],
                  [lon_min, lat_min]]
        # Draw bounding box for the streets
        for index in range(len(bounds) - 1):
            p = draw.Path(stroke="orange", stroke_width=6, fill='none')
            p.M(scaled_longitude * (bounds[index][0] - lon_min),
                scaled_latitude * (bounds[index][1] - lat_min))
            p.L(scaled_longitude * (bounds[index + 1][0] - lon_min),
                scaled_latitude * (bounds[index + 1][1] - lat_min))
            svg.append(p)

        colors = [
            "red",
            "blue",
            "springgreen",
            "deeppink",
            "orange",
            "purple",
            "cyan",
            "coral",
            "teal",
            "indigo",
            "lime",
            "chocolate",
            "magenta",
            "crimson",
            "deepskyblue",
            "greenyellow",
            "gold",
            "green",
            "aqua",
            "navy",
            "royalblue",
            "forestgreen",
            "dodgerblue"
        ]
        # Draw the streets with svg.
        for street in range(len(streets)):
            color = street
            if street >= len(colors):
                color = street % len(colors)
            p = draw.Path(
                stroke=colors[color],
                stroke_width=1.5,
                fill='none')
            node_coordinates = [[node["lon"], node["lat"]]
                                for node in streets[street]["nodes"]]
            for index in range(len(node_coordinates) - 1):
                p.M(scaled_longitude *
                    (node_coordinates[index][0] -
                     lon_min), scaled_latitude *
                    (node_coordinates[index][1] -
                     lat_min))
                p.L(scaled_longitude *
                    (node_coordinates[index +
                                      1][0] -
                     lon_min), scaled_latitude *
                    (node_coordinates[index +
                                      1][1] -
                     lat_min))
                svg.append(p)
            if "street_name" in streets[street]:
                svg_layers.append(
                    {"label": streets[street]["street_name"],
                        "svg": svg.asDataUri()})
            else:
                svg_layers.append(
                    {"label": str(streets[street]["street_id"]),
                        "svg": svg.asDataUri()})
        data = {
            "layers": 
            
        }
        rendering = {
            "type_id": "ca.mcgill.a11y.image.renderer.SVGLayers",
            "description": "This is SVG data to visualize response \
                             from the OpenStreetMap preprocessor.",
            "data": data}
        try:
            validator = jsonschema.Draft7Validator(
                renderer_schema, resolver=resolver
            )
            validator.validate(data)
        except ValidationError as e:
            logging.error(e)
            logging.error("Failed to validate the response renderer!")
            return jsonify("Failed to validate the response renderer"), 500
    else:
        logging.info("No data for streets. Skipping ...")
        return "", 204
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
    app.run(host="0.0.0.0", port=5000, debug=True)
