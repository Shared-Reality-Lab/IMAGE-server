import base64
import json
import jsonschema
import logging
import numpy as np
import soundfile as sf
from espnet_util import tts, fs
from flask import Flask, Response, request
from io import BytesIO
from jsonschema import validate
from werkzeug.wsgi import FileWrapper

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

with open("segment.request.json", "r") as f:
    segment_request = json.load(f)

with open("segment.response.json", "r") as f:
    segment_response = json.load(f)

app = Flask(__name__)

@app.route("/service/default-tts", methods=["POST"])
def perform_tts():
    data = request.get_json()
    if data is None or "text" not in data:
        return { "error": "Missing key \"text\"." }, 400
    elif not isinstance(data["text"], str):
        return { "error": "Key \"text\" must be of type string." }, 400
    text = data["text"]
    try:
        wav = tts(text)
        f = BytesIO()
        sf.write(f, wav, fs, format="WAV")
        f.seek(0)
        wrapper = FileWrapper(f)
        return Response(wrapper, mimetype="audio/wave", direct_passthrough=True)
    except Exception as e:
        logger.error(e)
        return { "error": "An error occurred while performing text-to-speech" }, 500

@app.route("/service/segment-tts", methods=["POST"])
def segment_tts():
    data = request.get_json()

    # Validate request
    try:
        validate(instance=data, schema=segment_request)
    except jsonschema.exceptions.ValidationError as e:
        logger.error(e)
        return { "error": e.message }, 400

    # TTS
    try:
        totalWav = None
        durations = []
        for segment in data["segments"]:
            wav = tts(segment)
            if totalWav is not None:
                totalWav = np.append(totalWav, wav)
            else:
                totalWav = wav
            durations.append((len(wav) * 1000) // fs)

        logger.debug("Done performing TTS")

        f = BytesIO()
        sf.write(f, totalWav, fs, format="WAV")
        encoded = base64.b64encode(f.getvalue()).decode()
        logger.debug("Encoded")

        response = {
            "audio": "data:audio/wave;base64," + encoded,
            "durations": durations
        }

        validate(response, segment_response)
        return response
    except Exception as e:
        logger.error(e)
        return { "error": "An error occurred while performing text-to-speech" }, 500
