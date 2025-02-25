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
from datetime import datetime
from config.logging_utils import configure_logging

configure_logging()

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


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
    # Get and validate the request contents
    contents = request.get_json()
    try:
        validator = jsonschema.Draft7Validator(
            request_schema, resolver=resolver
        )
        validator.validate(contents)
    except ValidationError as e:
        logging.error("Validation error occurred")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("None"), 204

    preprocessor = contents["preprocessors"]

    # Checking for TactileSVG renderer in request
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
            logging.error("Response validation failed")
            logging.pii(f"Validation error: {error.message}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Missing " +
                      "'ca.mcgill.a11y.image.renderer.TactileSVG'." +
                      " Sending empty response.")
        return response

    # Checking for data from OSM preprocessor
    if "ca.mcgill.a11y.image.preprocessor.openstreetmap"\
            not in preprocessor:
        logging.debug("OSM Preprocessor data not present. Skipping ...")
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
            logging.error("Response validation failed")
            logging.pii(f"Validation error: {error.message}")
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Missing " +
                      "'ca.mcgill.a11y.image.preprocessor.openstreetmap'." +
                      " Sending empty response.")
        return response

    dimensions = 700, 700

    renderingDescription = ("Tactile rendering of map centered at latitude " +
                            str(contents["coordinates"]["latitude"]) +
                            " and longitude " +
                            str(contents["coordinates"]["longitude"]))
    caption = ("Map centered at latitude " +
               str(contents["coordinates"]["latitude"]) +
               " and longitude " +
               str(contents["coordinates"]["longitude"]))
    # List of minor street types ('footway', 'crossing' and 'steps')
    # to be filtered out to simplify the resulting rendering
    remove_streets = ["footway", "crossing", "steps", "elevator"]
    svg = draw.Drawing(dimensions[0], dimensions[1],
                       origin=(0, -dimensions[1]))

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
        checkPOIs = []
        # Drawing streets in the first layer
        g = draw.Group(data_image_layer="firstLayer", aria_label="Streets")
        for i, street in enumerate(streets):
            color = i % len(colors)
            # Filter only necessary street types
            if street["street_type"] not in remove_streets:
                name = street["street_name"] if "street_name"\
                    in street else street["street_type"]
                description = getDescriptions(street)
                stroke_width = return_stroke_width(
                    street["street_type"])
                args = dict(stroke=colors[color], stroke_width=stroke_width,
                            fill='none', aria_label=name)
                # Add this arg only if the detailed description is not empty
                if description is not None:
                    args["aria_description"] = description
                p = draw.Path(**args)
                node_coordinates = []
                for node in street["nodes"]:
                    node_coordinates.append([node["lon"], node["lat"]])
                    if "POIs_ID" in node:
                        for POI_ID in node["POIs_ID"]:
                            if POI_ID not in checkPOIs:
                                checkPOIs.append(POI_ID)
                for index in range(len(node_coordinates) - 1):
                    p.M(scaled_longitude *
                        (node_coordinates[index][0] -
                         lon_min), scaled_latitude *
                        (node_coordinates[index][1] -
                         lat_min) - dimensions[1])
                    p.L(scaled_longitude *
                        (node_coordinates[index +
                                          1][0] -
                         lon_min), scaled_latitude *
                        (node_coordinates[index +
                                          1][1] -
                         lat_min) - dimensions[1])

                g.append(p)
        svg.append(g)

    # Checking for location tag from nominatim preprocessor
    if "ca.mcgill.a11y.image.preprocessor.nominatim"\
            in preprocessor:
        targetData = preprocessor[
                                 "ca.mcgill.a11y.image.preprocessor.nominatim"]
        try:
            latitude = (-dimensions[1] +
                        (float(targetData["lat"]) - lat_min)
                        * scaled_latitude)
            longitude = (
                        (float(targetData["lon"]) - lon_min)
                        * scaled_longitude)
            targetTag = targetData["name"] if\
                (notNoneorBlank(targetData["name"]))\
                else targetData["display_name"]\
                if (notNoneorBlank(targetData["display_name"]))\
                else targetData["type"]
            if type(targetTag) is not str:
                raise TypeError("Type Error. Obtained " +
                                "variable of type " + str(type(targetTag)))
            if targetTag.strip() == "":
                raise ValueError("Value Error. Obtained "
                                 "empty or blank string:"
                                 "'"+targetTag+"'")
            # Drawing a circle at point of interest if location tag is found
            svg.append(
                        draw.Circle(
                                    longitude,
                                    latitude,
                                    20,
                                    fill='green',
                                    stroke_width=1.5,
                                    stroke='green',
                                    aria_label=targetTag))
            """
            ## Using bounding box occasionally results in the whole map
            ## being occupied by the target POI
            ## e.g. when McGill University is the detected target POI
            bb=targetData["boundingbox"]
            logging.debug(", ".join(bb))
            lat_start = (
                        (float(bb[0]) - lat_min)
                        * scaled_latitude)
            height = (
                        (float(bb[1]) - lat_min)
                        * scaled_latitude
                        - lat_start)
            lon_start = (
                        (float(bb[2]) - lon_min)
                        * scaled_longitude)
            width = (
                        (float(bb[3]) - lon_min)
                        * scaled_longitude
                        -lon_start)
            svg.append(
                        draw.Rectangle(
                                        lon_start,
                                        lat_start,
                                        width,
                                        height,
                                        fill='red',
                                        stroke_width=1.5,
                                        stroke='red',
                                        aria_label=targetData["name"]))
            """
            renderingDescription = "Tactile rendering of map centered at "\
                + targetTag
            caption = "Map centered at " + targetTag
        except KeyError as e:
            logging.debug("Missing required key in nominatim preprocessor")
            logging.pii(f"KeyError: {e}")
            logging.debug("Reverse geocode data not added to response")
        except (TypeError, ValueError) as e:
            logging.debug(
                "Invalid value encountered in nominatim preprocessor")
            logging.pii(f"Validation error: {e}")
            logging.debug("Reverse geocode data not added to response")

    # Drawing in the nodes of category
    # intersection, traffic lights or crossing
    # along with their descriptions
    if "points_of_interest" in data:
        for POI in data["points_of_interest"]:
            if POI["id"] in checkPOIs:
                label, drawPOI = getNodeDescription(POI)
                if drawPOI:
                    latitude = (-dimensions[1] +
                                (POI["lat"] - lat_min)
                                * scaled_latitude)
                    longitude = (
                                (POI["lon"] - lon_min)
                                * scaled_longitude)
                    svg.append(
                                draw.Circle(
                                            longitude,
                                            latitude,
                                            10,
                                            fill='red',
                                            stroke_width=1.5,
                                            stroke='red',
                                            aria_label=label))
    title = draw.Title(caption)
    svg.append(title)
    data = {"graphic": svg.asDataUri()}
    rendering = {
        "type_id": "ca.mcgill.a11y.image.renderer.TactileSVG",
        "description": renderingDescription,
        "data": data}
    try:
        validator = jsonschema.Draft7Validator(
            renderer_schema, resolver=resolver
        )
        validator.validate(data)
    except ValidationError as e:
        logging.error("Failed to validate the response renderer!")
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
        logging.error("Failed to generate a valid response")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Failed to generate a valid response"), 500
    logging.debug("Sending response")
    return response


