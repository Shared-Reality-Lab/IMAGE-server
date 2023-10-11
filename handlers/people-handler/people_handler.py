# Copyright (c) 2023 IMAGE Project, Shared Reality Lab, McGill University
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

from flask import Flask, request
import logging
import time
import spacy
import re
import check as c
import format as f
import single_person as sp
import two_people as tp
import multiple as m
import find_subject_object as so
app = Flask(__name__)
logging.basicConfig(level=logging.NOTSET)


def per_change(objects):
    change = []
    for i in range(len(objects) - 1):
        big_obj = objects[i]["area"]
        small_obj = objects[i + 1]["area"]
        area = (big_obj - small_obj) / small_obj
        area = area * 100
        change.append(area)
    return change


def get_rendering(multiple_flag, emotion_flag, object_emotion_inanimate,
                  preprocessors, objects, just_person_count,
                  cloth_flag, contents, res):
    rendering = ""
    res = preprocessors["ca.mcgill.a11y.image.preprocessor.caption"]["caption"]
    if (len(rendering) == 0):
        rendering += "Image possibly contains: "
    else:
        rendering += "Moreover, on further inspection I can see "
    k = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]
    segment = k["segments"]
    for i in range(len(segment)):
        if ("person" in segment[i]["name"]):
            break
    # get number of people in the image
    person_count = f.check_multiple(objects, False)
    # determine whether the object is
    # in the middle, left or right portion of the image
    # s.get_position(object_emotion_inanimate, person_count, rendering)
    # change the description based on number of people
    if (multiple_flag):
        if (person_count < 3):
            rendering = rendering + str(person_count) + " people "
        else:
            rendering += "multiple people "
    else:
        if (person_count == 1):
            rendering = rendering + " a single person "
        else:
            rendering = rendering + str(person_count) + " " + "people "
    # if no people are detected, or the detected people were too small,
    # or the confidence threshold was not met, then return a standard response
    if ((len(object_emotion_inanimate) == 0 or emotion_flag)
            and cloth_flag):
        cloth = ""
        number = 0
        for i in range(len(object_emotion_inanimate)):
            if (object_emotion_inanimate[i]["clothes"] is not None):
                cloth += object_emotion_inanimate[i]["clothes"][0]["cloth"]
                number += 1
                cloth += ' , '
        if (number > 1 and len(object_emotion_inanimate) != 2):
            expr = "A few of these people seem to be wearing "
            rendering += expr + cloth + \
                ". However, I cannot give you more information than this. " + \
                "This is because the people are either " +\
                "too small or not properly " + \
                "oriented in the image to give more details."
        elif (number > 1 and len(object_emotion_inanimate) == 1):
            rendering += "This person seems to be wearing " + cloth + \
                ". However, I cannot give you more information than this " + \
                "as the face of the person is not clearly visible."
        elif (len(object_emotion_inanimate) == 2):
            rendering += "One of the person seems to be wearing " + cloth + \
                ". However, I cannot give you more information than this " + \
                "as the face of the people are not clearly visible."
        elif (len(object_emotion_inanimate) >= 2):
            rendering += "A few people seem to be wearing " + cloth + \
                ". However, I cannot give you more information than this " + \
                "as the face of the people are not clearly visible."
    caption = 0
    nlp = spacy.load("en_core_web_sm")
    # generate a description when image contains just one individual
    if (len(object_emotion_inanimate) == 1):
        # get the subject, verb and object
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(res)
        svo = so.findSVOs(doc)
        verb = svo[0][1]
        verb_posi = [token.i for token in doc if token.pos_ == "VERB"]
        posi = verb_posi[0]
        sentence = ""
        passed = False
        i = 0
        sentence_split = res.split()
        for word in sentence_split:
            if (word == verb or passed):
                passed = True
                sentence += word
                sentence += " "
            else:
                continue
        sentence = re.sub('[^A-Za-z0-9]+', ' ', sentence)
        rendering += sentence
        # generate the description by compiling all the information
        rendering, caption = sp.rendering_for_one_person(
            object_emotion_inanimate, rendering,
            preprocessors, person_count, sentence)

    # generate a description when image contains two individuals
    elif (len(object_emotion_inanimate) == 2):
        rendering, emo_count, clothes_count = tp.rendering_for_two_people(
            object_emotion_inanimate, rendering, preprocessors)
        sentence = re.sub('[^A-Za-z0-9]+', ' ', res)
        # add the verb and object of the caption to the description
        if (emo_count > 0 and clothes_count > 0):
            rendering += ". Interpretation: " + sentence
        elif (emo_count == 0 and clothes_count == 0):
            rendering = "Image possibly contains: " + sentence
        elif (clothes_count > 0):
            rendering += ". Interpretation: " + sentence
        else:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(res)
            svo = so.findSVOs(doc)
            verb = svo[0][1]
            verb_posi = [token.i for token in doc if token.pos_ == "VERB"]
            posi = verb_posi[0]
            sentence = ""
            passed = False
            i = 0
            sentence_split = res.split()
            for word in sentence_split:
                if (word == verb or passed):
                    passed = True
                    sentence += word
                    sentence += " "
                else:
                    continue
            sentence = re.sub('[^A-Za-z0-9]+', ' ', sentence)
            rendering += sentence
    # generate descriptions for images containing multiple people
    else:
        rendering, emo_count, clothes_count = m.rendering_for_multiple_people(
            object_emotion_inanimate, rendering, preprocessors)
        sentence = re.sub('[^A-Za-z0-9]+', ' ', res)
        if (emo_count > 0 and clothes_count > 0):
            rendering += ". Interpretation: " + sentence
        elif (emo_count == 0 and clothes_count == 0):
            rendering = "Image possibly contains: " + sentence
        else:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(res)
            verb_posi = [token.i for token in doc if token.pos_ == "VERB"]
            posi = verb_posi[-1]
            sentence = ""
            i = 0
            for token in doc:
                if (i >= posi):
                    sentence += token.orth_
                    sentence += " "
                i += 1
            sentence = re.sub('[^A-Za-z0-9]+', ' ', sentence)
            rendering += sentence
    return rendering


