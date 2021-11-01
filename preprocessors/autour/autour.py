import json
import time
import logging
import jsonschema
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_map_data():
    # Load schemas
    with open('./schemas/preprocessors/autour.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    schema_store = {
        data_schema['$id']: data_schema,
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    content = request.get_json()
    ###### Currently not validating properly ######
    with open('./schemas/preprocessors/request.schema.json') as jsonfile:
        request_schema = json.load(jsonfile)
    resolver = jsonschema.RefResolver.from_schema(
            request_schema, store=schema_store)
    try:
        validator = jsonschema.Draft7Validator(data_schema, resolver=resolver)
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Request JSON format"), 400

        
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

    places = dict()
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
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
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
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500

    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