# Returns stroke width for various street types
def return_stroke_width(street_type):
    if (street_type == "primary" or street_type == "secondary"):
        stroke_width = 7.5
    elif street_type == "tertiary":
        stroke_width = 6.5
    elif street_type == "residential":
        stroke_width = 4.5
    elif (street_type == "footway" or street_type == "crossing"):
        stroke_width = 3.0
    else:
        stroke_width = 1.5
    return stroke_width


# Generates the long description for streets
def getDescriptions(street):
    description = ""
    # default_attributes = ["street_id", "street_name", "nodes", "service"]
    # filtering for only the required attributes
    # as there are now some hard to understand attributes
    attributes = [
        "oneway", "lanes", "surface", "maxspeed", "access",
        "sidewalk"
        ]
    if "street_name" in street:
        attributes.append("street_type")
    for attr, val in street.items():
        if attr in attributes:
            match attr:
                case "oneway":
                    if val:
                        description += "oneway, "
                    else:
                        description += "not oneway, "
                case "lanes":
                    description += str(val) + " " + \
                        attr.replace("_", " ")+", "
                case "access":
                    if val == "yes":
                        description += "public access, "
                    else:
                        description += val + " " + \
                            attr + ", "
                case "sidewalk":
                    if val == "no":
                        description += "No usable sidewalk, "
                    else:
                        description += "Sidewalk present, "
                case _:
                    description += attr.replace("_", " ") + \
                        " " + str(street[attr].replace("_", " "))+", "

    # Remove the last ", "
    if description == "":
        return None
    else:
        return description[:-2]


# Returns the description at nodes with intersections,
# crossing, traffic lights or tactile paving
def getNodeDescription(POI):
    label = ""
    drawPOI = False
    if "intersection" in POI:
        drawPOI = True
        label += "Intersection"
    if "cat" in POI:
        tag, drPOI = getNodeCategoryData(POI)
        if len(label) != 0:
            label += ", "
        label += tag
        if drPOI:
            drawPOI = drPOI
    if "tactile_paving" in POI:
        tag = getNodePavingData(POI)
        if len(label) != 0:
            label += ", "
        label += tag
    return label, drawPOI


# Check for nodes of category
# traffic signal or crossing
# and generate their descriptions
def getNodeCategoryData(POI):
    tag = ""
    draw = True
    category = POI["cat"]
    match category:
        case "crossing":
            if POI["crossing"] == "marked":
                tag += "Marked crossing, "
            elif POI["crossing"] == "unmarked":
                tag += "Unmarked crossing, "
            elif POI["crossing"] == "traffic_signals":
                tag += "Crossing with traffic signal, "
            else:
                tag += "Crossing, "
        case "traffic_signals":
            tag += "Traffic lights present, "
        case _:
            draw = False
    return (tag if len(tag) == 0 else tag[:-2]), draw


# Generate tactile paving description
def getNodePavingData(POI):
    tag = ""
    paving = POI["tactile_paving"]
    match paving:
        case "yes":
            tag += "Tactile paving present, "
        case "no":
            tag += "Tactile paving absent, "
        case "contrasted":
            tag += "Tactile paving with high contrast, "
        case "incorrect":
            tag += "Incorrect tactile paving"
        case _:
            pass
    return (tag if len(tag) == 0 else tag[:-2])


# Checks whether input value is None or empty
def notNoneorBlank(x):
    if ((x is not None) and
            (x.strip() != "")):
        return True
    else:
        return False


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
