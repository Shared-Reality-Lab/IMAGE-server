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
import numpy as np

configure_logging()
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


@app.route("/handler", methods=["POST"])
def handle():
    logging.debug("Received request")
    contents = request.get_json()
    preprocessors = contents['preprocessors']
    preprocessor_names = []
    """
    try:
        # Load necessary schema files
        with open("./schemas/definitions.json") as f:
            definitions_schema = json.load(f)
        with open("./schemas/request.schema.json") as f:
            request_schema = json.load(f)
        with open("./schemas/handler-response.schema.json") as f:
            response_schema = json.load(f)
        with open("./schemas/renderers/multistage-diagram.schema.json") as f:
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
    
    # Throws error when multistage diagram preprocessor NOT found
    logging.debug("Checking for object detection "
                  "and/ or semantic segmentation responses")
    if not ("ca.mcgill.a11y.image.preprocessor.semanticSegmentation"
            in preprocessors):
        logging.debug("No Multistage Diagram outputs found")
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
    """
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
        """
        try:
            validator = jsonschema.Draft7Validator(
                response_schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
            logging.error("Graphic validation error")
            logging.pii(f"Validation error: {error.message}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        """
        logging.debug("Sending response")
        return response
    # Initialize svg if either object detection
    # or semantic segmentation is present
    svg = draw.Drawing(dimensions[0], dimensions[1],
                       origin=(0, -dimensions[1]))
    # form = inflect.engine()
    caption = "Rendering os a multistage diagram"

    # if "ca.mcgill.a11y.image.preprocessor.objectDetection" in preprocessors:
    if True:
        logging.debug("Multistage diagram preprocessor found. "
                      "Adding data to response...")
        data = contents["preprocessors"][
                                     "ca.mcgill.a11y.image.preprocessor."
                                     "multistageDiagram"]
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
                    coord_vals= (min(coords[:][0]) if (min(coords[:][0])<coord_vals[0]) else coord_vals[0], 
                                 min(coords[:][1]) if (min(coords[:][1])<coord_vals[1]) else coord_vals[1], 
                                 max(coords[:][0]) if (max(coords[:][0])>coord_vals[2]) else coord_vals[2],
                                 max(coords[:][1]) if (max(coords[:][1])>coord_vals[3]) else coord_vals[3])
                g.append(p)
            coord_lims[stage["id"]] = coord_vals
        for link in data["links"]:
            label = ("Arrow between "+ link["source"] +
                     " and " + link["target"])
            src_cntr = (coord_lims[link["source"]][2] - coord_lims[link["source"]][0], 
                        coord_lims[link["source"]][3] - coord_lims[link["source"]][1])
            tgt_cntr = (coord_lims[link["target"]][2] - coord_lims[link["target"]][0], 
                        coord_lims[link["target"]][3] - coord_lims[link["target"]][1])
            angle = np.degrees(np.atan2((tgt_cntr[1]-src_cntr[1]), (tgt_cntr[0]-src_cntr[0])))
            logging.debug(label)
            logging.debug(angle)
            
            

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
        "description": ("Tactile rendering of photo with " +
                        " and ".join(preprocessor_names)),
        "data": data
    }
    """
    try:
        validator = jsonschema.Draft7Validator(
            renderer_schema, resolver=resolver
        )
        validator.validate(data)
    except ValidationError as e:
        logging.error("Failed to validate the response renderer")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Failed to validate the response renderer"), 500
    """
    response = {
        "request_uuid": contents["request_uuid"],
        "timestamp": int(time.time()),
        "renderings": [rendering]
    }
    """
    try:
        validator = jsonschema.Draft7Validator(
            response_schema, resolver=resolver
        )
        validator.validate(response)
    except ValidationError as e:
        logging.debug("Failed to generate a valid response")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Failed to generate a valid response"), 500
    """
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
