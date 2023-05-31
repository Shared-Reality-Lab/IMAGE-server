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
    with open("./schemas/renderers/tactilesvg.schema.json") as f:
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

    preprocessor = contents["preprocessors"]

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
            logging.error(error)
            return jsonify("Invalid Preprocessor JSON format"), 500
        logging.debug("Missing " +
                      "'ca.mcgill.a11y.image.renderer.TactileSVG'." +
                      " Sending empty response.")
        return response

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
            logging.error(error)
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

    # List of minor street types ('footway', 'crossing' and 'steps')
    # to be filtered out to simplify the resulting rendering
    remove_streets = ["footway", "crossing", "steps"]
    svg = draw.Drawing(dimensions[0], dimensions[1])

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
        checkPOIs = {}
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
                # Add this arg only if the  not empty
                if description is not None:
                    args["aria_description"] = description
                p = draw.Path(**args)
                node_coordinates = []
                for node in street["nodes"]:
                    node_coordinates.append([node["lon"], node["lat"]])
                    if "POIs_ID" in node:
                        for POI_ID in node["POIs_ID"]:
                            if POI_ID in checkPOIs:
                                checkPOIs[POI_ID].append([name, description])
                            else:
                                checkPOIs[POI_ID] = [[name, description]]
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

                g.append(p)
        svg.append(g)

    if "ca.mcgill.a11y.image.preprocessor.nominatim"\
            in preprocessor:
        targetData = preprocessor[
                                 "ca.mcgill.a11y.image.preprocessor.nominatim"]
        try:
            latitude = (
                        (float(targetData["lat"]) - lat_min)
                        * scaled_latitude)
            longitude = (
                        (float(targetData["lon"]) - lon_min)
                        * scaled_longitude)
            targetTag = targetData["name"] if targetData["name"]\
                is not None else targetData["display_name"]\
                if targetData["display_name"]\
                is not None else targetData["type"]
            if type(targetTag) is not str:
                raise TypeError 
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
        except KeyError as e:
            logging.debug("Missing key " + str(e)
                          + " in neonatim preprocessor")
            logging.debug("Reverse geocode data not added to response")
        except TypeError as e:
            logging.debug("Expected to obtain string as POI name in nominatim ")
            logging.debug("Obtained type "+ str(type(targetTag)))

    if "points_of_interest" in data:
        for POI in data["points_of_interest"]:
            if POI["id"] in checkPOIs and POI["cat"] == "intersection":
                label = "Intersection of "
                if len(checkPOIs[POI["id"]]) == 1:
                    label += checkPOIs[POI["id"]][0][0]+" and minor street"
                    # description=checkPOIs[POI["id"]][0][0]+" "+checkPOIs[
                    # POI["id"]][0][1] if checkPOIs[POI["id"]][0][1]!=None
                    # else checkPOIs[POI["id"]][0][0]+" No details available"
                else:
                    label += ", ".join(x[0] for x in checkPOIs[POI["id"]][:-1])
                    label += " and "+checkPOIs[POI["id"]][-1][0]
                    # description=", ".join(((x[0]+" "+x[1]) if x[1]!=None else
                    # x[0]+" No details available") for x in
                    # checkPOIs[POI["id"]])
                latitude = (
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


def getDescriptions(street):
    description = ""
    default_attributes = ["street_id", "street_name", "nodes"]
    if "street_name" not in street:
        default_attributes.append("street_type")
    for attr in street:
        if attr not in default_attributes:
            match attr:
                case "oneway":
                    if street[attr]:
                        description += "oneway, "
                    else:
                        description += "not oneway, "
                case "lanes":
                    description += str(street[attr]) + " " + \
                        attr.replace("_", " ")+", "
                case _:
                    description += attr.replace("_", " ") + \
                        " " + str(street[attr])+", "

    # Remove the last ", "
    if description == "":
        return None
    else:
        return description[:-2]


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
