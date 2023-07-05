from flask import Flask, jsonify, request
import jsonschema
import json
import logging
from osm_service import (
    get_streets,
    get_timestamp,
    create_bbox_coordinates,
    process_streets_data,
    extract_street,
    allot_intersection,
    get_amenities,
    enlist_POIs,
    OSM_preprocessor,
    validate,
    get_coordinates,
)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configure logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%y-%m-%d %H:%M %Z",
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


@app.route('/preprocessor', methods=['POST', ])
def get_map_data():
    """
    Gets map data from OpenStreetMap
    """
    LOGGER.debug("Received request")
    # Load schemas
    with open('./schemas/preprocessors/openstreetmap.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definition_schema = json.load(jsonfile)
    schema_store = {
        data_schema['$id']: data_schema,
        schema['$id']: schema,
        definition_schema['$id']: definition_schema
    }
    content = request.get_json()
    with open('./schemas/request.schema.json') as jsonfile:
        request_schema = json.load(jsonfile)
    # Validate incoming request
    resolver = jsonschema.RefResolver.from_schema(
        request_schema, store=schema_store)

    validated = validate(
        schema=request_schema,
        data=content,
        resolver=resolver,
        json_message="Invalid Request JSON format",
        error_code=400)

    if validated is not None:
        return validated

    # Check if this request is for an openstreetmap
    if 'coordinates' not in content and 'placeID' not in content:
        LOGGER.info("Not map content. Skipping...")
        response = {
            "request_uuid": request_uuid,
            "timestamp": time_stamp,
            "name": name,
            "data": { }
        }
        try:
            validator = jsonschema.Draft7Validator(
            response_schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
                LOGGER.error(error)
                return jsonify("Invalid Preprocessor JSON format"), 500
        LOGGER.debug("Sending response")
        return response

    # Build OpenStreetMap request
    coords = get_coordinates(content)
    if coords is None:
        error = 'Unable to find Latitude/Longitude'
        LOGGER.error(error)
        response = {
            "request_uuid": request_uuid,
            "timestamp": time_stamp,
            "name": name,
            "data": { }
        }
        try:
            validator = jsonschema.Draft7Validator(
            response_schema, resolver=resolver)
            validator.validate(response)
        except jsonschema.exceptions.ValidationError as error:
                LOGGER.error(error)
                return jsonify("Invalid Preprocessor JSON format"), 500
        LOGGER.debug("Sending response")
        return response

    latitude = coords["latitude"]
    longitude = coords["longitude"]
    # distance in metres
    distance = 100
    time_stamp = int(get_timestamp())
    bbox_coordinates = create_bbox_coordinates(distance, latitude, longitude)
    name = "ca.mcgill.a11y.image.preprocessor.openstreetmap"
    header_info = {
        "latitude": {
            "min": bbox_coordinates[0],
            "max": bbox_coordinates[2]
        },
        "longitude": {
            "min": bbox_coordinates[1],
            "max": bbox_coordinates[3]
        }
    }
    OSM_data = get_streets(bbox_coordinates)
    request_uuid = content["request_uuid"]
    amenity = get_amenities(bbox_coordinates)
    if OSM_data is not None:
        processed_OSM_data = process_streets_data(OSM_data, bbox_coordinates)
        if processed_OSM_data is None:
            POD1 = None
        else:
            intersection_record_updated = extract_street(processed_OSM_data)
            POD1 = allot_intersection(
                processed_OSM_data,
                intersection_record_updated)
        POIs = enlist_POIs(POD1, amenity)
        if processed_OSM_data is not None and len(processed_OSM_data) != 0:
            response = OSM_preprocessor(processed_OSM_data, POIs, amenity)
            response = {
                "request_uuid": request_uuid,
                "timestamp": time_stamp,
                "name": name,
                "data": {
                    "bounds": header_info,
                    "points_of_interest": POIs,
                    "streets": response
                }
            }
        elif amenity is not None and len(amenity) != 0:
            response = {
                "request_uuid": request_uuid,
                "timestamp": time_stamp,
                "name": name,
                "data": {
                    "bounds": header_info,
                    "points_of_interest": amenity
                }
            }
        else:
            response = {
                "request_uuid": request_uuid,
                "timestamp": time_stamp,
                "name": name,
                "data": {
                    "bounds": header_info
                }
            }
    elif OSM_data is None and amenity is not None:
        response = {
            "request_uuid": request_uuid,
            "timestamp": time_stamp,
            "name": name,
            "data": {
                "bounds": header_info,
                "points_of_interest": amenity
            }
        }
    else:
        response = {
            "request_uuid": request_uuid,
            "timestamp": time_stamp,
            "name": name,
            "data": {
                "bounds": header_info
            }
        }
    validated = validate(
        schema=schema,
        data=response,
        resolver=resolver,
        json_message='Invalid Preprocessor JSON format',
        error_code=500)

    if validated is not None:
        return validated
    LOGGER.debug("Sending response")
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
