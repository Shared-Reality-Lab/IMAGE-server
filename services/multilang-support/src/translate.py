#!/usr/bin/env python3

from flask import Flask, request, jsonify
from .utils import translate_helsinki, LOGGER
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
    - segments (required): a list/array of strings to translate
    - src_lang (optional, default: 'en'): the source language
    - tgt_lang (required): the target language
    A request must have at least `segment`.
    """
    try:
        jsonschema.validate(instance=request, schema=TRANSLATION_SCHEMA)
        return True
    except jsonschema.exceptions.ValidationError as e:
        LOGGER.error(f'Schema ValidationError: {e.message}')
        return False


@app.route("/service/translate", methods=["POST"])
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
    # source lang is optional, hence the try/except
    try:
        source_lang = content["src_lang"]
    except KeyError:
        source_lang = "en"

    target_lang = content["tgt_lang"]

    # Handles source/target language
    if target_lang == source_lang:
        LOGGER.error("Source and target languages are the same")
        return jsonify("Source and target languages are the same"), 204
    if target_lang not in ["fr", "en"]:
        LOGGER.error("Target language is not yet implemented")
        return jsonify("Target language not implemented"), 501
    if source_lang == 'en' and target_lang == 'fr':
        # Translate, from list to list
        translation, elapsed_time = translate_helsinki(segments)
    else:
        LOGGER.error("Service Error, unable to handle")
        return jsonify("Service Error"), 500
    # Prepare response
    response = {
        "src_lang": source_lang,
        "tgt_lang": target_lang,
        "translations": translation,
    }
    LOGGER.debug(f"- Response SENT! Time taken: {elapsed_time}-")
    # Return response
    return jsonify(response), 200
