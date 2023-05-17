#!/usr/bin/env python3

from flask import Flask, request, jsonify
from utils import translate_helsinki
import time

app = Flask(__name__)

# Validate schema (?)
def validate_schema():
    pass

# Validate request 
def validate_request():
    '''
    Validate incoming request:
    - segment: the text to translate
    - src_lang (defaulted to be 'en'): the source language
    - tgt_lang (defaulted to be 'fr'): the target language
    A request must have at least `segment`.
    ''' 
    return True

@app.route('/service/translate/french', methods=['POST'])
def translate_request():
    '''
    Translate text from one language to another
    '''
    # Get request data
    content = request.get_json()
    print(content)

    # Validate incoming request
    if not validate_request():
        return jsonify("Invalid Request JSON format"), 400

    # Get text to translate
    # request_uuid = content['request_uuid'] # NOT IMPLEMENTED
    segment:list = content['segment']
    # source = content['src_lang'] # NOT IMPLEMENTED
    # target = content['tgt_lang'] # NOT IMPLEMENTED

    # Translate, from list to list
    translation, elapsed_time = translate_helsinki(segment)

    # Prepare response
    response = {
        # "request_uuid": content["request_uuid"],
        "timestamp": int(time.time()),
        "translations": [
            {
                "translation": translation,
                "elapsed_time_in_seconds": elapsed_time
                # "src_lang": source,
                # "tgt_lang": target
            }
        ]
    }

    # Return response
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)    