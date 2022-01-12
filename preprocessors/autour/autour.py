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
    
    google_api_key = os.environ["GOOGLE_PLACES_KEY"]
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
    
    if 'coordinates' not in content.keys() and 'placeID' in content.keys():
        # Query google places API to find latlong
        place_response = requests.get(f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={content['placeID']}&key={google_api_key}")
        coordinates = {
            'latitude': place_response.json()['results'][0]['geometry']['location']['lat'],
            'longitude': place_response.json()['results'][0]['geometry']['location']['lng']
        }
        content['coordinates'] = coordinates
    
    with open('./schemas/request.schema.json') as jsonfile:
        request_schema = json.load(jsonfile)
    # Validate incoming request
    resolver = jsonschema.RefResolver.from_schema(
            request_schema, store=schema_store)
    try:
        validator = jsonschema.Draft7Validator(
            request_schema,
            resolver=resolver
        )
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as error:
        logging.error(error)
        return jsonify("Invalid Request JSON format"), 400
    # Use response schema to validate response
    resolver = jsonschema.RefResolver.from_schema(
            schema, store=schema_store)
    # Check if request is for a map
    if 'image' in content:
        logging.info("Not map content. Skipping...")
        return "", 204
    # Build Autour request
    url = content['url']
    coords = content['coordinates']
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

    try:
        validator = jsonschema.Draft7Validator(data_schema, resolver=resolver)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as error:
        logging.error(error)
        return jsonify("Invalid Preprocessor JSON format"), 500

    response = {
        'request_uuid': request_uuid,
        'timestamp': timestamp,
        'name': name,
        'data': data
    }

    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as error:
        logging.error(error)
        return jsonify("Invalid Preprocessor JSON format"), 500

    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
