# Copyright (c) 2022 IMAGE Project, Shared Reality Lab, McGill University
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

import re
import json
import time
import base64
import logging
import warnings
import os, sys
import tempfile
import jsonschema
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify


import nltk
import clipscore
from nltk.tag.stanford import StanfordNERTagger


nltk.download('punkt')
app = Flask(__name__)

# using python's tmp file to store the image and context json
dir_prefix = 'ner_'
CONTEXT_DIR = tempfile.mkdtemp(prefix=dir_prefix)
IMAGE_DIR = tempfile.mkdtemp(prefix=dir_prefix)

# path to the stanford ner models (https://nlp.stanford.edu/software/CRF-NER.shtml)
STANFORD_JAR = '/app/stanford-ner/stanford-ner.jar'
STANFORD_MODEL = '/app/stanford-ner/ner-model-english.ser.gz'


"""
Save a html contaning an image to a given location
:my_html: the html to save
:name: name of the to save
:out_dir: directory to save the image to
"""
def save_image(my_html, name, out_dir):
    path_ = os.path.abspath(f"{out_dir}")
    image_b64 = my_html.split(",")[1]
    binary = base64.b64decode(image_b64)
    with open(f"{path_}/{name}.png","wb") as file:
        file.write(eval(str(binary)))


"""
Given a json from the raw data, this function will extract the alt text
:my_json: json from raw data
"""
def get_alt(my_json):
    context = my_json['context']
    soup = BeautifulSoup(context, 'html.parser')
    alt = soup.find('img', alt=True)['alt']
    return alt


"""
Object to pass parameters to clipscore module
"""
class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

"""
Removes temp dirs created
"""
def remove_dirs():
    try:
        shutil.rmtree(CONTEXT_DIR)
        logging.info(f"Deleted {str(CONTEXT_DIR)}")
    except Exception as e:
        logging.error(e)

    try:
        shutil.rmtree(IMAGE_DIR)
        logging.info(f"Deleted {str(IMAGE_DIR)}")
    except Exception as e:
        logging.error(e)


"""
Function to extarct the NERs from a given english sentence, using the Stanford ner model
:sentence: the sentence to check
:only_ner: the stanford model also tags pos, set the only_ner to only extract the ner tags
"""
def stanford_ner(sentence, only_ner = True):
    # Prepare NER tagger with english model
    ner_tagger = StanfordNERTagger(STANFORD_MODEL, STANFORD_JAR, encoding='utf8')

    # Tokenize: Split sentence into words
    words = nltk.word_tokenize(sentence)

    # Run NER tagger on words
    words =  ner_tagger.tag(words)
    
    if only_ner:
        rtn  = []
        for i in words:
            if len(i[1]) > 4:
                rtn.append(i)
        return rtn
    
    return words


"""
Given a tuple of strings and their index, the function returns the index of the first string contaning a given substring.
e.g. find_index("Namdar", [("Hello", 0), ("I", 1), ("am", 2), ("Namdar", 3), ("Namdar", 4)]) = 3
:word: the string to check
:arr: list of (word, index) tuples
"""
def find_first_index(word, arr):
    for i in arr:
        if word in i[0]:
            return i[1]
    return -1


@app.route('/preprocessor', methods=['POST', 'GET'])
def main():
    
    logging.debug("Received request")

    with open('./schemas/preprocessors/ner.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)

    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)

    with open('./schemas/definitions.json') as jsonfile:
        definition_schema = json.load(jsonfile)

    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)

    schema_store = {
        data_schema['$id']: data_schema,
        schema['$id']: schema,
        definition_schema['$id']: definition_schema
    }

    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)

    content = request.get_json()

    try:
        validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 400

    # ------ START COMPUTATION ------ #

    # check if 'graphic' and 'context' keys are in the content dict
    if 'graphic' in content and 'context' in content:
        name_ = "1"
        captions = {}              # dict to store the captions
        text = get_alt(content)    # extract alt text and save it in the caption dict
        captions[name_] = text
        html_ = content['graphic'] # get the image html content
    else:
        logging.info("No 'graphic' or 'context' tag")
        return "", 204
    
    # save pic and caption to directory for clipscore evaluation
    with open(CONTEXT_DIR+'/captions.json', "w") as outfile:
        json.dump(captions, outfile)
    save_image(html_, name_, IMAGE_DIR)

    # check if we have an alt text
    if len(text) < 2:
        logging.info("No alttxt")
        return "", 204

    # create path parameters for clipscore
    parameters = Namespace(candidates_json=CONTEXT_DIR+'/captions.json', compute_other_ref_metrics=1, image_dir=IMAGE_DIR, references_json=None, save_per_instance=CONTEXT_DIR+'/score.json')
    
    # calculate the clipscore
    score = round(clipscore.main(parameters)['1']['CLIPScore'], 3)
    # compute the NERs
    ners = stanford_ner(text)

    # create ner object and add index
    arr = text.split()
    indexed_list = list(zip(arr, range(len(arr))))
    index = 0
    ner_data = []
    for i in ners:
        my_dict = {}
        my_dict['value'] = i[0]
        my_dict['tag'] = i[1]
        index = find_first_index(i[0], indexed_list[index:]) + 1
        my_dict['index'] = index
        ner_data.append(my_dict)


    data = {
        'clipscore': score,
        'ner': ner_data,
        'alttxt': captions['1']
        }
    
    # ------ END COMPUTATION ------ #
    
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.ner"

    response = {
        'request_uuid': request_uuid,
        'timestamp': int(timestamp),
        'name': name,
        'data': data
    }

    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500

    logging.debug("Sending response")
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    main()
    remove_dirs()