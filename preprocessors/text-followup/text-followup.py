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

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


@app.route("/preprocessor", methods=['POST', ])
def followup():
    logging.debug("Received request")

    # load the schemas and verify incoming data
    with open('./schemas/preprocessors/text-followup.schema.json') \
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
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 400

    # check we received a graphic (e.g., not a map or chart request)
    if "graphic" not in content:
        logging.info("Request is not a graphic. Skipping...")
        return "", 204  # No content

    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.text-followup"

    # debugging this preprocessor is really difficult without seeing what
    # ollama is returning, but this can contain PII. Until we have a safe
    # way of logging PII, using manually set LOG_PII env variable
    # to say whether or not we should go ahead and log potential PII
    log_pii = os.getenv('LOG_PII', "false").lower() == "true"
    if log_pii:
        logging.warning("LOG_PII is True: potential PII will be logged!")

    # convert the uri to processable image
    # source.split code referred from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = content["graphic"]
    graphic_b64 = source.split(",")[1]

    # TODO: crop graphic if the user has specified a region of interest
    # TODO: add previous request history before new prompt

    # default prompt, which can be overriden by env var just after
    general_prompt = ("""
              I am blind so I cannot see this image.
              Answer in a single JSON object containing two keys.
              The first key is "response_brief" and is a single sentence
              that can stand on its own that directly answers the specific
              request at the end of this prompt.
              The second key is "response_full" and provides maximum
              three sentences of additional detail,
              without repeating the information in the first key.
              If there is no more detail you can provide,
              omit the second key instead of having an empty key.
              Remember to answer only in JSON, or I will be very angry!
              Do not put anything before or after the JSON,
              and make sure the entire response is only a single JSON block,
              with both keys in the same JSON object.
              Here is an example of the output JSON in the format you
              are REQUIRED to follow:
              {
                "response_brief": "One sentence response to the user request",
                "response_full": "Further details."
              }
              Note that the first character of output MUST be "{".
              Remove all whitespace before and after the JSON.
              Here is my request:
              """)
    # override with prompt from environment variable only if it exists
    general_prompt = os.getenv('TEXT_FOLLOWUP_PROMPT_OVERRIDE', general_prompt)
    user_prompt = content["followup"]["query"]
    prompt = general_prompt + ' ' + user_prompt
    if log_pii:
        logging.debug("user followup prompt: " + prompt)
    else:
        logging.debug("user followup prompt: {general_prompt} [redacted]")

    # prepare ollama request
    api_url = os.environ['OLLAMA_URL']
    api_key = os.environ['OLLAMA_API_KEY']
    ollama_model = os.environ['OLLAMA_MODEL']

    logging.debug("OLLAMA_URL " + api_url)
    if api_key.startswith("sk-"):
        logging.debug("OLLAMA_API_KEY looks properly formatted: " +
                      "sk-[redacted]")
    else:
        logging.warning("OLLAMA_API_KEY does not start with sk-")

    request_data = {
        "model": ollama_model,
        "prompt": prompt,
        "images": [graphic_b64],
        "stream": False,
        "temperature": 0.0,
        "format": "json",
        "keep_alive": -1  # keep model loaded in memory indefinitely
    }
    logging.debug("serializing json from request_data dictionary")
    request_data_json = json.dumps(request_data)

    request_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    logging.debug("Posting request to ollama model " + ollama_model)
    response = requests.post(api_url, headers=request_headers,
                             data=request_data_json)
    logging.debug("ollama request response code: " + str(response.status_code))

    if response.status_code == 200:
        ollama_error_msg = None
        try:
            # strip() at end since llama often puts a newline before json
            followup_response_text = json.loads(response.text)['response'].strip()
            if log_pii:
                logging.debug("raw ollama response: " + followup_response_text)
            followup_response_json = json.loads(followup_response_text)
        except json.JSONDecodeError:
            ollama_error_msg = "raw response does not look like json"
        except KeyError:
            ollama_error_msg = "no response tag found in returned json"
        except TypeError:  # have seen this when we just get a string back
            # TODO: investigate what is actually happening here!
            ollama_error_msg = "unknown error decoding json. investigate!"
        finally:
            if ollama_error_msg is not None:
                logging.error(ollama_error_msg + " returning 204")
                return jsonify("Invalid LLM results"), 204
    else:
        if log_pii:
            logging.error("Error {response.status_code}: {response.text}")
        else:
            logging.error("Error {response.status_code}: "
                          "[response text redacted]")
        return jsonify("Invalid response from ollama"), 204

    # check if ollama returned valid json that follows schema
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(followup_response_json)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(f"JSON schema validation fail: {e.validator} {e.schema}")
        if log_pii:
            logging.debug(e)
        return jsonify("Invalid Preprocessor JSON format"), 500

    # create full response & check meets overall preprocessor response schema
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": followup_response_json
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(f"JSON schema validation fail: {e.validator} {e.schema}")
        if log_pii:
            logging.debug(e)  # print full error only in debug, due to PII
        return jsonify("Invalid Preprocessor JSON format"), 500

    # all done; return to orchestrator
    logging.debug("full response length: " + str(len(response)))
    if log_pii:
        logging.debug(response)

    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    followup()
