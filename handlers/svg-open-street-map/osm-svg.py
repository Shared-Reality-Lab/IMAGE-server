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
from colour import Color
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
        return jsonify("Invalid request received!"), 400

    preprocessor = contents['preprocessors']
    # Check preprocessor data
    if "ca.mcgill.a11y.image.preprocessor.openstreetmap"\
            not in preprocessor:
        logging.info("Not for OSM preprocessor. Skipping ...")
        return "", 204
    dimensions = 500, 500
    svg = draw.Drawing(dimensions[0], dimensions[1])
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
        # Latitude is north-south, Longitude is east-west
        for street in range(len(streets)):
            foo = object()
            p = draw.Path(
                stroke=Color(
                    pick_for=foo),
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

            svg_layers.append(
                {"label": streets[street]["street_type"],
                    "svg": svg.asDataUri()})
        data = {
            "layers": svg_layers
        }
        rendering = {
            "type_id": "ca.mcgill.a11y.image.renderer.SVGLayers",
            "description": "OpenStreetMap Visualisation",
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
