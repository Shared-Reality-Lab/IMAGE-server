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

from copy import deepcopy
from flask import Flask, jsonify, request
from jsonschema.exceptions import ValidationError
import logging
import time
from copy import deepcopy
import spacy
import re
import time

import check as c
import format as f
import single_person as sp
import two_people as tp
import supplementary as s
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


def rendering_format_check(object_emotion_inanimate, rendering, preprocessors):
    caption = 0
    celeb0 = object_emotion_inanimate[0]["celebrity"]["name"]
    celeb1 = object_emotion_inanimate[1]["celebrity"]["name"]
    clothes = object_emotion_inanimate[0]["clothes"]
    cloth0 = ""
    cloth1 = ""
    for i in range(len(clothes)):

        if (clothes[i]["article"] is not None and clothes[i]
                ["confidence"] >= 0.40):
            try:
                if (clothes[i]["color"] is not None):
                    cloth0 += " " + clothes[i]["color"] + " "
                cloth0 = cloth0 + clothes[i]["article"]
            except BaseException:
                cloth0 = cloth0 + clothes[i]["article"]
        if (len(clothes) == 1):
            cloth0 = cloth0

        elif (i == (len(clothes) - 2) and len(clothes) > 1):
            cloth0 = cloth0 + " and "
        else:
            cloth0 = cloth0 + " , "
    clothes = object_emotion_inanimate[1]["clothes"]
    for i in range(len(clothes)):
        if (clothes[i]["article"] is not None and clothes[i]
                ["confidence"] >= 0.40):
            try:
                if (clothes[i]["color"] is not None):
                    cloth1 += " " + clothes[i]["color"] + " "
                cloth1 = cloth1 + clothes[i]["artcile"]
            except BaseException:
                cloth1 = cloth1 + clothes[i]["article"]
        if (len(clothes) == 1):
            cloth1 = cloth1
        elif (i == (len(clothes) - 2) and len(clothes) > 1):
            cloth1 = cloth1 + " and "
        else:
            cloth1 = cloth1 + " , "
    happy = 0
    sad = 0
    neutral = 0
    for i in range(len(object_emotion_inanimate)):
        if (object_emotion_inanimate[i]["emotion"]["emotion"] is not None):
            if ("happy" in object_emotion_inanimate[i]["emotion"]["emotion"]):
                happy = happy + 1
            elif ("neutral" in object_emotion_inanimate[i]["emotion"]["emotion"]):
                neutral = neutral + 1
            elif ("sad" in object_emotion_inanimate[i]["emotion"]["emotion"]):
                sad = sad + 1
    dominant_emotion = tp.calculate_dominant_emotion_for_two(
        happy, sad, neutral)
    if (celeb0 is not None or celeb1 is not None):
        caption += 2
    if (cloth0 is not None or cloth1 is not None):
        caption += 1
    if (dominant_emotion is not None):
        caption += 1
    return caption


