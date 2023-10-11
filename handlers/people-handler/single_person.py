# This file will generate a rendering if the image contains only one person

import supplementary as s


def rendering_for_one_person(
        object_emotion_inanimate, rendering, preprocessors, person_count, res):
    caption = 0
    celeb = object_emotion_inanimate[0]["celebrity"]["name"]
    # rendering stratergy will be different
    # if the person is not a celebrity
    if (celeb != "None"):
        caption += 1
        rendering = "Image possibly contains: "
        if (person_count > 1):
            rendering = "Image possibly contains: " + \
                str(person_count) + " people with one of them being "
        emotion = " "
        if (object_emotion_inanimate[0]["emotion"]["emotion"] != "None"):
            emotion = object_emotion_inanimate[0]["emotion"]["emotion"]
            if ("happy" in emotion or "sad" in emotion):
                emotion = emotion + " "
            else:
                emotion = " a neutral faced "
        rendering = rendering + emotion + celeb
    else:
        caption += 1
        rendering = "Image possibly contains: "
        gender = " person "
        emotion = " "
        if (object_emotion_inanimate[0]["emotion"]["emotion"] != "None"):
            emotion = object_emotion_inanimate[0]["emotion"]["emotion"]
            if ("happy" in emotion or "sad" in emotion):
                emotion = "a " + emotion
            else:
                emotion = " a neutral"
            emotion += " faced "
        rendering += emotion + gender
    clothes = object_emotion_inanimate[0]["clothes"]
    # add clothes information to the description
    if (clothes != "None"):
        caption += 1
        cloth = ""
        for i in range(len(clothes)):
            if (clothes[i]["article"] !=
                    "None" and clothes[i]["confidence"] >= 0.40):
                try:
                    if (clothes[i]["color"] is not None):
                        cloth += " " + clothes[i]["color"] + " "
                    cloth = cloth + clothes[i]["article"]
                except BaseException:
                    cloth = cloth + clothes[i]["article"]
            if (len(clothes) == 1):
                cloth = cloth

            elif (i == (len(clothes) - 2) and len(clothes) > 1):
                cloth = cloth + " and "
            else:
                cloth = cloth + " , "
        if (len(cloth) > 0 and cloth != " , "):
            rendering += " ,wearing: " + cloth + ". "
        else:
            rendering += ". "
        rendering = s.get_position(
            object_emotion_inanimate,
            person_count,
            rendering)
        rendering = s.inanimate_rendering(
            object_emotion_inanimate[0]["inanimate"], rendering, res)
    process = preprocessors
    segment = process["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]
    segment = segment["segments"]
    for i in range(len(segment)):
        if ("person" in segment[i]["name"]):
            break
    return rendering, caption
