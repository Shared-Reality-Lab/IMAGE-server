

def get_position(object_emotion_inanimate, person_count, rendering):
    posi = []
    print(person_count)
    if (person_count == 1):
        try:
            x_val = object_emotion_inanimate[0]['objects']['centroid'][0]
        except BaseException:
            x_val = 0.5
        if (x_val < 0.3):
            posi.append(['left'])
        elif (x_val > 0.7):
            posi.append(['right'])
        else:
            posi.append(['middle'])
        rendering += " , in the " + posi[0][0] + " "
    elif (person_count == 2):
        if (len(object_emotion_inanimate) < 2):
            posi.append(['', ''])
        else:
            x_val1 = object_emotion_inanimate[0]['objects']['centroid'][0]
            x_val2 = object_emotion_inanimate[1]['objects']['centroid'][0]
            if (x_val1 < 0.3):
                if (x_val2 < 0.3):
                    posi.append(['left', 'left'])
                elif (x_val2 >= 0.3 and x_val2 <= 0.6):
                    posi.append(['left', 'middle'])
                else:
                    posi.append(['left', 'right'])
            elif (x_val1 >= 0.3 and x_val1 <= 0.6):
                if (x_val2 < 0.3):
                    posi.append(['middle', 'left'])
                elif (x_val2 >= 0.3 and x_val2 <= 0.6):
                    posi.append(['middle', 'middle'])
                else:
                    posi.append(['middle', 'right'])
            else:
                if (x_val2 < 0.3):
                    posi.append(['right', 'left'])
                elif (x_val2 >= 0.3 and x_val2 <= 0.6):
                    posi.append(['right', 'middle'])
                else:
                    posi.append(['right', 'right'])
        # print(posi)
        if (len(posi[0][0]) == 0):
            rendering += " "
        elif (posi[0][0] == posi[0][1]):
            rendering += " in the " + posi[0][0] + ' '
        elif (posi[0][0] == 'left'):
            if (posi[0][1] == 'middle'):
                rendering += " in the left and middle part of the image."
            else:
                rendering += " in the left and right end of image."
        elif (posi[0][0] == 'middle'):
            rendering += " in the middle and right part of the image."
    else:
        x_val = 0
        for i in range(len(object_emotion_inanimate)):
            x_val += object_emotion_inanimate[i]['objects']['centroid'][0]
        try:
            x_val /= len(object_emotion_inanimate)
        except ZeroDivisionError:
            posi.append(['middle'])
        if (x_val < 0.3):
            posi.append(['left'])
        elif (x_val > 0.7):
            posi.append(['right'])
        else:
            posi.append(['middle'])
        rendering += " in the " + posi[0][0]
    return rendering


def check_caption_inanimate(obj, caption):
    obj = obj.replace(" ", "")
    caption = ''.join(e for e in caption if e.isalnum())
    if (obj in caption):
        return False
    return True


def get_action(obj):
    vehicle = ["bicycle", "car", "motorcycle", "bus", "train", "truck", "boat"]
    outdoor = ["bench", "chair", "couch"]
    animal = [
        "bear",
        "bird",
        "cat",
        "dog",
        "cow",
        "elephant",
        "giraffe",
        "horse",
        "sheep",
        "zebra"]
    accessory = ["backpack", "handbag", "suitcase", "umbrella"]
    appliance = [
        "microwave",
        "oven",
        "refrigerator",
        "sink",
        "toaster",
        "wineglass"]
    misc = ["tie", ]
    electronic = ["cell phone", "laptop", "remote", "tv"]

    obj = obj.replace(" ", "")
    # print(obj)
    if (obj in vehicle):
        return " near a " + obj
    elif (obj in outdoor):
        return " on the " + obj
    elif (obj in animal):
        return " near a " + obj
    elif (obj in accessory):
        return " using a " + obj
    elif (obj in appliance):
        return " near a " + obj
    elif (obj in misc):
        # return " wearing a tie "
        return " "
    elif (obj in electronic):
        return " using a " + obj
    return "near a " + obj


def inanimate_rendering(inanimate_obj, rendering, caption):
    print("caption is", caption)
    rendering += caption
    if (len(inanimate_obj) > 2):
        rendering += " near a few objects like "
        for i in range(len(inanimate_obj)):
            if (check_caption_inanimate(inanimate_obj[0]["type"], caption)):
                rendering += inanimate_obj[i]["type"]
            if (i == 3):
                rendering += " etcetra."
                return rendering
            rendering += ", "
        rendering += "."
        return rendering
    elif (len(inanimate_obj) == 2):
        if (check_caption_inanimate(inanimate_obj[0]["type"], caption)):
            obj = inanimate_obj[0]["type"]
            rendering += get_action(obj)
        if (check_caption_inanimate(inanimate_obj[1]["type"], caption)):
            rendering += " and "
            obj = inanimate_obj[1]["type"]
            rendering += get_action(obj)
        return rendering
    elif (len(inanimate_obj) > 0):
        if (check_caption_inanimate(inanimate_obj[0]["type"], caption)):
            obj = inanimate_obj[0]["type"]
            rendering += get_action(obj)
            rendering += "."
        return rendering
    else:
        return rendering