def rendering_two_people_caption(
        object_emotion_inanimate,
        rendering,
        preprocessors):
    clothes = object_emotion_inanimate[0]["clothes"]
    happy = 0
    sad = 0
    neutral = 0
    cloth0 = ""
    cloth1 = ""
    for i in range(len(object_emotion_inanimate)):
        if (object_emotion_inanimate[i]["emotion"]["emotion"] is not None):
            if ("happy" in object_emotion_inanimate[i]["emotion"]["emotion"]):
                happy = happy + 1
            elif ("neutral" in object_emotion_inanimate[i]["emotion"]["emotion"]):
                neutral = neutral + 1
            elif ("sad" in object_emotion_inanimate[i]["emotion"]["emotion"]):
                sad = sad + 1
    dominant_emotion = tp.calculate_dominant_emotion_for_two(
        happy, sad, neutral)
    for i in range(len(clothes)):
        if (clothes[i]["cloth"] is not None and clothes[i]
                ["confidence"] >= 0.40):
            try:
                if (clothes[i]["color"] is not None):
                    cloth0 += " " + clothes[i]["color"] + " "
                cloth0 = cloth0 + clothes[i]["cloth"]
            except BaseException:
                cloth0 = cloth0 + clothes[i]["cloth"]
        if (len(clothes) == 1):
            cloth0 = cloth0

        elif (i == (len(clothes) - 2) and len(clothes) > 1):
            cloth0 = cloth0 + " and "
        else:
            cloth0 = cloth0 + " , "
    clothes = object_emotion_inanimate[1]["clothes"]
    for i in range(len(clothes)):
        if (clothes[i]["cloth"] is not None and clothes[i]
                ["confidence"] >= 0.40):
            try:
                if (clothes[i]["color"] is not None):
                    cloth1 += " " + clothes[i]["color"] + " "
                cloth1 = cloth1 + clothes[i]["cloth"]
            except BaseException:
                cloth1 = cloth1 + clothes[i]["cloth"]
        if (len(clothes) == 1):
            cloth1 = cloth1
        elif (i == (len(clothes) - 2) and len(clothes) > 1):
            cloth1 = cloth1 + " and "
        else:
            cloth1 = cloth1 + " , "

    if (len(cloth0) > 0 and cloth0 != " , "):
        rendering += "The first person seems to be wearing " + cloth0
        if (len(cloth1) > 0 and cloth1 != " , "):
            rendering += " and the second person seems to be wearing " + cloth1
    elif (len(cloth1) > 0 and cloth1 != " , "):
        rendering += " The second person seems to be wearing " + cloth1
    if (dominant_emotion is not None):
        if ((len(cloth0) > 0 and cloth0 != " , ") or (
                len(cloth1) > 0 and cloth1 != " , ")):
            rendering += "and all the mentioned people seem to be " + dominant_emotion
        else:
            rendering += " Additionally all the mentioned people seem to be " + dominant_emotion
    return rendering


def check_major_person(object_emotion_inanimate, rendering):
    objects = deepcopy(object_emotion_inanimate)
    objects_sorted = sorted(
        objects['objects'],
        key=lambda d: d['area'],
        reverse=True)


