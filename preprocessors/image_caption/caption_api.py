import replicate
import time
import cv2
import base64
import numpy as np
from flask import Flask, request
import time
import logging
from io import BytesIO, BufferedReader

app = Flask(__name__)
logging.basicConfig(level=logging.NOTSET)

@app.route("/preprocessor", methods=['POST', 'GET'])
def readImage():
    content = request.get_json()
    image_b64 = content["graphic"].split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    pil_image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    img_original = np.array(pil_image)
    height, width, channels = img_original.shape
    ret, img_encode = cv2.imencode('.jpg', img_original)
    str_encode = img_encode.tostring()
    img_byteio = BytesIO(str_encode)
    img_byteio.name = 'img.jpg'
    reader = BufferedReader(img_byteio)
    output = replicate.run(
    "j-min/clip-caption-reward:de37751f75135f7ebbe62548e27d6740d5155dfefdf6447db35c9865253d7e06",
    input={"image": reader})
    data = {
        "caption":output
    }
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.captionGeneration"
    data = {"data":data}
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": data
    }
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)