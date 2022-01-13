import os
import json
import time
import logging
import jsonschema
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_map_data():
    """
    Gets data on locations nearby a map from the Autour API
    """
    # Load schemas
    with open('./schemas/preprocessors/autour.schema.json') as jsonfile:
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

    validated = validate(request_schema, content, resolver, "Invalid Request JSON format", 400)

    if validated is not None:
        return validated

    # Check if request is for a map
    if 'image' in content:
        logging.info("Not map content. Skipping...")
        return "", 204

    # Build Autour request
    url = content['url']
    coords = get_coordinates(content)

    if coords is None:
        error = 'Invalid map place received. Unable to find Lat/Lng'
        logging.error(error)
        return jsonify(error), 400

    api_request = f"https://isassrv.cim.mcgill.ca/autour/getPlaces.php?\
            framed=1&\
            times=1&\
            radius=250&\
            lat={coords['latitude']}&\
            lon={coords['longitude']}&\
            condensed=0&\
            from=foursquare&\
            as=json&\
            fsqmulti=1&\
            font=9&\
            pad=0"

    response = requests.get(api_request).json()
    results = response['results']

    places = {}
    for result in results:
        places[result['id']] = {k: v for k, v in result.items() if k != 'id'}

    name = 'ca.mcgill.a11y.image.preprocessor.autour'
    request_uuid = content['request_uuid']
    timestamp = int(time.time())
    data = {
        'url': url,
        'lat': coords['latitude'],
        'lon': coords['longitude'],
        'api_request': api_request,
        'places': places,
    }

    # Use response schema to validate response
    resolver = jsonschema.RefResolver.from_schema(
            schema, store=schema_store)

    validated = validate(data_schema, data, resolver, 'Invalid Preprocessor JSON format', 500)

    if validated is not None:
        return validated

    response = {
        'request_uuid': request_uuid,
        'timestamp': timestamp,
        'name': name,
        'data': data
    }

    validated = validate(schema, response, resolver, 'Invalid Preprocessor JSON format', 500)

    if validated is not None:
        return validated

    return response

def validate(schema, data, resolver, json_messaage, error_code):
    """
    Validate a piece of data against a schema

    Args:
        schema: a JSON schema to check against
        data: the data to check
        resolver: a JSON schema resolver
        json_messaage: the error to jsonify and return
        error_code: the error code to return

    Returns:
        None or Tuple[flask.Response, int]
    """
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as error:
        logging.error(error)
        return jsonify(json_messaage), error_code

    return None

def get_coordinates(content):
    """
    Retrieve the coordinates of a map from the
    content of the request or through a Google Places API call

    Args:
        content: a dictionary with the content of the map

    Returns:
        Dict[str: int] or None
    """
    if 'coordinates' in content.keys():
        return content['coordinates']

    google_api_key = os.environ["GOOGLE_PLACES_KEY"]

    # Query google places API to find latlong
    place_response = requests.get(
        f"https://maps.googleapis.com/maps/api/place/textsearch/json? \
            query={content['placeID']}& \
            key={google_api_key}"
        ).json()

    if not check_google_response(place_response):
        return None

    coordinates = {
        'latitude': place_response['results'][0]['geometry']['location']['lat'],
        'longitude': place_response['results'][0]['geometry']['location']['lng']
    }

    return coordinates

def check_google_response(place_response):
    """
    Helper method to check whether the response from
    the Google Places API is valid

    Args:
        place_response: the response from the Google Places API

    Returns:
        bool: True if valid, False otherwise
    """
    if 'results' not in place_response.keys() or len(place_response['results']) == 0:
        logging.error("No results found for placeID")
        return False

    if 'geometry' not in place_response['results'][0].keys():
        logging.error("No geometry found for placeID")
        return False

    if 'location' not in place_response['results'][0]['geometry'].keys():
        logging.error("No location found for placeID")
        return False

    if 'lat' not in place_response['results'][0]['geometry']['location'].keys():
        logging.error("No lat found for placeID")
        return False

    if 'lng' not in place_response['results'][0]['geometry']['location'].keys():
        logging.error("No lng found for placeID")
        return False

    return True


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
