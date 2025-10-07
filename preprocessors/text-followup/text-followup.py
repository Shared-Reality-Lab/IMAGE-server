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
import json
import time
import logging
import os
import sys
import html
from datetime import datetime
from config.logging_utils import configure_logging
from utils.llm import (
    LLMClient,
    FOLLOWUP_PROMPT,
    FOLLOWUP_PROMPT_FOCUS
    )
from utils.validation import Validator
import base64
from io import BytesIO
from PIL import Image, ImageDraw

app = Flask(__name__)

configure_logging()

DATA_SCHEMA = './schemas/preprocessors/text-followup.schema.json'
with open(DATA_SCHEMA, 'r') as f:
    FOLLOWUP_RESPONSE_SCHEMA = json.load(f)

PREPROCESSOR_NAME = "ca.mcgill.a11y.image.preprocessor.text-followup"

try:
    llm_client = LLMClient()
    validator = Validator(data_schema=DATA_SCHEMA)
    logging.debug("LLM client and validator initialized")
except Exception as e:
    logging.error(f"Failed to initialize clients: {e}")
    sys.exit(1)

# Dictionary to store conversation history by request_uuid
# Maintains conversation context between requests
conversation_history = {}

# Configuration for history management
# Max messages to keep (including user and model messages)
MAX_HISTORY_LENGTH = int(os.getenv('MAX_HISTORY_LENGTH', '100'))
# History expiry in seconds after the last message
HISTORY_EXPIRY = int(os.getenv('HISTORY_EXPIRY', '3600'))


def draw_rectangle(
    base64_image, focus_coords, rectangle_color="red", line_width=3
):
    """
    Draw a rectangle on a base-64 encoded image based on normalized
    coordinates.

    Args:
        base64_image (str): Base-64 encoded image string.
        focus_coords (list): Normalized coordinates [x1, y1, x2, y2]
        where values are 0-1.
        rectangle_color (str): Color of the rectangle (default: "red").
        line_width (int): Width of the rectangle outline (default: 3).

    Returns:
        str: Base-64 encoded image with rectangle drawn
    """

    # Decode the base-64 image
    image_data = base64.b64decode(base64_image)
    image = Image.open(BytesIO(image_data))

    # Get image dimensions
    width, height = image.size

    # Convert normalized coordinates to pixel coordinates
    x1 = int(focus_coords[0] * width)
    y1 = int(focus_coords[1] * height)
    x2 = int(focus_coords[2] * width)
    y2 = int(focus_coords[3] * height)

    # Ensure coordinates are within image bounds
    x1 = max(0, min(x1, width))
    y1 = max(0, min(y1, height))
    x2 = max(0, min(x2, width))
    y2 = max(0, min(y2, height))

    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Draw rectangle outline
    draw.rectangle(
        [x1, y1, x2, y2],
        outline=rectangle_color,
        width=line_width
    )

    # Convert image back to base-64
    buffer = BytesIO()

    # Preserve original format if possible, otherwise use PNG
    image_format = image.format if image.format else 'PNG'
    image.save(buffer, format=image_format)

    # Encode to base-64
    encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return encoded_image


def create_text_message(text):
    """Create a simple text message."""
    return {
        "role": "user",
        "content": text
    }


def create_multimodal_message(text, graphic_b64):
    """Create a message with text and image."""
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{graphic_b64}"}
            }
        ]
    }


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

    # load the content and verify incoming data
    content = request.get_json()

    ok, _ = validator.check_request(content)
    if not ok:
        return jsonify({"error": "Invalid Preprocessor JSON format"}), 400

    # check we received a graphic (e.g., not a map or chart request)
    if "graphic" not in content:
        logging.info("Request is not a graphic. Skipping...")
        return "", 204  # No content

    request_uuid = content["request_uuid"]
    timestamp = time.time()

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

    user_prompt = content["followup"]["query"]

    logging.pii(f'Full followup: {content["followup"]}')

    # if focus area is in the query, we replace the original graphic
    # with the graphic with the focus area highlighted in red rectangle
    if (
        "focus" in content["followup"]
        and len(content["followup"]["focus"]) == 4
    ):
        focus = content["followup"]["focus"]
        logging.info(f"Focus area provided: {focus}")
    else:
        focus = None
        logging.info("No focus area provided")

    if focus:
        try:
            graphic_b64 = draw_rectangle(
                base64_image=graphic_b64,
                focus_coords=focus,
                rectangle_color="red",
                line_width=3
            )
            logging.info("Drew rectangle on image based on focus area")
        except ValueError as e:
            logging.error(f"Error drawing rectangle: {str(e)}")
            return jsonify(
                {"error": "Failed to process focus area on image"}
            ), 500

    if not focus:
        system_prompt = FOLLOWUP_PROMPT
    else:
        system_prompt = FOLLOWUP_PROMPT + FOLLOWUP_PROMPT_FOCUS

    system_message = {
        "role": "developer",
        "content": system_prompt
        }

    if not uuid_exists:
        # For the first message, create a new history entry
        # include the system prompt, the user's text, and the image

        user_message = create_multimodal_message(user_prompt, graphic_b64)

        conversation_history[request_uuid] = {
            'messages': [system_message, user_message],
            'last_updated': timestamp,
            'focus': focus if focus else None
        }

    elif (
        uuid_exists
        and focus == conversation_history[request_uuid].get('focus')
    ):
        # existing uuid and same focus: add user message to history
        user_message = create_text_message(user_prompt)

        conversation_history[request_uuid]['messages'].append(user_message)
        conversation_history[request_uuid]['last_updated'] = timestamp

    else:
        # existing uuid but different focus: add new message with new graphic
        user_message = create_multimodal_message(
            user_prompt + FOLLOWUP_PROMPT_FOCUS,
            graphic_b64
        )

        conversation_history[request_uuid]['messages'].append(user_message)
        conversation_history[request_uuid]['last_updated'] = timestamp
        conversation_history[request_uuid]['focus'] = focus

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

    followup_response_json = llm_client.chat_completion(
        prompt="",  # Empty since we're using full messages via kwargs
        json_schema=FOLLOWUP_RESPONSE_SCHEMA,
        temperature=0.0,
        messages=messages,  # Pass full conversation history via kwargs
        parse_json=True
        )

    if followup_response_json is None:
        logging.error("Failed to receive response from LLM.")
        return jsonify(
            {"error": "Failed to get graphic caption from LLM"}
        ), 500

    response_text = json.dumps(followup_response_json)

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

    # check if LLM returned valid json that follows schema
    # validate data
    ok, _ = validator.check_data(followup_response_json)
    if not ok:
        return jsonify("Invalid Preprocessor JSON format"), 500

    # create full response & check meets overall preprocessor response schema
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": PREPROCESSOR_NAME,
        "data": followup_response_json
    }

    ok, _ = validator.check_response(response)
    if not ok:
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
