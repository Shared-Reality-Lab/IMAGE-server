# Copyright (c) 2021 IMAGE Project, Shared Reality Lab, McGill University
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

import os
import time
import logging
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from config.logging_utils import configure_logging
from utils.validation import Validator

configure_logging()

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Initialize shared validator
VALIDATOR = Validator(data_schema='./schemas/preprocessors/autour.schema.json')


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_map_data():
    """
    Gets data on locations nearby a map from the Autour API
    """
    logging.debug("Received request")

    content = request.get_json()

    # Validate incoming request
    ok, _ = VALIDATOR.check_request(content)
    if not ok:
        return jsonify("Invalid Request JSON format"), 400

    # Check if request is for a map
    if 'coordinates' not in content and 'placeID' not in content:
        logging.info("Not map content. Skipping...")
        return "", 204

    # Build Autour request
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
            from=transit|osmxing|osmsegments|foursquare&\
            as=json&\
            fsqmulti=1&\
            font=9&\
            pad=0"

    api_request = ''.join(api_request.split())

    try:
        response = requests.get(api_request).json()
    except Exception as e:
        logging.error("Failed to fetch data from Autour API")
        logging.pii(f"Error: {e}")
        return jsonify("Failed to fetch data from Autour API"), 500

    results = response['results']

    name = 'ca.mcgill.a11y.image.preprocessor.autour'
    request_uuid = content['request_uuid']
    timestamp = int(time.time())
    data = {
        'lat': coords['latitude'],
        'lon': coords['longitude'],
        'api_request': api_request,
        'places': results,
    }

    # Validate preprocessor data against its schema
    ok, _ = VALIDATOR.check_data(data)
    if not ok:
        return jsonify('Invalid Preprocessor JSON format'), 500

    response = {
        'request_uuid': request_uuid,
        'timestamp': timestamp,
        'name': name,
        'data': data
    }

    # Validate full response
    ok, _ = VALIDATOR.check_response(response)
    if not ok:
        return jsonify('Invalid Preprocessor JSON format'), 500

    logging.debug("Sending response")
    return response


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
    request = f"https://maps.googleapis.com/maps/api/place/textsearch/json?\
            query={content['placeID']}&\
            key={google_api_key}"

    request = request.replace(" ", "")

    place_response = requests.get(request).json()

    if not check_google_response(place_response):
        logging.error("Failed to retrieve valid response from Google API")
        logging.pii(f"Google API response: {place_response}")
        return None

    location = place_response['results'][0]['geometry']['location']
    coordinates = {
        'latitude': location['lat'],
        'longitude': location['lng']
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
    if 'results' not in place_response or len(place_response['results']) == 0:
        logging.error("No results found for placeID")
        logging.pii(f"Google API response: {place_response}")
        return False

    results = place_response['results'][0]

    if 'geometry' not in results:
        logging.error("No geometry found for placeID")
        return False

    if 'location' not in results['geometry']:
        logging.error("No location found for placeID")
        return False

    if 'lat' not in results['geometry']['location']:
        logging.error("No lat found for placeID")
        return False

    if 'lng' not in results['geometry']['location']:
        logging.error("No lng found for placeID")
        return False

    return True


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
    app.run(host='0.0.0.0', port=5000, debug=True)
