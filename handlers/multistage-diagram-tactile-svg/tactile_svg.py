# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
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
from config.logging_utils import configure_logging
from datetime import datetime
import numpy as np

configure_logging()
app = Flask(__name__)


@app.route("/handler", methods=["POST"])
def handle():
    logging.debug("Received request")
    try:
        # Load necessary schema files
        with open("./schemas/definitions.json") as f:
            definitions_schema = json.load(f)
        with open("./schemas/request.schema.json") as f:
            request_schema = json.load(f)
        with open("./schemas/handler-response.schema.json") as f:
            response_schema = json.load(f)
        with open("./schemas/renderers/tactilesvg.schema.json") as f:
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
        logging.debug("Validating request schema")
        validator = jsonschema.Draft7Validator(
            request_schema, resolver=resolver
        )
        validator.validate(contents)
    except ValidationError as e:
        logging.error("Validation error in request schema")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid request received!"), 400

    preprocessors = contents['preprocessors']

    logging.debug("Checking whether renderer is supported")
    if "ca.mcgill.a11y.image.renderer.TactileSVG" not in contents["renderers"]:
        logging.debug("TactileSVG Renderer not supported")
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
            logging.error("Renderer validation error")
            logging.pii(f"Validation error: {error.message}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    # Throws error when both multistage diagram preprocessor NOT found
    logging.debug("Checking for multistage diagram "
                  "segmentation responses")
    if not ("ca.mcgill.a11y.image.preprocessor.multistage-diagram-segmentation"
            in preprocessors):
        logging.debug("Multistage Diagram Preprocessor not found")
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
            logging.error("Preprocessor validation error")
            logging.pii(f"Validation error: {error.message}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response

    logging.debug("Checking whether graphic and"
                  " dimensions are available")
    if "graphic" in contents and "dimensions" in contents:
        # If an existing graphic exists, often it is
        # best to use that for convenience.
        # see the following for SVG coordinate info:
        # developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Positions
        dimensions = contents["dimensions"]
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
            logging.error("Graphic validation error")
            logging.pii(f"Validation error: {error.message}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Sending response")
        return response
    # Initialize svg if either multistage diagram preprocessor is present
    svg = draw.Drawing(dimensions[0], dimensions[1],
                       origin=(0, -dimensions[1]))
    caption = "Rendering is a multistage diagram"

    preprocessors = contents['preprocessors']
    logging.debug("Multistage diagram preprocessor found. "
                  "Adding data to response...")
    data = contents["preprocessors"][
                                    "ca.mcgill.a11y.image.preprocessor."
                                    "multistage-diagram-segmentation"]
    layer = 0
    g = draw.Group(data_image_layer="Layer " +
                   str(layer), aria_label="Overview")
    coord_lims = {}
    # Loop through stages
    for stage in data["stages"]:
        label = stage["label"]
        description = None
        if description in stage:
            description = stage["description"]
        # (x_min, y_min, x_max, y_max)
        coord_vals = (1, 1, 0, 0)
        segments = stage["segments"]
        for segment in segments:
            contour = segment["contours"]
            try:
                p = draw.Path(stroke="#ff4477", stroke_width=10,
                              fill='none', aria_label=label,)
            except BaseException:
                p = draw.Path(stroke="red", stroke_width=10,
                              fill='none', aria_label=label,)
            if description is not None:
                p.append(aria_description=description)
            for c in contour:
                coords = c["coordinates"]
                for i in range(1, len(coords), 5):
                    if (i == 1):
                        p.M(coords[i][0] * dimensions[0],
                            (- coords[i][1] * dimensions[1]))
                    p.L(coords[i][0] * dimensions[0],
                        (- coords[i][1] * dimensions[1]))
                coords = np.asarray(coords)
                coords_max = coords.max(axis=0, keepdims=True)
                coords_min = coords.min(axis=0, keepdims=True)
                coord_vals = (coords_min[0][0]
                              if (coords_min[0][0] < coord_vals[0])
                              else coord_vals[0],
                              coords_min[0][1]
                              if (coords_min[0][1] < coord_vals[1])
                              else coord_vals[1],
                              coords_max[0][0]
                              if (coords_max[0][0] > coord_vals[2])
                              else coord_vals[2],
                              coords_max[0][1]
                              if (coords_max[0][1] > coord_vals[3])
                              else coord_vals[3])
            g.append(p)
        coord_lims[stage["id"]] = {"lims": coord_vals, "name": label}
    for link in data["links"]:
        try:
            label = ("Arrow between " + coord_lims[link["source"]]["name"] +
                     " and " + coord_lims[link["target"]]["name"])
            src_cntr = ((coord_lims[link["source"]]["lims"][2] +
                        coord_lims[link["source"]]["lims"][0])/2,
                        (coord_lims[link["source"]]["lims"][3] +
                        coord_lims[link["source"]]["lims"][1])/2)
            tgt_cntr = ((coord_lims[link["target"]]["lims"][2] +
                        coord_lims[link["target"]]["lims"][0])/2,
                        (coord_lims[link["target"]]["lims"][3] +
                        coord_lims[link["target"]]["lims"][1])/2)
            arw_src = cohenSutherlandClip(src_cntr, tgt_cntr,
                                          (coord_lims
                                           [link["source"]]["lims"]))
            arw_tgt = cohenSutherlandClip(tgt_cntr, src_cntr,
                                          (coord_lims
                                           [link["target"]]["lims"]))
            arw_src = point_at_distance(arw_src, arw_tgt, 0.1)
            arw_tgt = point_at_distance(arw_tgt, arw_src, 0.2)
            p = draw_arrow(arw_src, arw_tgt, dimensions,
                           label, link["directed"])
            g.append(p)
        except Exception as e:
            logging.debug("Encountered error while drawing arrow")
            logging.pii(e.message)

    svg.append(g)

    # Checking if graphic-caption preprocessor is present
    if ("ca.mcgill.a11y.image.preprocessor.graphic-caption"
            in preprocessors):
        logging.debug("Adding title from "
                      "graphic-caption")
        caption = preprocessors["ca.mcgill.a11y.image."
                                "preprocessor.graphic-caption"][
                            "caption"]
    else:
        logging.debug("graphic-caption not found. "
                      "Adding default title.")

    title = draw.Title(caption)
    svg.append(title)
    logging.debug("Generating final rendering")
    data = {"graphic": svg.asDataUri()}

    rendering = {
        "type_id": "ca.mcgill.a11y.image.renderer.TactileSVG",
        "description": ("Tactile rendering of multistage diagram"),
        "data": data
    }
    try:
        validator = jsonschema.Draft7Validator(
            renderer_schema, resolver=resolver
        )
        validator.validate(data)
    except ValidationError as e:
        logging.error("Failed to validate the response renderer")
        logging.pii(f"Validation error: {e.message}")
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
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Failed to generate a valid response"), 500
    logging.debug("Sending response")
    return response


# Adapted from the implementation of
# Cohen-Sutherland algorithm at :
# https://www.geeksforgeeks.org/line-clipping-set-1-cohen-sutherland-algorithm/
# Function to compute region code for a point(x, y)
def computeCode(x, y, lims):
    (x_min, y_min, x_max, y_max) = lims
    code = 0
    if x < x_min:  # to the left of rectangle
        code |= 1
    elif x > x_max:  # to the right of rectangle
        code |= 2
    if y < y_min:  # below the rectangle
        code |= 4
    elif y > y_max:  # above the rectangle
        code |= 8
    return code


# Adapted from the implementation of
# Cohen-Sutherland algorithm at :
# https://www.geeksforgeeks.org/line-clipping-set-1-cohen-sutherland-algorithm/
def cohenSutherlandClip(src, tgt, lims):
    (x_min, y_min, x_max, y_max) = lims
    (x1, y1) = src
    (x2, y2) = tgt
    # Compute region codes for P1, P2
    code1 = computeCode(x1, y1, lims)
    code2 = computeCode(x2, y2, lims)
    while True:

        # If both endpoints lie within rectangle
        if code1 == 0 and code2 == 0:
            break

        # Some segment lies within the rectangle
        else:

            # Line needs clipping
            # At least one of the points is outside,
            # select it
            x = 1.0
            y = 1.0

            # Find intersection point
            # using formulas y = y1 + slope * (x - x1),
            # x = x1 + (1 / slope) * (y - y1)
            if code2 & 8:
                # Point is above the clip rectangle
                x = x1 + (x2 - x1) * (y_max - y1) / (y2 - y1)
                y = y_max
            elif code2 & 4:
                # Point is below the clip rectangle
                x = x1 + (x2 - x1) * (y_min - y1) / (y2 - y1)
                y = y_min
            elif code2 & 2:
                # Point is to the right of the clip rectangle
                y = y1 + (y2 - y1) * (x_max - x1) / (x2 - x1)
                x = x_max
            elif code2 & 1:
                # Point is to the left of the clip rectangle
                y = y1 + (y2 - y1) * (x_min - x1) / (x2 - x1)
                x = x_min

            # Now intersection point (x, y) is found
            # We replace point outside clipping rectangle
            # by intersection point
            x2 = x
            y2 = y
            code2 = computeCode(x2, y2, lims)

    return (x2, y2)


def point_at_distance(start_point, end_point, fraction):
    """
    Calculates a point at a specified distance along a line segment.

    Args:
        start_point (tuple): Coordinates of the starting point (x, y).
        end_point (tuple): Coordinates of the ending point (x, y).
        fraction (float): Fraction of distance from the start point to the
        desired point.

    Returns:
        tuple: Coordinates of the point at the specified distance (x, y).
               Returns None if the distance is invalid.
    """
    x1, y1 = start_point
    x2, y2 = end_point

    line_length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
    distance = line_length * fraction

    if line_length == 0:
        return start_point

    ratio = distance / line_length

    x = x1 + ratio * (x2 - x1)
    y = y1 + ratio * (y2 - y1)

    return (x, y)


# Draws arrows between stages
def draw_arrow(arw_src, arw_tgt, dimensions, label, directed):
    try:
        p = draw.Path(stroke="#ff4477", stroke_width=10,
                      fill='none', aria_label=label,)
    except BaseException:
        p = draw.Path(stroke="red", stroke_width=10,
                      fill='none', aria_label=label,)
    p.M(arw_src[0] * dimensions[0],
        (- arw_src[1] * dimensions[1]))
    p.L(arw_tgt[0] * dimensions[0],
        (- arw_tgt[1] * dimensions[1]))
    if directed:
        # Length of arrow head
        arw_hd_start = point_at_distance(arw_tgt, arw_src, 0.1)
        # find point at perpendicular distance from arrow head base
        dx = arw_src[0] - arw_tgt[0]
        dy = arw_src[1] - arw_tgt[1]
        L = (dx**2 + dy**2)**0.5
        distance = 0.05 * L
        # Unit direction vector of the line
        ux = dx / L
        uy = dy / L
        # Unit normal vector (perpendicular to line)
        nx = -dy / L
        ny = dx / L
        offset_x1 = (ux + nx) / np.sqrt(2)
        offset_y1 = (uy + ny) / np.sqrt(2)
        offset_x2 = (ux - nx) / np.sqrt(2)
        offset_y2 = (uy - ny) / np.sqrt(2)
        # Final points at the given distance
        p1 = (arw_hd_start[0] + distance * offset_x1, arw_hd_start[1] +
              distance * offset_y1)
        p2 = (arw_hd_start[0] + distance * offset_x2, arw_hd_start[1] +
              distance * offset_y2)
        p.M(p1[0] * dimensions[0],
            (- p1[1] * dimensions[1]))
        p.L(arw_tgt[0] * dimensions[0],
            (- arw_tgt[1] * dimensions[1]))
        p.L(p2[0] * dimensions[0],
            (- p2[1] * dimensions[1]))
    return p


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint to verify if the service is running
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
