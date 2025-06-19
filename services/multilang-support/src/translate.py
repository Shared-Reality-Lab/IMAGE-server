#!/usr/bin/env python3

from flask import Flask, request, jsonify
from .utils import LOGGER, Translator, SUPPORTED_LANGS
import json
import jsonschema
from datetime import datetime

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

    # Validate incoming request
    if not validate_request(request=content):
        return jsonify("Invalid Request JSON format"), 400

    LOGGER.debug("-- Request received & validated! --")

    # Get text to translate
    segments: list = content["segments"]
    # source lang is optional, hence try/except
    try:
        source_lang = content["src_lang"]
    except KeyError:
        LOGGER.debug("Source language not specified, defaulting to 'en'")
        source_lang = "en"

    target_lang = content["tgt_lang"]

    # Handles source/target language
    try:
        if target_lang == source_lang:
            LOGGER.error(
                f'Source and target languages are the same: "{source_lang}"')
            return jsonify("Source and target languages are the same"), 204
        elif target_lang not in SUPPORTED_LANGS:
            LOGGER.error(f'Target "{target_lang}" is not yet implemented')
            return jsonify("Target language not implemented"), 501
        else:
            # Translate the segments using a corresponding translator object
            translation, elapsed_time = Translator\
                .get_translator(source_lang, target_lang)\
                .translate(segments)
    except Exception as e:
        LOGGER.error("Service Error: " + e.message)
        LOGGER.debug(f"Attempted request: '{source_lang}' -> '{target_lang}'")
        LOGGER.debug(f"Attempted segments: {segments}")
        return jsonify("Service Error"), 500
    # Prepare response
    response = {
        "src_lang": source_lang,
        "tgt_lang": target_lang,
        "translations": translation,
    }
    LOGGER.debug(f"- Response SENT! Time taken: {elapsed_time} ms -")
    # Return response
    return jsonify(response), 200


@app.route("/warmup", methods=["GET"])
def warmup():
    """
    Trigger a dummy translation to warm up the Hugging Face model.
    """
    try:
        LOGGER.info("[WARMUP] Warmup endpoint triggered.")

        # Instantiate a dummy translator (e.g., English to French)
        dummy_translator = Translator("en", "fr")
        _ = dummy_translator.translate(
            "Internet Multimodal Access to Graphical Exploration")

        LOGGER.info("[WARMUP] Model warmed successfully.")
        return jsonify({"status": "warmed"}), 200
    except Exception as e:
        LOGGER.exception("[WARMUP] Warmup failed.")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint to verify if the service is running
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200
