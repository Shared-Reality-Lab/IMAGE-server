import logging
import soundfile as sf
from espnet_util import tts, fs
from flask import Flask, Response, request
from io import BytesIO
from werkzeug.wsgi import FileWrapper

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
