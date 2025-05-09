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
import requests
import json
import time
import jsonschema
import logging
import os
from datetime import datetime
from config.logging_utils import configure_logging

configure_logging()

app = Flask(__name__)


@app.route("/preprocessor", methods=['POST', ])
def categorise():
    logging.debug("Received request")

    # load the schemas and verify incoming data
    with open('./schemas/preprocessors/content-categoriser.schema.json') \
            as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') \
            as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    # Following 6 lines of code from
    # https://stackoverflow.com/questions/42159346
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
    content = request.get_json()
    try:
        validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for incoming request")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid Preprocessor JSON format"), 400

    # check we received a graphic (e.g., not a map or chart request)
    if "graphic" not in content:
        logging.info("Request is not a graphic. Skipping...")
        return "", 204  # No content

    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"

    # convert the uri to processable image
    # source.split code referred from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = content["graphic"]
    graphic_b64 = source.split(",")[1]

    # prepare ollama request
    api_url = f"{os.environ['OLLAMA_URL']}/generate"
    api_key = os.environ['OLLAMA_API_KEY']
    ollama_model = os.environ['OLLAMA_MODEL']

    logging.debug("OLLAMA_URL " + api_url)
    if api_key.startswith("sk-"):
        logging.pii("OLLAMA_API_KEY looks properly formatted: " +
                    api_key[:3] + "[redacted]")
    else:
        logging.warning("OLLAMA_API_KEY usually starts with sk-, "
                     "but this one starts with: " + api_key[:3])

    prompt = "Answer only in JSON with the format " \
             '{"category": "YOUR_ANSWER"}. ' \
             "Which of the following categories best " \
             "describes this image, selecting from this enum: "
    possible_categories = "photograph, chart, text, other"
    # override with prompt from environment variable only if it exists
    prompt = os.getenv('CONTENT_CATEGORISER_PROMPT_OVERRIDE', prompt)
    prompt += "[" + possible_categories + "]"
    logging.debug("prompt: " + prompt)

    request_data = {
        "model": ollama_model,
        "prompt": prompt,
        "images": [graphic_b64],
        "stream": False,
        "format": "json",
        "temperature": 0.0,
        "keep_alive": -1  # keep model loaded in memory indefinitely
    }
    logging.debug("serializing json from request_data dictionary")
    request_data_json = json.dumps(request_data)
    logging.debug("serialization complete")

    request_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    logging.debug("Posting request to ollama model " + ollama_model)
    response = requests.post(api_url, headers=request_headers,
                             data=request_data_json)
    logging.debug("ollama request response code: " + str(response.status_code))

    if response.status_code == 200:
        graphic_category_json = json.loads(response.text)['response']

        # extract the category value from the json returned by the LMM
        ollama_error_msg = None
        try:
            graphic_category = json.loads(graphic_category_json)['category']
        except json.JSONDecodeError:
            ollama_error_msg = "this does not look like json"
        except KeyError:
            ollama_error_msg = "no category tag found in returned json"
        except TypeError:  # have seen this when we just get a string back
            # TODO: investigate what is actually happening here!
            ollama_error_msg = "unknown error decoding json. investigate!"
        finally:
            if ollama_error_msg is not None:
                logging.pii(
                    f"{ollama_error_msg}. Raw response: \
                    {graphic_category_json}")
                return jsonify("Invalid LLM results"), 204

        # is the found category  one of the ones we require?
        graphic_category = graphic_category.strip().lower()
        if graphic_category in possible_categories.split(", "):
            logging.debug("category: " + graphic_category)
        else:  # llamas are not to be trusted to pay attention to instructions
            logging.error(f"category [{graphic_category}] not a valid option")
            return jsonify("Invalid LLM results"), 204
    else:
        logging.error(f"Error: {response.text}")
        return jsonify("Invalid response from ollama"), 204

    # create data json and verify the content-categoriser schema is respected
    graphic_category_json = {"category": graphic_category}
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(graphic_category_json)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for categorizer response")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    # create full response & check meets overall preprocessor response schema
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": graphic_category_json
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error("Validation failed for final response")
        logging.pii(f"Validation error: {e.message}")
        return jsonify("Invalid Preprocessor JSON format"), 500

    # all done. give final category information and return to orchestrator
    logging.info(graphic_category_json)
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
