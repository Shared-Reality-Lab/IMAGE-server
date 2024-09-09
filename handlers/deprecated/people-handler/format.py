# this file rearranges the code to the following format
# {
# "object",
# "emotion",
# "celebrity",
# "clothes"
# "position"
# "inanimate"
# }
# The "object" field, contains the ID of the person and
# the "inanimate" field refers to the number of objects near that person
# the "position" object is a non-mandatory field.
# The option has been provided in case the position (sitting, standing)
# is detected.
# We initially planned to integrate this information in the handler,
# but decided to not provide the information
# as the associated ML model gave incorrect responses

# check number of people in the image
# that occupy more than 10% area of the image.
# We have chosen 10% empirically as from our testing
# with 30-40 images. People that occupy
# lesser area than that are generally in the background and are not
# important for the image
def check_multiple(objects, major):
    count = 0
    for i in range(len(objects)):
        if ("person" in objects[i]["type"]):
            if (major):
                if (objects[i]["area"] * 100 > 10.0):
                    count = count + 1
            else:
                count = count + 1
    return count


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


def remove_low_confidence(objects, left2right):
    objects_high_conf = []
    for o in objects:
        if ((o["confidence"]) <= 0.3):
            if (o["ID"] in left2right):
                left2right.remove(o["ID"])
            continue
        else:
            objects_high_conf.append(o)
    return objects_high_conf, left2right

# calculate the area occupied by the object


def area(a, b):
    dx = min(a[2] * 100, b[2] * 100) - max(a[0] * 100, b[0] * 100)
    dy = min(a[3] * 100, b[3] * 100) - max(a[1] * 100, b[1] * 100)
    if (dx >= 0) and (dy >= 0):
        return (dx * dy)
    else:
        return None


def get_ideal_format(objects, emotion, preprocessors):
    ideal_format = []
    left2right_object = []
    # check if the position preprocessor exists,
    # else skip
    try:
        posi_data = preprocessors['ca.mcgill.a11y.image.preprocessor.position']
        position = posi_data['data']
    except BaseException:
        position = [{"id": None, "position": None}]
    objson = preprocessors["ca.mcgill.a11y.image.preprocessor.objectDetection"]
    ob_json = objson['objects']
    l2rjson = preprocessors["ca.mcgill.a11y.image.preprocessor.sorting"]
    l2r_json = l2rjson["leftToRight"]
    # remove low confidence objects
    objects, left2right = remove_low_confidence(
        ob_json, l2r_json)
    # arrange objects from left to right based on centroid positions
    for i in range(len(left2right)):
        for j in range(len(objects)):
            if (left2right[i] == objects[j]["ID"]):
                if ("person" in objects[j]["type"] and objects[j]["area"]
                        * 100 > 4.0 and objects[j]["confidence"] * 100 > 30.0):
                    left2right_object.append(objects[j])
                break

    for i in range(len(left2right_object)):
        for j in range(len(emotion)):
            if (left2right_object[i]["ID"] == emotion[j]["id"]):
                # if person is a celebrity include that information
                celeb = {
                    "name": emotion[j]['celeb']["name"],
                    "confidence": emotion[j]['celeb']["confidence"]
                }
                # if clothes information is available include that
                clothes = emotion[j]["clothes"]
                posi_obj = None
                # if emotion information is available include that
                if (emotion[j]["confidence"] is not None):
                    if (emotion[j]["confidence"] >= 0.40):
                        emotion_to_be_sent = {
                            "emotion": emotion[j]["emotion"],
                            "confidence": emotion[j]["confidence"],
                            "gender": None,
                        }
                    else:
                        emotion_to_be_sent = {
                            "emotion": "None",
                            "confidence": "None",
                            "gender": "None",
                        }
                else:
                    emotion_to_be_sent = {
                        "emotion": "None",
                        "confidence": "None",
                        "gender": "None",
                    }
                for k in range(len(position)):
                    if (left2right_object[i]["ID"] == position[k]["id"]):
                        posi_obj = position[k]["position"]
                ideal_format.append({
                    "objects": left2right_object[i],
                    "emotion": emotion_to_be_sent,
                    "celebrity": celeb,
                    "clothes": clothes,
                    "position": posi_obj
                })
                break
    return ideal_format


def inanimated_interaction(object_emotion, objects):
    object_emotion_inanimate = object_emotion.copy()
    inanimate_obj = []
    for i in range(len(objects)):
        if ("person" in objects[i]["type"] or (
                objects[i]["confidence"] * 100) <= 50.0):
            continue
        inanimate_obj.append(objects[i])
    for i in range(len(object_emotion)):
        obj = object_emotion[i]["objects"]
        object_emotion_inanimate[i]["inanimate"] = list()
        for j in range(len(inanimate_obj)):
            ar = area(obj["dimensions"], inanimate_obj[j]["dimensions"])
            if (ar is not None):
                object_emotion_inanimate[i]["inanimate"].append(
                    inanimate_obj[j])
    return object_emotion_inanimate


def get_original_format(preprocessors):
    json = preprocessors["ca.mcgill.a11y.image.preprocessor.celebrityDetector"]
    json1 = preprocessors["ca.mcgill.a11y.image.preprocessor.emotion"]
    json2 = preprocessors["ca.mcgill.a11y.image.preprocessor.clothesDetector"]
    emotion = json1["person_emotion"]
    cloth = json2["clothes"]
    celeb = json["celebrities"]
    data = []
    # the expected output should be
    # {[id, emotion, celebrity, clothes]}
    for i in range(len(emotion)):
        json_data = {}
        id = emotion[i]["personID"]
        for j in range(len(cloth)):
            if (cloth[j]["personID"] == id):
                json_data["clothes"] = cloth[j]["attire"]
        for j in range(len(celeb)):
            if (celeb[j]["personID"] == id):
                json_data["celeb"] = celeb[j]
        json_data["emotion"] = emotion[i]["emotion"]["emotion"]
        json_data["confidence"] = emotion[i]["emotion"]["confidence"]
        json_data["id"] = emotion[i]["personID"]
        data.append(json_data)
    preprocessors["ca.mcgill.a11y.image.preprocessor.originalFormat"] = {
        "data": data}
    return preprocessors


def format_json(objects, change, preprocessors):
    multiple_flag = False
    emotion_flag = False
    just_person_count = check_multiple(objects, False)
    if (just_person_count >= 3):
        multiple_flag = True
    if ("ca.mcgill.a11y.image.preprocessor.emotion" in preprocessors):
        of = preprocessors["ca.mcgill.a11y.image.preprocessor.originalFormat"]
        emotion = of["data"]
        emotion_flag, cloth_flag, no_none_emotion = rendering_emotion(emotion)
        if (emotion_flag):
            # expected output will contain the information of an individual,
            # for instance a sample output of this function will be
            # {
            # ["object",
            # "emotion",
            # "celebrity",
            # "clothes"
            # "position"]
            # }
            object_emotion = get_ideal_format(
                objects, no_none_emotion, preprocessors)
            # add inanimated objects to the aforementioned output
            object_emotion_inanimate = inanimated_interaction(
                object_emotion, objects)
        else:
            object_emotion_inanimate = []
    return (
        multiple_flag,
        emotion_flag,
        object_emotion_inanimate,
        objects,
        just_person_count,
        cloth_flag)
