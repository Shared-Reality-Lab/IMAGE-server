import logging
import soundfile as sf
from espnet_util import tts, fs
from flask import Flask, Response
from io import BytesIO
from werkzeug.wsgi import FileWrapper

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__)

@app.route("/service/default-tts", methods=["GET"])
def perform_tts():
    default_string = "Penny is a very circular cat."
    try:
        wav = tts(default_string)
        f = BytesIO()
        sf.write(f, wav, fs, format="WAV")
        f.seek(0)
        wrapper = FileWrapper(f)
        return Response(wrapper, mimetype="audio/wave", direct_passthrough=True)
    except Exception as e:
        logger.error(e)
        return { "error": "An error occurred while performing text-to-speech" }, 500
