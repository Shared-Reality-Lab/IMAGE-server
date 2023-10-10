# This file will generate a rendering if the image contains two people

import logging


def common_check(inanimate1, inanimate2):
    check_common = []
    for i in range(len(inanimate1)):
        for j in range(len(inanimate2)):
            if (inanimate1[i]["ID"] == inanimate2[j]["ID"]):
                check_common.append(inanimate1[i])
                break
    return check_common


def calculate_dominant_emotion_for_two(happy, sad, neutral):
    if (happy == 2):
        return "happy expression "
    if (sad == 2):
        return "sad expression "
    if (neutral == 2):
        return "serious expression "
    if (happy == 1 and neutral == 1):
        return "happy  expressions "
    if (neutral == 1 and sad == 1):
        return "sad expressions "
    if (happy == 1):
        return "happy expression "
    if (sad == 1):
        return "sad expression "
    if (neutral == 1):
        return "serious expression "
    return ""



def rendering_for_two_people(
        object_emotion_inanimate, rendering, preprocessors):
    # common = common_check(
    #     object_emotion_inanimate[0]["inanimate"],
    #     object_emotion_inanimate[1]["inanimate"])
    emo_count = 0
    clothes_count = 0
    cloth0 = ""
    cloth1 = ""
    emotion0 = object_emotion_inanimate[0]["emotion"]["emotion"]
    emotion1 = object_emotion_inanimate[1]["emotion"]["emotion"]
    happy = 0
    sad = 0
    neutral = 0
    celeb0 = object_emotion_inanimate[0]["celebrity"]["name"]
    celeb1 = object_emotion_inanimate[1]["celebrity"]["name"]
    logging.critical("line 34,two_people: {}".format(celeb1))
    clothes = object_emotion_inanimate[0]["clothes"]
    if (celeb0 != 'None' and celeb1 != 'None'):
        rendering = "Image possibly contains: "
        print("line 38, two_people")

    for i in range(len(clothes)):
        if (clothes[i]["confidence"] != 'None'):
            clothes[i]["confidence"] = 0
        if (clothes[i]["article"] !=
                'None' and clothes[i]["confidence"] >= 0.40):
            try:
                if (clothes[i]["color"] != 'None'):
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
        if (clothes[i]["article"] !=
                'None' and clothes[i]["confidence"] >= 0.40):
            try:
                if (clothes[i]["color"] != 'None'):
                    cloth1 += " " + clothes[i]["color"] + " "
                cloth1 = cloth1 + clothes[i]["article"]
            except BaseException:
                cloth1 = cloth1 + clothes[i]["article"]
        if (len(clothes) == 1):
            cloth1 = cloth1
        elif (i == (len(clothes) - 2) and len(clothes) > 1):
            cloth1 = cloth1 + " and "
        else:
            cloth1 = cloth1 + " , "

    if (celeb0 != 'None'):
        rendering = "Image possibly contains: "
        rendering = rendering + celeb0
        if (object_emotion_inanimate[0]["emotion"]["emotion"] != 'None'):
            rendering += " having a " + \
                object_emotion_inanimate[0]["emotion"]["emotion"] + \
                " expression, "
            emo_count += 1
        if (len(cloth0) > 0 and cloth0 != " , "):
            rendering = rendering + " wearing " + cloth0
            clothes_count += 1
    if (celeb1 != 'None'):
        if (celeb0 != 'None'):
            rendering = rendering + " and " + celeb1 + ""
        else:
            rendering = rendering + " with one of them being " + celeb1 + ""
        first_person = object_emotion_inanimate[1]
        if ((len(cloth1) > 0 and (cloth1 != " , " or cloth1 != " and "))
                or first_person["emotion"]["emotion"] != 'None'):
            if (object_emotion_inanimate[0]["emotion"]["emotion"] != 'None'):
                rendering += " having a " + \
                    object_emotion_inanimate[1]["emotion"]["emotion"] + \
                    " expression, "
                emo_count += 1
            if (len(cloth0) > 0 and cloth0 != " , "):
                rendering = rendering + " wearing " + cloth1
                clothes_count += 1
    elif (celeb0 == 'None' and celeb1 == 'None'):
        second_person = object_emotion_inanimate[0]
        if (object_emotion_inanimate[1]["emotion"]["emotion"] !=
                'None' or second_person["emotion"]["emotion"] != 'None'):
            if ("happy" in emotion0 or "happy" in emotion1):
                happy = happy + 1
            elif ("neutral" in emotion0 or "neutral" in emotion1):
                neutral = neutral + 1
            elif ("sad" in emotion0 or "sad" in emotion1):
                sad = sad + 1
            emo_combined = calculate_dominant_emotion_for_two(
                happy, neutral, sad)
            if (len(emo_combined) > 0):
                rendering = rendering + " having a " + emo_combined
                emo_count += 1
        if ((len(cloth1) > 0 and (cloth1 != " , " or cloth1 != " and ")) or (
                len(cloth0) > 0 and (cloth0 != " , " or cloth0 != " and "))):
            rendering += " wearing "
            clothes_count += 1
            print(cloth0)
            print(cloth1)
            if (len(cloth0) >= 2 and len(cloth1) == 0):
                rendering += cloth0
                # rendering += " etc. "
            elif (len(cloth1) >= 2 and len(cloth0) == 0):
                rendering = rendering + cloth1
            else:
                rendering = rendering + cloth0 + ","
                if (len(cloth1) > 1):
                    rendering = rendering + cloth1
    return rendering, emo_count, clothes_count