def get_rendering(
        multiple_flag,
        emotion_flag,
        object_emotion_inanimate,
        preprocessors,
        objects,
        just_person_count,
        cloth_flag,
        contents,
        res):
    rendering = ""
    res = preprocessors["ca.mcgill.a11y.image.preprocessor.caption"]["caption"]
    if (len(rendering) == 0):
        rendering += "Image possibly contains: "
    else:
        rendering += "Moreover, on further inspection I can see "
    segment = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]["segments"]
    for i in range(len(segment)):
        if ("person" in segment[i]["name"]):
            area = segment[i]["area"]
            break
    person_count = f.check_multiple(objects, False)
    print("person count is(people_handler,285)", person_count)
    # print(person_count)
    s.get_position(object_emotion_inanimate, person_count, rendering)
    if (multiple_flag):
        if (person_count < 3):
            rendering = rendering + str(person_count) + " people "
        else:
            rendering += "multiple people "
    else:
        if (person_count == 1):
            # ,standing in the centre of the image. This person occupies " + str(int(area*100)) + " percent of the image. "
            rendering = rendering + " a single person "
        else:
            rendering = rendering + str(person_count) + " " + "people "
    print("rendering is(people_hanlder,300):", rendering)
    print("length of object emotion inanimate", len(object_emotion_inanimate))
    print(object_emotion_inanimate)
    if ((len(object_emotion_inanimate) == 0 or emotion_flag == False) and cloth_flag):
        cloth = ""
        number = 0
        for i in range(len(object_emotion_inanimate)):
            if (object_emotion_inanimate[i]["clothes"] is not None):
                cloth += object_emotion_inanimate[i]["clothes"][0]["cloth"]
                number += 1
                cloth += ' , '
        if (number > 1 and len(object_emotion_inanimate) != 2):
            rendering += "A few of these people seem to be wearing " + cloth + \
                ". However, I cannot give you more information than this. This is because the people are either too small or not properly oriented in the image to give more details."
        elif (number > 1 and len(object_emotion_inanimate) == 1):
            rendering += "This person seems to be wearing " + cloth + \
                ". However, I cannot give you more information than this as the face of the person is not clearly visible."
        elif (len(object_emotion_inanimate) == 2):
            rendering += "One of the person seems to be wearing " + cloth + \
                ". However, I cannot give you more information than this as the face of the people are not clearly visible."
        elif (len(object_emotion_inanimate) >= 2):
            rendering += "A few people seem to be wearing " + cloth + \
                ". However, I cannot give you more information than this as the face of the people are not clearly visible."
    caption = 0
    nlp = spacy.load("en_core_web_sm")
    print(len(object_emotion_inanimate))
    if (len(object_emotion_inanimate) == 1):
        print("single person caption", res)
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(res)
        svo = so.findSVOs(doc)
        print("verb positions are", svo[0])
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
        # print(sentence)
        rendering, caption = sp.rendering_for_one_person(
            object_emotion_inanimate, rendering, preprocessors, person_count, sentence)
        print("rendering is,people_handler(354):", rendering)

    elif (len(object_emotion_inanimate) == 2):
        caption = rendering_format_check(
            object_emotion_inanimate, rendering, preprocessors)
        rendering, emo_count, clothes_count = tp.rendering_for_two_people(
            object_emotion_inanimate, rendering, preprocessors)
        sentence = re.sub('[^A-Za-z0-9]+', ' ', res)
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
            print("verb positions are", svo[0])
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

    print("final output is: ")
    print(rendering)
    print("\n")
    return rendering


@app.route("/handler", methods=["POST"])
def handle():
    logging.debug("Received request")
    contents = request.get_json()

    # Check preprocessor data
    preprocessors = contents['preprocessors']
    possible_people = 0

    # No Object Detector found
    if "ca.mcgill.a11y.image.preprocessor.objectDetection" not in preprocessors:
        logging.debug("No Object Detector found")
        logging.debug("Sending response")
        response = {
            "request_uuid": contents["request_uuid"],
            "timestamp": int(time.time()),
            "renderings": []
        }
        return response
    # add check
    # possible_people = 0
    if ("ca.mcgill.a11y.image.preprocessor.graphicTagger" in preprocessors):
        if (preprocessors["ca.mcgill.a11y.image.preprocessor.graphicTagger"]
                ["category"] == "people"):
            objects = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]["objects"]
            possible_people += 1
            # print("SC")
            count = 0

    # checks if emotion detection detects face
    possible_people += c.custom_check(preprocessors)
    # print("possible people: ",possible_people)
    objects = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]["objects"]
    # print("Possible people", possible_people)
    res = preprocessors["ca.mcgill.a11y.image.preprocessor.caption"]["caption"]
    print("Caption is:(line 422) ", res)
    print("\n")
    print("\n")
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
        # return str(possible_people)
    else:
        # return "people"
        objects, left2right = f.remove_low_confidence(
            objects, preprocessors["ca.mcgill.a11y.image.preprocessor.sorting"]["leftToRight"])
        objects_sorted = sorted(objects, key=lambda d: d['area'], reverse=True)
        change = per_change(objects_sorted)
        if ("ca.mcgill.a11y.image.preprocessor.emotion" in preprocessors):
            preprocessors = f.get_original_format(preprocessors)
            multiple_flag, emotion_flag, object_emotion_inanimate, objects, just_person_count, cloth_flag = f.format_json(
                objects_sorted, change, preprocessors)
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
            logging.critical(time.time())
            print(time.time())
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

        else:
            return "cannot be rendered"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=82, debug=True)
