# Copyright (c) 2022 IMAGE Project, Shared Reality Lab, McGill University
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


import json
import time
import logging
import jsonschema
from flask import Flask, request, jsonify

from charts_utils import getLowerPointsOnLeft, getHigherPointsOnLeft
from charts_utils import getLowerPointsOnRight, getHigherPointsOnRight
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_chart_info():
    """
    The preprocessor currently handles only single-line charts,
    functionality to be extended later
    """
    logging.debug("Received request")
    # Load schemas
    with open('./schemas/preprocessors/line-charts.schema.json') as jsonfile:
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

    # Check if request is for a chart
    if 'highChartsData' not in content:
        logging.info("Not a highcharts charts request. Skipping...")
        return "", 204

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

    name = 'ca.mcgill.a11y.image.preprocessor.lineChart'
    request_uuid = content['request_uuid']
    timestamp = int(time.time())

    series_object = content['highChartsData']['series'][0]
    series_data = series_object['data']

    for index, point in enumerate(series_data):
        point['lowerPointsOnLeft'] = getLowerPointsOnLeft(
                                        index,
                                        point,
                                        series_data
                                    )
        point['higherPointsOnLeft'] = getHigherPointsOnLeft(
                                        index,
                                        point,
                                        series_data
                                    )
        point['lowerPointsOnRight'] = getLowerPointsOnRight(
                                        index,
                                        point,
                                        series_data
                                    )
        point['higherPointsOnRight'] = getHigherPointsOnRight(
                                        index,
                                        point,
                                        series_data
                                    )

    data = {'dataPoints': series_data}

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

    logging.debug("Sending response")
    logging.debug(data)
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
    app.run(host='0.0.0.0', port=5000, debug=True)
