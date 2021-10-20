from flask import Flask, request, jsonify
import json
import time
import jsonschema
import logging
import collections

app = Flask(__name__)

@app.route('/preprocessor', methods=['POST', 'GET'])
def get_map_data():
    
    with open('./schemas/preprocessors/autour.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
            schema, store=schema_store)
    content = request.get_json()
    url = content['url']
    coords = content['coordinates']
    api_request = 'https://isassrv.cim.mcgill.ca/autour/getPlaces.php?\
            framed=1&\
            times=1&\
            radius=250&\
            lat={latitude}&\
            lon={longitude}&\
            condensed=0&\
            from=foursquare&\
            as=json&\
            fsqmulti=1&\
            font=9&\
            pad=0'.format(latitude=coords['latitude'], longitude=coords['longitude'])

    name = 'ca.mcgill.a11y.image.preprocessor.autour'
    request_uuid = content['request_uuid']
    timestamp = int(time.time())
    response = {
        'request_uuid': request_uuid,
        'timestamp': timestamp,
        'name': name,
        'data': {
            'url': url,
            'coordinates': coords,
            'api_request': api_request
        }
    }

    return response
    
    



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)