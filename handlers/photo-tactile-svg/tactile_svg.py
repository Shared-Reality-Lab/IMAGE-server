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
import inflect
from config.logging_utils import configure_logging
from datetime import datetime

configure_logging()
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


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
    preprocessor_names = []

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

    # Throws error when both Object Detector AND semantic segmentation are
    # NOT found
    # Also checks for grouping preprocessor along with object detector
    logging.debug("Checking for object detection "
                  "and/ or semantic segmentation responses")
    if not (("ca.mcgill.a11y.image.preprocessor.semanticSegmentation"
             in preprocessors) or
            all(x in preprocessors for x in
                ["ca.mcgill.a11y.image.preprocessor.objectDetection",
                 "ca.mcgill.a11y.image.preprocessor.grouping"])):
        logging.debug("No Object Detector and Semantic Segmentation found")
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

    # Initialize svg if either object detection
    # or semantic segmentation is present
    svg = draw.Drawing(dimensions[0], dimensions[1],
                       origin=(0, -dimensions[1]))
    form = inflect.engine()
    caption = ""

    if "ca.mcgill.a11y.image.preprocessor.objectDetection"\
        in preprocessors\
            and "ca.mcgill.a11y.image.preprocessor.grouping" in preprocessors:
        logging.debug("Object detector and grouping preprocessor found. "
                      "Adding data to response...")
        caption = "This photo contains "
        obj_list = []
        preprocessor_names.append('Things and people')
        o = preprocessors[
            "ca.mcgill.a11y.image.preprocessor.objectDetection"
            ]
        g = preprocessors["ca.mcgill.a11y.image.preprocessor.grouping"]
        objects = o["objects"]
        grouped = g["grouped"]
        ungrouped = g["ungrouped"]
        layer = 0
        # Loop through the object groups and generate a layer for each
        for group in grouped:
            ids = group["IDs"]
            obj_tag = objects[ids[0]]["type"]
            # Pluralize names of layers with more than 1 object
            category = form.plural(obj_tag).strip()
            obj_list.append(str(len(ids)) + " " + category)
            layer += 1
            g = draw.Group(data_image_layer="Layer " +
                           str(layer), aria_label=category)
            # Loop through the individual items
            # Draw a rectangle for each and tag objects
            for i, id in enumerate(ids):
                x1 = objects[id]['dimensions'][0] * dimensions[0]
                x2 = objects[id]['dimensions'][2] * dimensions[0]
                y1 = objects[id]['dimensions'][1] * dimensions[1]
                y2 = objects[id]['dimensions'][3] * dimensions[1]
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                start_y1 = -(y1 + height)
                g.append(
                    draw.Rectangle(
                        x1,
                        start_y1,
                        width,
                        height,
                        stroke="#ff4477",
                        stroke_width=2.5,
                        fill="none",
                        aria_label=obj_tag+" "+str(i+1)))

            svg.append(g)

        # Loop through ungrouped objects and generate a layer for each
        for val in ungrouped:
            category = objects[val]["type"].strip()
            # appending singular objects with appropriate article
            obj_list.append(form.a(category))
            layer += 1
            x1 = (objects[val]
                  ['dimensions'][0] * dimensions[0])
            x2 = (objects[val]
                  ['dimensions'][2] * dimensions[0])
            y1 = (objects[val]
                  ['dimensions'][1] * dimensions[1])
            y2 = (objects[val]
                  ['dimensions'][3] * dimensions[1])
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            start_y1 = -(y1 + height)
            svg.append(
                draw.Rectangle(
                    x1,
                    start_y1,
                    width,
                    height,
                    stroke="#ff4477",
                    stroke_width=2.5,
                    fill="none",
                    aria_label=category,
                    data_image_layer="Layer "+str(layer)))

        if len(obj_list) > 1:
            obj_list[-1] = "and " + obj_list[-1] + "."
            caption += ", ".join(obj_list)
        elif len(obj_list) == 1:
            caption += obj_list[0] + "."

    # Include semantic segmentation in SVG independent of the layers
    if "ca.mcgill.a11y.image.preprocessor.semanticSegmentation"\
            in preprocessors:
        logging.debug("Semantic segmentation found. "
                      "Adding data to response...")
        preprocessor_names.append("Outlines of regions")
        obj_list = []
        caption += ("This photo " +
                    ("" if len(caption) == 0 else "also ") +
                    "contains the following outlines of regions: ")
        s = preprocessors["ca.mcgill.a11y.image."
                          "preprocessor.semanticSegmentation"]
        segments = s["segments"]
        if (len(segments) > 0):
            for segment in segments:
                category = segment["name"]
                obj_list.append(category)
                contour = segment["contours"]
                try:
                    p = draw.Path(stroke="#ff4477", stroke_width=10,
                                  fill='none', aria_label=category,)
                except BaseException:
                    p = draw.Path(stroke="red", stroke_width=10,
                                  fill='none', aria_label=category,)
                for c in contour:
                    coords = c["coordinates"]
                    for i in range(1, len(coords), 5):
                        if (i == 1):
                            p.M(coords[i][0] * dimensions[0],
                                (- coords[i][1] * dimensions[1]))
                        p.L(coords[i][0] * dimensions[0],
                            (- coords[i][1] * dimensions[1]))
                svg.append(p)

        if len(obj_list) > 0:
            if len(obj_list) > 1:
                obj_list[-1] = "and " + obj_list[-1] + "."
                caption += ", ".join(obj_list)
            else:
                caption += obj_list[0] + "."

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
        "description": ("Tactile rendering of photo with " +
                        " and ".join(preprocessor_names)),
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
