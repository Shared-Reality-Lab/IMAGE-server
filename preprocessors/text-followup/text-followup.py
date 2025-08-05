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
import html
from datetime import datetime
from config.logging_utils import configure_logging
from openai import OpenAI

app = Flask(__name__)

configure_logging()

# Dictionary to store conversation history by request_uuid
# Maintains conversation context between requests
conversation_history = {}

# Configuration for history management
# Max messages to keep (including user and model messages)
MAX_HISTORY_LENGTH = int(os.getenv('MAX_HISTORY_LENGTH', '100'))
# History expiry in seconds after the last message
HISTORY_EXPIRY = int(os.getenv('HISTORY_EXPIRY', '3600'))


# Function to clean up old conversation histories
@app.route("/cleanup", methods=["GET"])
def cleanup_old_histories():
    """
    Remove conversation histories that are older than HISTORY_EXPIRY seconds
    """
    current_time = time.time()
    uuids_to_remove = []

    for uuid, history in conversation_history.items():
        if current_time - history.get('last_updated', 0) > HISTORY_EXPIRY:
            uuids_to_remove.append(uuid)

    for uuid in uuids_to_remove:
        del conversation_history[uuid]

    if uuids_to_remove:
        logging.debug(
            f"Cleaned up {len(uuids_to_remove)} old conversation histories"
        )

    return {"status": "success", "removed": len(uuids_to_remove)}, 200


