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


import time
import logging
from flask import Flask, request, jsonify
from config.logging_utils import configure_logging
from utils.validation import Validator
from charts_utils import getLowerPointsOnLeft, getHigherPointsOnLeft
from charts_utils import getLowerPointsOnRight, getHigherPointsOnRight
from datetime import datetime

configure_logging()

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Initialize shared validator
VALIDATOR = Validator(
    data_schema='./schemas/preprocessors/line-charts.schema.json'
)


@app.route('/preprocessor', methods=['POST', 'GET'])
def get_chart_info():
    """
    The preprocessor currently handles only single-line charts,
    functionality to be extended later
    """
    logging.debug("Received request")

    content = request.get_json()

    # Check if request is for a chart
    if 'highChartsData' not in content:
        logging.info("Not a highcharts charts request. Skipping...")
        return "", 204

    # request validation (request.schema.json)
    ok, _ = VALIDATOR.check_request(content)
    if not ok:
        return jsonify("Invalid Request JSON format"), 400

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

    # data validation
    ok, _ = VALIDATOR.check_data(data)
    if not ok:
        return jsonify("Invalid Preprocessor JSON format"), 500

    response = {
        'request_uuid': request_uuid,
        'timestamp': timestamp,
        'name': name,
        'data': data
    }

    # Validate response (preprocessor-response.schema.json)
    ok, _ = VALIDATOR.check_response(response)
    if not ok:
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
