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
from flask import Flask, Response, request, jsonify
from io import BytesIO
from jsonschema import validate
from torch.cuda import empty_cache
from werkzeug.wsgi import FileWrapper
from num2words import num2words
import re  # for regular expression processing

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define regular expression (regex)
numRegex = r'\d+(?:[,.]\d+)?'
rangeRegex = r'\d+(?:[,.]\d+)?\s*-\s*\d+(?:[,.]\d+)?'

with open("segment.request.json", "r") as f:
    segment_request = json.load(f)

with open("segment.response.json", "r") as f:
    segment_response = json.load(f)

app = Flask(__name__)


def frenchNum(num):
    '''
    Convert numeric number to French words
    - @param: `num` - could be str or int type
    - The function can also process `,` separated numbers
    '''
    commaSeparateRegex = re.compile(r'\d+\,\d+')
    if commaSeparateRegex.search(num):
        num = num.replace(",", ".")
    return num2words(num, lang='fr')


def processRange(match):
    '''
    Processing a number range (having a hyphen as a separator)
    Cases: age, year, statistic ranges
    E.g.: 12-24, 12,56 - 25,67
    '''
    phrase = match.group()
    numRange = re.findall(numRegex, phrase)  # num range will have 2 elements
    if len(numRange) != 2:
        logger.debug(
            f"Error: processing range, but having {len(numRange)} numbers")
        return
    return f"de {frenchNum(numRange[0])} à {frenchNum(numRange[1])}"


def processSegment(s):
    if re.match(rangeRegex, s):
        # If the match is a range type
        return re.sub(rangeRegex, processRange, s)
    elif re.match(numRegex, s):
        # If the match is a standalone number
        return frenchNum(s)
    else:
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
            for s in segment.split():
                try:
                    segment_new.append(processSegment(s))
                except Exception as e:
                    # logger.error(f"ERROR processing {s}")
                    logger.error(e)
                    segment_new.append(s)

            segment_new = " ".join(str(s) for s in segment_new)
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


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify if the service is running
    """
    return jsonify({"status": "healthy", "timestamp": request.date}), 200
