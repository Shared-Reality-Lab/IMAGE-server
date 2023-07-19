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
from torch.cuda import empty_cache
from werkzeug.wsgi import FileWrapper
from num2words import num2words

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

with open("segment.request.json", "r") as f:
    segment_request = json.load(f)

with open("segment.response.json", "r") as f:
    segment_response = json.load(f)

app = Flask(__name__)


def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


def processSegment(s):
    if s.isdigit() or isfloat(s):
        return num2words(s, lang='fr')
    if "." in s:
        temps = s.replace(".", "")
        if temps.isnumeric():
            temps = int(temps)
            s = num2words(int(temps), lang='fr')
    if "," in s:
        tempns = s.replace(",", ".")
        if isfloat(tempns):
            s = num2words(tempns, lang='fr')
    if "-" in s:
        num_in_ns = s.split("-")
        s = " ".join(["de", num2words(num_in_ns[0], lang='fr'),
                      "à", num2words(num_in_ns[1], lang='fr')])
    return s


@app.route("/service/tts/simple", methods=["POST"])
def perform_tts():
    logger.debug("Received request")
    data = request.get_json()
    if data is None or "text" not in data:
        return {"error": "Missing key \"text\"."}, 400
    elif not isinstance(data["text"], str):
        return {"error": "Key \"text\" must be of type string."}, 400
    text = data["text"]
    try:
        wav = tts(text)
        f = BytesIO()
        sf.write(f, wav, fs, format="WAV")
        f.seek(0)
        wrapper = FileWrapper(f)
        logger.debug("Sending response")
        return Response(wrapper, mimetype="audio/wav", direct_passthrough=True)
    except Exception as e:
        logger.error(e)
        return {
            "error": "An error occurred while performing text-to-speech"
        }, 500
    finally:
        empty_cache()


@app.route("/service/tts/segments", methods=["POST"])
def segment_tts():
    logger.debug("Received request")
    data = request.get_json()

    # Validate request
    try:
        validate(instance=data, schema=segment_request)
    except jsonschema.exceptions.ValidationError as e:
        logger.error(e)
        return {"error": e.message}, 400

    # TTS
    try:
        totalWav = None
        durations = []
        wavs = []
        for segment in data["segments"]:
            # detect numerical in segments
            segment_new = []
            logger.debug(segment.split())
            for s in segment.split():
                logger.debug(f'Performing on: {s}')
                segment_new.append(processSegment(s))
            segment_new = " ".join(segment_new)
            logger.debug(f'New Segment: {segment_new}')
            wavs.append(tts(segment_new))
        for wav in wavs:
            if totalWav is not None:
                totalWav = np.append(totalWav, wav)
            else:
                totalWav = wav
            durations.append(len(wav))

        logger.debug("Done performing TTS")

        f = BytesIO()
        sf.write(f, totalWav, fs, format="WAV")
        encoded = base64.b64encode(f.getvalue()).decode()
        logger.debug("Encoded")

        response = {
            "audio": "data:audio/wav;base64," + encoded,
            "durations": durations
        }

        validate(response, segment_response)
        logger.debug("Sending response")
        return response
    except Exception as e:
        logger.error(e)
        return {
            "error": "An error occurred while performing text-to-speech"
        }, 500
    finally:
        empty_cache()
