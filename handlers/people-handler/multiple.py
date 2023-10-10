# The file will generate a rendering if the image contains more than 3 people

import supplementary as s
import logging


def calculate_dominant_emotion(happy, sad, neutral):
    if (happy >= 1 and neutral >= 1 and sad == 0):
        return " mostly having a happy or neutral expression "
    if (sad >= 1 and neutral >= 1 and happy == 0):
        return "mostly having a sad or neutral expression "
    if (happy > 0 and neutral == 0 and sad == 0):
        return "mostly being happy "
    if (sad > 0 and neutral == 0 and happy == 0):
        return "mostly being sad "
    if (neutral > 0 and sad == 0 and happy == 0):
        return "mostly having a neutral expression "
    if (happy >= 1 and sad >= 1 and neutral == 0):
        return "mostly having happy expression "
    if (happy >= 1 and sad >= 1 and neutral >= 1):
        return (
            "There is a mix of different emotions for these people."
            "Some seem to be happy "
            "while others seem to have neutral or sad expression."
        )


def inanimate_rendering_multiple(object_emotion_inanimate, rendering):
    inanimate_dict = {}
    for i in range(len(object_emotion_inanimate)):
        inanimate = object_emotion_inanimate[i]["inanimate"]
        for j in range(len(inanimate)):
            if (inanimate[j]["type"] in inanimate_dict):
                inanimate_dict[inanimate[j]["type"]
                               ] = inanimate_dict[inanimate[j]["type"]] + 1
            else:
                inanimate_dict[inanimate[j]["type"]] = 1
    inanimate_dict = dict(
        sorted(
            inanimate_dict.items(),
            key=lambda item: item[1],
            reverse=True))
    if (len(inanimate_dict) > 0):
        rendering += "Among these people, "
    i = 0
    multiple_flag = 0
    single_flag = 0
    printed = 0
    for key in (inanimate_dict):
        if (inanimate_dict[key] > 1):
            if (multiple_flag == 0):
                rendering += "a few seem to be "
                rendering += s.get_action(key)
                rendering += ","
                multiple_flag += 1
            else:
                if (multiple_flag == 1 and printed == 0):
                    rendering += " while others seem to be "
                    printed += 1
                    rendering += s.get_action(key)
                    rendering += ","
                elif (printed == 1):
                    rendering += " etc. ."
                    printed += 1
                elif (printed > 1):
                    continue
        elif (inanimate_dict[key] == 1):
            if (multiple_flag >= 2):
                rendering += ". Additionally "
            elif (multiple_flag == 1):
                rendering += " and "
            if (single_flag > 0):
                rendering += " while another person seems to be "
                rendering += s.get_action(key)
                rendering += ","
                break
            elif (single_flag == 0):
                rendering += " one person seems to be "
                rendering += s.get_action(key)
                rendering += ","
            single_flag += 1

        if (i == 2):
            break

        i += 1
    rendering += "."
    return rendering


def rendering_for_multiple_people(
        object_emotion_inanimate, rendering, preprocessors):
    celeb_position = []
    unique_cloth = []
    emotion_count = 0
    clothes_count = 0
    for i in range(len(object_emotion_inanimate)):
        if (object_emotion_inanimate[i]["celebrity"]["name"] != 'None'):
            celeb_position.append(i)
    print("celeb position in multiple", celeb_position)
    if (len(celeb_position) == 0):
        happy = 0
        sad = 0
        neutral = 0
        cloth = ""

        for i in range(len(object_emotion_inanimate)):
            if (object_emotion_inanimate[i]["emotion"]["emotion"] != 'None'):
                emo = object_emotion_inanimate[i]["emotion"]["emotion"]
                if ("happy" in emo):
                    happy = happy + 1
                elif ("neutral" in emo):
                    neutral = neutral + 1
                elif ("sad" in emo):
                    sad = sad + 1
        dominant_emotion = calculate_dominant_emotion(happy, sad, neutral)
        if (dominant_emotion is not None):
            emotion_count += 1
            rendering = rendering + dominant_emotion
        for i in range(len(object_emotion_inanimate)):
            if (object_emotion_inanimate[i]["clothes"] != 'None'):
                for j in range(len(object_emotion_inanimate[i]["clothes"])):
                    please_flake8 = object_emotion_inanimate[i]
                    if (please_flake8["clothes"][j]["article"] != 'None'):
                        article = \
                            please_flake8["clothes"][j]["article"]
                        logging.critical(article)
                        logging.critical(unique_cloth)
                        if (any(
                                article in s for s in unique_cloth)):
                            continue
                        else:
                            unique_cloth.append(article)
                            cloth = cloth + \
                                please_flake8["clothes"][j]["color"] + " "
                            cloth += article
                            cloth += " , "
                            clothes_count += 1
            if (clothes_count >= 3):
                cloth += " etc. "
                break
        if (len(cloth) != 0):
            if (emotion_count > 0):
                rendering += " and wearing: "
            else:
                rendering += " mostly wearing: "
            rendering += cloth
    else:
        i_list = 0
        render_add = 0
        if (len(celeb_position) == 1):
            rendering += "with one of them being "
        elif (len(celeb_position) == 2):
            rendering += "with two of them being "
        else:
            rendering += " with a few of them being "

        while (i_list < len(object_emotion_inanimate)):
            if (i_list in celeb_position):
                if (object_emotion_inanimate[i_list]
                        ["emotion"]["emotion"] is not None):
                    random_obj = object_emotion_inanimate[i_list]
                    rendering = rendering + " a " + \
                        random_obj["emotion"]["emotion"] + " faced "
                    emotion_count += 1
                rendering = rendering + \
                    random_obj["celebrity"]["name"] + " , "
                emotion_count += 1
            i_list = i_list + 1
            render_add += 1
    return rendering, emotion_count, clothes_count
