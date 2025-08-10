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

import html
from flask import Flask, request, jsonify
import json
import time
import jsonschema
import logging
import os
from datetime import datetime
from config.logging_utils import configure_logging
from openai import OpenAI
from pydantic import BaseModel, Field
from enum import Enum

configure_logging()

app = Flask(__name__)


# Define the response model schema
class CategoryType(str, Enum):
    PHOTOGRAPH = "photograph"
    CHART = "chart"
    TEXT = "text"
    OTHER = "other"


class ResponseModel(BaseModel):
    category: CategoryType = Field(
        ...,
        description="The type of content being categorized"
    )


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

    # prepare llm request
    llm_base_url = os.environ['LLM_URL']
    api_key = os.environ['LLM_API_KEY']
    llm_model = os.environ['LLM_MODEL']

    logging.debug(f"LLM URL: {llm_base_url}")
    logging.debug(f"LLM MODEL: {llm_model}")
    if api_key.startswith("sk-"):
        logging.pii("LLM_API_KEY looks properly formatted: sk-[redacted]")
    else:
        logging.warning("LLM_API_KEY does not start with sk-")

    prompt = "Answer only in JSON with the format " \
             '{"category": "YOUR_ANSWER"}. ' \
             "Which of the following categories best " \
             "describes this image, selecting from this enum: "
    possible_categories = "photograph, chart, text, other"
    # override with prompt from environment variable only if it exists
    prompt = os.getenv('CONTENT_CATEGORISER_PROMPT_OVERRIDE', prompt)

    # Initialize OpenAI client with custom base URL for LLM
    client = OpenAI(
        api_key=api_key,
        base_url=llm_base_url
    )

    try:
        logging.debug("Posting request to LLM model: " + llm_model)

        json_schema = ResponseModel.model_json_schema()

        # Make the request using OpenAI client
        response = client.chat.completions.create(
            model=llm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + possible_categories},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{graphic_b64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.0,
            stream=False,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "response-format",
                    "schema": json_schema
                },
            }
        )

        # The OpenAI library handles status codes internally
        # A successful response means status code was 200
        logging.debug("LLM request response code: 200")

        try:
            # Get the response content
            response_text = html.unescape(response.choices[0].message.content)
            graphic_category_json = response_text.strip().lower()
            graphic_category = json.loads(graphic_category_json)['category']
            if graphic_category in possible_categories.split(", "):
                logging.debug("category: " + graphic_category)
            # LLMs are not to be trusted to pay attention to instructions
            else:
                logging.error(f"'{graphic_category}' not a valid category")
                return jsonify("Invalid LLM results"), 204

        except json.JSONDecodeError:
            logging.error("raw response does not look like json")
            return jsonify("Invalid LLM results"), 204
        except (KeyError, AttributeError):
            logging.error("no response content found in returned object")
            return jsonify("Invalid LLM results"), 204
        except TypeError:
            logging.error("unknown error decoding json, returning 204")
            return jsonify("Invalid LLM results"), 204

    except Exception as e:
        logging.error(f"Error calling LLM: {str(e)}")
        return jsonify("Invalid response from LLM"), 204

    logging.pii(f"Graphic category JSON: {graphic_category}")
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
    Trigger a warmup call to load the Ollama LLM into memory.
    This avoids first-request latency by sending a dummy request.
    vLLM keeps the model in memory after the container startup.
    """
    try:
        llm_base_url = os.environ['LLM_URL']
        api_key = os.environ['LLM_API_KEY']
        llm_model = os.environ['LLM_MODEL']

        # Initialize OpenAI client with custom base URL for vllm
        client = OpenAI(
            api_key=api_key,
            base_url=llm_base_url,
            timeout=60.0
        )

        logging.debug("Posting request to LLM model: " + llm_model)

        # Make the request using OpenAI client
        client.chat.completions.create(
            model=llm_model,
            messages=[
                {
                    "role": "user",
                    "content": "ping"
                }
            ],
            temperature=0.0,
            stream=False
        )

        logging.info("[WARMUP] Warmup endpoint triggered.")
        logging.pii(f"[WARMUP] Posting to {llm_base_url} with model \
                    {llm_model}")

        return jsonify({"status": "warmed"}), 200

    except Exception as e:
        logging.exception(f"[WARMUP] Exception details: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