@app.route("/handler", methods=["POST"])
def handle():
    logging.debug("Received request")
    contents = request.get_json()

    # Check preprocessor data
    preprocessors = contents['preprocessors']
    possible_people = 0

    # No Object Detector found
    prep = "ca.mcgill.a11y.image.preprocessor.objectDetection"
    if prep not in preprocessors:
        logging.debug("No Object Detector found")
        logging.debug("Sending response")
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        return response

    if ("ca.mcgill.a11y.image.preprocessor.graphicTagger" in preprocessors):
        if (preprocessors["ca.mcgill.a11y.image.preprocessor.graphicTagger"]
                ["category"] == "people"):
            objects = preprocessors[prep]["objects"]
            possible_people += 1

    # Run the Stage 1 of the handler
    possible_people += c.custom_check(preprocessors)
    objects = preprocessors[prep]["objects"]
    res = preprocessors["ca.mcgill.a11y.image.preprocessor.caption"]["caption"]
    if (possible_people <= 1):
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": [
                {
                    "type_id": "ca.mcgill.a11y.image.renderer.Text",
                    "description": "The text found in a graphic.",
                    "data": {
                        "text": "Cannot be rendered"
                    }
                }
            ]
        }
        return response
    else:
        sort = "ca.mcgill.a11y.image.preprocessor.sorting"
        # remove low confidence predictions
        objects, left2right = f.remove_low_confidence(
            objects, preprocessors[sort]["leftToRight"])
        # sort the objects based on their area
        objects_sorted = sorted(objects, key=lambda d: d['area'], reverse=True)
        # determine the percentage change that happens with consecutive objects
        # this shows how much larger the previous object was compared to
        # current one
        change = per_change(objects_sorted)
        # the input format needs to be reorganised for easy manipulation of
        # data
        preprocessors = f.get_original_format(preprocessors)
        mf, ef, oei, objects, just_person_count, cf = f.format_json(
            objects_sorted, change, preprocessors)
        multiple_flag = mf
        emotion_flag = ef
        cloth_flag = cf
        object_emotion_inanimate = oei
        rendering = get_rendering(
            multiple_flag,
            emotion_flag,
            object_emotion_inanimate,
            preprocessors,
            objects,
            just_person_count,
            cloth_flag,
            contents,
            res)
        logging.critical(rendering)
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": [
                {
                    "type_id": "ca.mcgill.a11y.image.renderer.Text",
                    "description": "Image description",
                    "data": {
                        "text": rendering
                    }
                }
            ]
        }
        return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=82, debug=True)
