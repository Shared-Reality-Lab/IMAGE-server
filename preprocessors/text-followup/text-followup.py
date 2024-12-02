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

    # convert the uri to processable image
    # source.split code referred from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = content["graphic"]

    # TODO: crop graphic if the user has specified a region of interest

    graphic_b64 = source.split(",")[1]

    # TODO: add previous request history before new prompt

    prompt = ("Answer with two paragraphs. "
              "The first paragraph should be a single sentence "
              "that can stand on its own. "
              "The second paragraph should be no more than 3 sentences, "
              "and provide additional detail, without repeating the "
              "information in the first sentence. "
              "If there is no more detail you can provide, say, "
              "\"I don't have any more details.\" instead of saying nothing."
              " Note I am blind so I cannot see this image. " +
              content["followup"]["query"])

    # prepare ollama request
    api_url = os.environ['OLLAMA_URL']
    api_key = os.environ['OLLAMA_API_KEY']
    ollama_model = os.environ['OLLAMA_MODEL']

    logging.debug("OLLAMA_URL " + api_url)
    if api_key.startswith("sk-"):
        logging.debug("OLLAMA_API_KEY looks properly formatted: " +
                      api_key[:3] + "[redacted]")
    else:
        logging.warn("OLLAMA_API_KEY usually starts with sk-, "
                     "but this one starts with: " + api_key[:3])

    request_data = {
        "model": ollama_model,
        "prompt": prompt,
        "images": [graphic_b64],
        "stream": False,
        "temperature": 0.0,
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
        response_text = response.text
        data = json.loads(response_text)

        # break response into two separate fields, brief and full
        followup_response_split = data['response'].split("\n", 1)
        followup_brief = followup_response_split[0]
        if len(followup_response_split) > 1:
            followup_full = followup_response_split[1]
        else:
            followup_full = "No more details."
    else:
        logging.error("Error: {response.text}")
        return jsonify("Invalid response from ollama"), 500

    # create data json and verify the text-followup schema is respected
    followup_response_json = {"response_brief": followup_brief,
                              "response_full":  followup_full}
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(followup_response_json)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(f"JSON schema validation fail: {e.validator} {e.schema}")
        logging.debug(e)  # print full error only in debug, due to PII
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
        logging.debug(e)  # print full error only in debug, due to PII
        return jsonify("Invalid Preprocessor JSON format"), 500

    # all done; return to orchestrator
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    followup()
