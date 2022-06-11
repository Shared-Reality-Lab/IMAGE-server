from flask import Flask, jsonify, request
import jsonschema
import json
import logging
from osm_service import (
    query_OSMap,
    get_timestamp,
    create_bbox_coordinates,
    process_OSMap_data,
    extract_street,
    allot_intersection,
    get_amenities,
    enlist_POIs,
    OSM_preprocessor,
    validate,
    get_coordinates,
)

app = Flask(__name__)


@app.route("/")
def health():
    return {"Hello": "World"}


@app.route('/preprocessor', methods=['POST', ])
def get_map_data():
    """
    Gets data on locations nearby a map from the OVERPASS API
    """
    logging.debug("Received request")
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

    # Build OpenStreetMap request
    coords = get_coordinates(content)

    if coords is None:
        error = 'Invalid map place received. Unable to find Lat/Lng'
        logging.error(error)
        return jsonify(error), 400

    latitude = coords["latitude"]
    longitude = coords["longitude"]
    request_uuid = content["request_uuid"]
    distance: float = 100
    bbox_coordinates = create_bbox_coordinates(distance, latitude, longitude)
    OSM_data = query_OSMap(bbox_coordinates)
    processed_OSM_data = process_OSMap_data(OSM_data)
    intersection_record_updated = extract_street(processed_OSM_data)
    POD1 = allot_intersection(processed_OSM_data, intersection_record_updated)
    amenity = get_amenities(bbox_coordinates)
    POIs = enlist_POIs(POD1, amenity)
    response = OSM_preprocessor(processed_OSM_data, POIs)
    response = {
        "point_of_interest": POIs,
        "streets": response,
    }
    response = {

        "request_uuid": request_uuid,
        "timestamp": int(get_timestamp()),
        "name": "ca.mcgill.a11y.image.preprocessor.openstreetmap",
        "data": response

    }

    validated = validate(
        schema=schema,
        data=response,
        resolver=resolver,
        json_message='Invalid Preprocessor JSON format',
        error_code=500)

    if validated is not None:
        return validated

    logging.debug("Sending response")
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
