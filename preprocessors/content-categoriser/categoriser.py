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

from flask import Flask, request, jsonify
import time
import logging
import sys
from datetime import datetime
from config.logging_utils import configure_logging
from utils.llm import LLMClient, CATEGORISER_PROMPT

from utils.validation import Validator
import json

configure_logging()

app = Flask(__name__)

DATA_SCHEMA = './schemas/preprocessors/content-categoriser.schema.json'
with open(DATA_SCHEMA, 'r') as f:
    CATEGORISER_RESPONSE_SCHEMA = json.load(f)

categories_properties = (
    CATEGORISER_RESPONSE_SCHEMA.get("properties", {})
    .get("categories", {})
    .get("properties", {})
)
POSSIBLE_CATEGORIES = str(list(categories_properties.keys()))
logging.debug(f"Possible categories: {POSSIBLE_CATEGORIES}")

PREPROCESSOR_NAME = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"

try:
    llm_client = LLMClient()
    validator = Validator(data_schema=DATA_SCHEMA)
    logging.debug("LLM client and validator initialized")
except Exception as e:
    logging.error(f"Failed to initialize clients: {e}")
    sys.exit(1)


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    logging.debug("Received request")

    # load the content and verify incoming data
    content = request.get_json()

    # request schema validation (check_* style)
    ok, _ = validator.check_request(content)
    if not ok:
        return jsonify({"error": "Invalid Preprocessor JSON format"}), 400

    # check we received a graphic (e.g., not a map or chart request)
    if "graphic" not in content:
        logging.info("Request is not a graphic. Skipping...")
        return "", 204  # No content

    request_uuid = content["request_uuid"]
    timestamp = time.time()

    # convert the uri to processable image
    # source.split code referred from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = content["graphic"]
    base64_image = source.split(",")[1]

    graphic_category = llm_client.chat_completion(
        prompt=f"{CATEGORISER_PROMPT} {POSSIBLE_CATEGORIES}",
        image_base64=base64_image,
        temperature=0.0,
        json_schema=CATEGORISER_RESPONSE_SCHEMA,
        parse_json=True
    )

    if graphic_category is None:
        logging.error("Failed to receive response from LLM.")
        return jsonify(
            {"error": "Failed to get graphic category from LLM"}
        ), 500

    # data schema validation
    ok, _ = validator.check_data(graphic_category)
    if not ok:
        return jsonify("Invalid Preprocessor JSON format"), 500

    # create full response & check meets overall preprocessor response schema
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": PREPROCESSOR_NAME,
        "data": graphic_category
    }

    # response envelope validation
    ok, _ = validator.check_response(response)
    if not ok:
        return jsonify("Invalid Preprocessor JSON format"), 500

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


@app.route("/warmup", methods=["GET"])
def warmup():
    """
    vLLM loads and keeps the specified model in memory on container startup,
    but we keep this endpoint as a health check.
    """
    try:
        if llm_client.warmup():
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify(
                {"status": "error", "message": "Warmup failed"}
            ), 500
    except Exception as e:
        logging.error(f"Warmup endpoint failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
