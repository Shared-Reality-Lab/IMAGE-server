# removes low confidence predictions.
# In this case we have assumed 0.3 to be the confidence threshold
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

# this function checks if there are people in the input image.
# This is the Stage 1 of the handler, that checks if the input image
# should be rendered by the handler


def custom_check(preprocessors):
    possible_people = 0
    od_prep = "ca.mcgill.a11y.image.preprocessor.objectDetection"
    sort_prep = "ca.mcgill.a11y.image.preprocessor.sorting"
    segment_prep = "ca.mcgill.a11y.image.preprocessor.semanticSegmentation"
    objects = preprocessors[od_prep]['objects']
    # remove low confidence predictions
    objects_high_conf, left2right = remove_low_confidence(
        objects, preprocessors[sort_prep]["leftToRight"])
    # sort according to decreasing confidence
    objects_sorted = sorted(
        objects_high_conf,
        key=lambda d: d['area'],
        reverse=True)
    area = 0.0
    # check if Object detector detected people in the image
    for i in range(len(objects_sorted)):
        if ("person" in objects_sorted[i]["type"]
                and objects_sorted[i]["confidence"] > 0.30):
            area += objects_sorted[i]["area"] * 100
            possible_people += 1
            break
    # check if semantic segmentation detected people in the image
    segments = preprocessors[segment_prep]["segments"]
    for i in range(len(segments)):
        if (segments[i]["name"] == "person" and segments[i]["area"] >= 0.05):
            possible_people = possible_people + 1
            break
    return possible_people
