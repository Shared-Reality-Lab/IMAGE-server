import os, sys
import json
import shutil
import logging
import tempfile

import nltk
import clipscore
from bs4 import BeautifulSoup
from html2image import Html2Image
from nltk.tag.stanford import StanfordNERTagger


CONTEXT_DIR = tempfile.mkdtemp()
IMAGE_DIR = tempfile.mkdtemp()
jar = './stanford-ner/stanford-ner.jar'
model = './stanford-ner/ner-model-english.ser.gz'


"""
Save a html contaning an image to a given location
:my_html: the html to save
:name: name of the to save
:out_dir: directory to save the image to
"""
def save_pic(my_html, name, out_dir):
    path = f"{out_dir}"
    hti = Html2Image()
    path_ = os.path.abspath(path)
    hti._output_path = path_
    hti.screenshot(html_str=my_html, save_as=name)
     
"""
Creates the image from the image data
:my_image: image data extracted from the raw data json
"""
def get_img_html(my_image):
    return f"<html> <body> <img src=\"{my_image}\"> </body> </html>"

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
Function to extarct the NERs from a given english sentence, using the Stanford ner model
:sentence: the sentence to check
"""
def stanford_ner(sentence, only_ner = True):
    
    # Prepare NER tagger with english model
    ner_tagger = StanfordNERTagger(model, jar, encoding='utf8')

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


# @app.route('/preprocessor', methods=['POST', 'GET'])
def main():

    with open('./example_input.json') as f:
        content = json.load(f)

    name_ = "1"
    captions = {}                            # dict to store the captions
    text = get_alt(content)                  # extract alt text and save it in the caption dict
    captions[name_] = text
    html_ = get_img_html(content['graphic']) # get the image html content
    url = content["URL"]                     # extract image url
    
    # save pic and caption to directory for clipscore evaluation
    with open(CONTEXT_DIR+'/captions.json', "w") as outfile:
        json.dump(captions, outfile)

    save_pic(html_, name_+'.png', IMAGE_DIR)
    
    # check if we have an alt text
    if len(text) < 2:
        logging.info("No alttxt")
        return "", 204

    # create path parameters for clipscore
    parameters = Namespace(candidates_json=CONTEXT_DIR+'/captions.json', compute_other_ref_metrics=1, image_dir=IMAGE_DIR, references_json=None, save_per_instance=CONTEXT_DIR+'/score.json')
    
    # calculate the clipscore
    score = clipscore.main(parameters)['1']['CLIPScore']
    
    # compute the NERs
    ners = stanford_ner(text)
    
    # create final json
    rtn = {'clipscore': score,
           'ner': [[i[0], i[1]] for i in ners],
           'alttxt': captions['1']
          }
    
    print(rtn)
    

if __name__ == '__main__':
    main()


