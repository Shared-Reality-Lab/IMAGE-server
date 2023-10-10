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
import supplementary as s
import multiple as m
import find_subject_object as so
app = Flask(__name__)
logging.basicConfig(level=logging.NOTSET)


def remove_emotion(emotion):
    detected_emotion = []
    cloth_flag = False
    for i in range(len(emotion)):
        if ((emotion[i]["emotion"] is not None or emotion[i]
                ["celeb"] is not None)):
            detected_emotion.append(emotion[i])
        if (emotion[i]["clothes"] is not None):
            cloth_flag = True
    return detected_emotion, cloth_flag


def rendering_emotion(emotion):
    emotion, cloth_flag = remove_emotion(emotion)
    if (len(emotion) > 0):
        return True, cloth_flag, emotion
    else:
        return False, cloth_flag, emotion


def area(a, b):
    dx = min(a[2] * 100, b[2] * 100) - max(a[0] * 100, b[0] * 100)
    dy = min(a[3] * 100, b[3] * 100) - max(a[1] * 100, b[1] * 100)
    if (dx >= 0) and (dy >= 0):
        return (dx * dy)
    else:
        return None


def common_check(inanimate1, inanimate2):
    check_common = []
    for i in range(len(inanimate1)):
        for j in range(len(inanimate2)):
            if (inanimate1[i]["ID"] == inanimate2[j]["ID"]):
                check_common.append(inanimate1[i])
                break
    return check_common


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
            emo = object_emotion_inanimate[i]["emotion"]
            if ("happy" in emo["emotion"]):
                happy = happy + 1
            elif ("neutral" in emo["emotion"]):
                neutral = neutral + 1
            elif ("sad" in emo["emotion"]):
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
        object_emotion_inanimate, rendering, preprocessors):
    clothes = object_emotion_inanimate[0]["clothes"]
    happy = 0
    sad = 0
    neutral = 0
    cloth0 = ""
    cloth1 = ""
    for i in range(len(object_emotion_inanimate)):
        if (object_emotion_inanimate[i]["emotion"]["emotion"] is not None):
            emo = object_emotion_inanimate[i]["emotion"]
            if ("happy" in emo["emotion"]):
                happy = happy + 1
            elif ("neutral" in emo["emotion"]):
                neutral = neutral + 1
            elif ("sad" in emo["emotion"]):
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
            expr = "and all the mentioned people seem to be "
            rendering += expr + dominant_emotion
        else:
            expr = " Additionally all the mentioned people seem to be "
            rendering += expr + dominant_emotion
    return rendering


def image_description(preprocessors, rendering):
    if ("ca.mcgill.a11y.image.preprocessor.graphicTagger" in preprocessors):
        gt = preprocessors["ca.mcgill.a11y.image.preprocessor.graphicTagger"]
        if ("category" in gt):
            graphicTagger = gt["category"]
            # print(graphicTagger)
            if ("captions" in graphicTagger):
                desc = graphicTagger["description"]["captions"][0]["text"]
                expr = "Hence looking at the overall image, "
                expr += "this image seems to be of "
                rendering += expr + desc
                rendering += ". "
            else:
                rendering = rendering
            return rendering
        else:
            return ""
    else:
        return ""

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
    print("person count is(people_handler,285)", person_count)
    s.get_position(object_emotion_inanimate, person_count, rendering)
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
    print(len(object_emotion_inanimate))
    # find the verb and object
    if (len(object_emotion_inanimate) == 1):
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
        rendering, caption = sp.rendering_for_one_person(
            object_emotion_inanimate, rendering,
            preprocessors, person_count, sentence)
        print("rendering is,people_handler(354):", rendering)

    elif (len(object_emotion_inanimate) == 2):
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
        # this shows how much larger the previous object was compared to current one
        change = per_change(objects_sorted)
        # the input format needs to be reorganised for easy manipulation of data
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