@app.route("/preprocessor", methods=['POST'])
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
        logging.error("Validation failed for incoming request")
        logging.pii(f"Validation error: {e.message} | Data: {content}")
        return jsonify("Invalid Preprocessor JSON format"), 400

    # check we received a graphic (e.g., not a map or chart request)
    if "graphic" not in content:
        logging.info("Request is not a graphic. Skipping...")
        return "", 204  # No content

    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.text-followup"

    # Clean up history based on defined expiry time
    cleanup_old_histories()

    # History status log
    conversation_count = len(conversation_history)
    logging.debug(
        f"Current history status: {conversation_count} conversations stored"
    )

    # Check if this uuid exists in history
    uuid_exists = request_uuid in conversation_history
    logging.debug(
        f"Request UUID {request_uuid} exists in history: {uuid_exists}"
    )
    if uuid_exists:
        msg_count = len(conversation_history[request_uuid]["messages"])
        logging.debug(
            f"Current history length for {request_uuid}: {msg_count}"
            )

    # convert the uri to processable image
    # source.split code referred from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    source = content["graphic"]
    graphic_b64 = source.split(",")[1]

    # TODO: crop graphic if the user has specified a region of interest
    # TODO: add previous request history before new prompt

    # default prompt, which can be overriden by env var just after
    general_prompt = """
              The user cannot see this image. Answer user's question about it.
              Answer in a single JSON object containing two keys.
              The first key is "response_brief" and its value is a single
              sentence that can stand on its own. It directly answers the
              specific request at the end of this prompt.
              The second key is "response_full" and its value provides maximum
              three sentences of additional detail,
              without repeating the information in the first key.
              If there is no more detail you can provide,
              omit the "response_full" key instead of having an empty key.
              IMPORTANT: answer only in JSON.
              Do not put anything before or after the JSON,
              and make sure the entire response is only a single JSON block,
              with both keys in the same JSON object.
              Here is an example of the output JSON in the format you
              are REQUIRED to follow:
              {
              "response_brief": "One sentence response to the user request.",
              "response_full": "Further details. Maximum three sentences."
              }
              Note that the first character of output MUST be "{".
              Remove all whitespace before and after the JSON.
              """
    # override with prompt from environment variable only if it exists
    general_prompt = os.getenv('TEXT_FOLLOWUP_PROMPT_OVERRIDE', general_prompt)
    user_prompt = content["followup"]["query"]

    # prepare vllm request
    vllm_base_url = os.environ['VLLM_URL']
    api_key = os.environ['VLLM_API_KEY']
    vllm_model = os.environ['VLLM_MODEL']

    logging.debug("VLLM_URL " + vllm_base_url)
    logging.debug("VLLM_MODEL " + vllm_model)
    if api_key.startswith("sk-"):
        logging.pii("VLLM_API_KEY looks properly formatted: sk-[redacted]")
    else:
        logging.warning("VLLM_API_KEY does not start with sk-")

    # Initialize OpenAI client with custom base URL for vllm
    client = OpenAI(
        api_key=api_key,
        base_url=vllm_base_url
    )

    system_message = {"role": "system", "content": general_prompt}

    # Retrieve existing conversation history or create new one
    if uuid_exists:
        # For follow-up messages, add the new user prompt
        user_message = {
            "role": "user",
            "content": user_prompt
        }
        conversation_history[request_uuid]['messages'].append(user_message)
        conversation_history[request_uuid]['last_updated'] = timestamp
    else:
        # For the first message, create a new history entry
        # include the system prompt, the user's text, and the image
        user_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{graphic_b64}"
                    }
                }
            ]
        }

        conversation_history[request_uuid] = {
            'messages': [system_message, user_message],
            'last_updated': timestamp
        }

    # Use history for the request
    uuid_messages = conversation_history[request_uuid]["messages"]

    if len(uuid_messages) <= MAX_HISTORY_LENGTH:
        messages = uuid_messages
    else:
        # Get system message, first user message w/ image, and recent messages
        messages = (
            uuid_messages[:2] +
            uuid_messages[-(MAX_HISTORY_LENGTH-2):]
        )

    # Create log-friendly version without full base64 content
    log_friendly_messages = []
    for msg in messages:
        # Create a copy to avoid modifying the original
        log_msg = msg.copy()
        if isinstance(msg.get('content'), list):
            # Handle multi-part content (text + image)
            log_content = []
            for part in msg['content']:
                if part['type'] == 'image_url':
                    log_content.append({
                        'type': 'image_url',
                        'image_url': {'url': '[BASE64_IMAGE]'}
                    })
                else:
                    log_content.append(part)
            log_msg['content'] = log_content
        log_friendly_messages.append(log_msg)

    logging.pii(
        f"Message history: {json.dumps(log_friendly_messages, indent=2)}"
        )
    logging.debug(f"User followup prompt: {general_prompt} [redacted]")

    # Create request data for chat endpoint
    try:
        logging.debug("Posting request to vllm model " + vllm_model)

        from pydantic import BaseModel, Field

        class ResponseModel(BaseModel):
            response_brief: str = Field(
                ...,
                description="One sentence response to the user request."
            )
            response_full: str = Field(
                ...,
                description="Further details. Maximum three sentences."
            )
        json_schema = ResponseModel.model_json_schema()

        # Make the request using OpenAI client
        response = client.chat.completions.create(
            model=vllm_model,
            messages=messages,
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
        logging.debug("vllm request response code: 200")

        try:
            # Get the response content
            response_text = response.choices[0].message.content.strip()
            logging.pii("raw vllm response: " + response_text)
            followup_response_json = json.loads(response_text)

            # Format assistant response for history
            model_resp = {
                "role": "assistant",
                "content": html.unescape(response_text)
            }

            # Update conversation history
            conversation_history[request_uuid]["messages"].append(model_resp)
            conversation_history[request_uuid]["last_updated"] = timestamp

            # Add debug logging
            status = 'updated' if uuid_exists else 'created'
            logging.debug(
                f"Conversation history status: UUID {request_uuid} {status}"
            )
            logging.debug(
                f"History contains {len(conversation_history)} conversations"
                )

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
        logging.error(f"Error calling vllm: {str(e)}")
        return jsonify("Invalid response from vllm"), 204

    # check if LLM returned valid json that follows schema
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(followup_response_json)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(f"JSON schema validation fail: {e.validator} {e.schema}")
        logging.pii(e)
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
        logging.pii(e)
        return jsonify("Invalid Preprocessor JSON format"), 500

    logging.debug("full response length: " + str(len(response)))
    logging.pii(response)
    return jsonify(response)


# Two following endpoints don't have immediate use
# They are implemented in case we need to extend functionality later
# They are tested and fully functional
# New endpoint to clear history for a specific request_uuid
@app.route("/clear-history/<request_uuid>", methods=["GET"])
def clear_history(request_uuid):
    """
    Clear conversation history for a specific request_uuid
    """
    uuid_exists = request_uuid in conversation_history
    logging.info(f"Request to clear history for {request_uuid}")
    logging.info(
        f"Before clearing: {len(conversation_history)} conversations in memory"
    )
    logging.info(f"UUID exists in history: {uuid_exists}")

    if uuid_exists:
        del conversation_history[request_uuid]
        logging.info(
            f"After clearing: {len(conversation_history)} conversations"
            )
        return jsonify({
            "status": "success",
            "message": f"History for {request_uuid} cleared"
        }), 200
    else:
        logging.info("UUID not found in history")
        return jsonify({
            "status": "not_found",
            "message": f"No history found for {request_uuid}"
        }), 404


# New endpoint to get conversation statistics
@app.route("/history-stats", methods=["GET"])
def history_stats():
    """
    Get statistics about stored conversation histories
    """
    history_data = conversation_history.values()
    return (
        jsonify(
            {
                "active_conversations": len(conversation_history),
                "oldest_conversation": (
                    min([h["last_updated"] for h in history_data])
                    if conversation_history
                    else None
                ),
                "newest_conversation": (
                    max([h["last_updated"] for h in history_data])
                    if conversation_history
                    else None
                ),
            }
        ),
        200,
    )


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
    """
    try:
        # construct the target Ollama endpoint for generate
        api_url = f"{os.environ['OLLAMA_URL']}/generate"

        # authorization headers with API key
        headers = {
            "Authorization": f"Bearer {os.environ['OLLAMA_API_KEY']}",
            "Content-Type": "application/json"
        }

        # prepare the warmup request data using the configured model
        data = {
            "model": os.environ["OLLAMA_MODEL"],
            "prompt": "ping",
            "stream": False,
            "keep_alive": -1  # instruct Ollama to keep the model in memory
        }

        logging.info("[WARMUP] Warmup endpoint triggered.")
        logging.pii(f"[WARMUP] Posting to {api_url} with model \
                    {data['model']}")

        # send warmup request (with timeout)
        r = requests.post(api_url, headers=headers, json=data, timeout=60)
        r.raise_for_status()

        return jsonify({"status": "warmed"}), 200

    except Exception as e:
        logging.exception(f"[WARMUP] Exception details: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
