#!/usr/bin/env python3

from flask import Flask, request, jsonify
from .utils import translate_helsinki, LOGGER
import logging
import json
import jsonschema

app = Flask(__name__)

# Load schema
"""
(Check the Dockerfile)
Here we send the app to / directory, along with the schema file.
Hence, we can load the schema file as below. (relative path)
"""

# uncomment this line to test the server locally (without Docker)
# with open("../../schemas/services/translation.schema.json", "r") as f:
with open("translation.schema.json", "r") as f:
    TRANSLATION_SCHEMA = json.load(f)

# Validate request


def validate_request(request):
    """
    Validate incoming request:
    - segment: the text to translate
    - src_lang (defaulted to be 'en'): the source language
    - tgt_lang (defaulted to be 'fr'): the target language
    A request must have at least `segment`.
    """
    try:
        jsonschema.validate(instance=request, schema=TRANSLATION_SCHEMA)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return False


@app.route("/service/translate/french", methods=["POST"])
def translate_request():
    """
    Translate text from one language to another
    """
    # Get request data
    content = request.get_json()
    # print(content)

    # Validate incoming request
    if not validate_request(request=content):
        return jsonify("Invalid Request JSON format"), 400

    LOGGER.debug("- Request validated! -")

    # Get text to translate
    segments: list = content["segments"]
    source_lang = content["src_lang"]
    target_lang = content["tgt_lang"]

    # Handles source/target language

    # Translate, from list to list
    translation, elapsed_time = translate_helsinki(segments)

    # Prepare response
    response = {
        "src_lang": source_lang,
        "tgt_lang": target_lang,
        "elapsed_time_in_seconds": elapsed_time,
        "translations": translation,
    }
    LOGGER.debug("- Response SENT! -")
    # Return response
    return jsonify(response), 200
