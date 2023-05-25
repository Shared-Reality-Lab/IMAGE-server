#!/usr/bin/env python3

from flask import Flask, request, jsonify
from .utils import instantiate, translate_helsinki
import time, logging, json, jsonschema
app = Flask(__name__)

# Load schema
'''
(Check the Dockerfile)
Here we send the app to / directory, along with the schema file.
Hence, we can load the schema file as below. (relative path)
'''
with open("../../schemas/services/translation.schema.json", "r") as f:
# with open("translation.schema.json", "r") as f:
    translation_schema = json.load(f)

# Validate request 
def validate_request(request):
    '''
    Validate incoming request:
    - segment: the text to translate
    - src_lang (defaulted to be 'en'): the source language
    - tgt_lang (defaulted to be 'fr'): the target language
    A request must have at least `segment`.
    '''
    try:
        jsonschema.validate(instance=request, schema=translation_schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return False

@app.route('/service/translate/french', methods=['POST'])
def translate_request():
    '''
    Translate text from one language to another
    '''
    # Get request data
    request = request.get_json()
    print(request)

    # Validate incoming request
    if not validate_request():
        return jsonify("Invalid Request JSON format"), 400
    logging.debug("-- Request validated! --")
    # Get text to translate
    segment:list = request['segment']
    source_lang = request['src_lang']
    target_lang = request['tgt_lang']

    # Translate, from list to list
    translation, elapsed_time = translate_helsinki(segment)

    # Prepare response
    response = {
        "timestamp": int(time.time()),
        "translations": [
            {
                "src_lang": source_lang,
                "tgt_lang": target_lang,
                "translation": translation,
                "elapsed_time_in_seconds": elapsed_time
            }
        ]
    }

    # Return response
    return jsonify(response), 200

if __name__ == '__main__':
    instantiate()
    app.run(host='0.0.0.0', port=5000, debug=True)    
