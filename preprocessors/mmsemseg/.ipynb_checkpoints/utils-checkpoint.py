import numpy as np
import cv2
import logging
import mmseg

# get the color palette used and class names
COLORS = mmseg.core.evaluation.get_palette("ade20k")
CLASS_NAMES = mmseg.core.evaluation.get_classes("ade20k")

def unique(ar, return_index=False, return_inverse=False, return_counts=False):
    ar = np.asanyarray(ar).flatten()

    optional_indices = return_index or return_inverse
    optional_returns = optional_indices or return_counts

    if ar.size == 0:
        if not optional_returns:
            ret = ar
        else:
            ret = (ar,)
            if return_index:
                ret += (np.empty(0, np.bool),)
            if return_inverse:
                ret += (np.empty(0, np.bool),)
            if return_counts:
                ret += (np.empty(0, np.intp),)
        return ret
    if optional_indices:
        perm = ar.argsort(kind='mergesort' if return_index else 'quicksort')
        aux = ar[perm]
    else:
        ar.sort()
        aux = ar
    flag = np.concatenate(([True], aux[1:] != aux[:-1]))

    if not optional_returns:
        ret = aux[flag]
    else:
        ret = (aux[flag],)
        if return_index:
            ret += (perm[flag],)
        if return_inverse:
            iflag = np.cumsum(flag) - 1
            inv_idx = np.empty(ar.shape, dtype=np.intp)
            inv_idx[perm] = iflag
            ret += (inv_idx,)
        if return_counts:
            idx = np.concatenate(np.nonzero(flag) + ([ar.size],))
            ret += (np.diff(idx),)
    return ret

def colorEncode(labelmap, colors, mode='RGB'):
    labelmap = labelmap.astype('int32') # TODO : -1 which was present in the default labelmap is encoded as 255 because of the uint8 type, find better type
    labelmap_rgb = np.zeros((labelmap.shape[0], labelmap.shape[1], 3),
                            dtype=np.uint8)
    
    # BUG : 255 is not a valid index for colors, comes from the uint8 type
    print(f"unique labelmap : {np.unique(labelmap)}")
    labels = unique(labelmap)
    print(f"labels : {labels}")
    for label in labels:
        print(f"label : {label}")
        print(f"colors[label] : {colors[label]}")
        if label < 0:
            continue
        labelmap_rgb += ((labelmap == label)[:, :, np.newaxis] * \
            np.tile(colors[label], (labelmap.shape[0], labelmap.shape[1], 1))).astype(np.uint8)

    if mode == 'BGR':
        return labelmap_rgb[:, :, ::-1]
    else:
        return labelmap_rgb

# Removes the remaining segments and only highlights the segment of
# interest with a particular color.
def visualize_result(img, pred, index=None):
    if index is not None:
        pred = pred.copy()
        pred[pred != index] = -1

    logging.info("encoding detected segmets with unique colors")

    # INFO : replaces the index of the class with its RGB color
    pred_color = colorEncode(pred, COLORS).astype(np.uint8) 
    object_name = CLASS_NAMES[index]

    return pred_color, object_name

# takes the colored segment(determined in visualise_reslt function and
# compressed the segment to 100 pixels


def findContour(pred_color, width, height):
    image = pred_color
    dummy = pred_color.copy()
   
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _ , thresh = cv2.threshold(gray_image, 10, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    logging.info("Total contours detected are: {}".format(len(contours)))

    cv2.drawContours(image, contours, -1, (0, 255, 0), 2)
    
    # removes the remaining part of image and keeps the contours of segments
    logging.info("deleting remainder of the image except the contours")

    image = image - dummy # TODO : Free dummy memory after this line for optimization
    centres = []
    area = []
    totArea = 0
    send_contour = []
    flag = False

    # calculate the centre and area of individual contours
    logging.info("computing individual contour metrics")

    for i in range(len(contours)):
        moments = cv2.moments(contours[i])

        if moments['m00'] == 0:
            continue
        # if contour area for a given class is very small then omit that
        if cv2.contourArea(contours[i]) < 2000:
            continue

        totArea = totArea + cv2.contourArea(contours[i])
        area.append(cv2.contourArea(contours[i]))
        centres.append(
            (int(moments['m10'] / moments['m00']),
             int(moments['m01'] / moments['m00'])))
        
        area_indi = cv2.contourArea(contours[i])
        centre_indi = (int(moments['m10'] / moments['m00']), int(moments['m01'] / moments['m00']))
        contour_indi = [list(x) for x in contours[i]]
        contour_indi = np.squeeze(contour_indi)
        centre_down = [centre_indi[0] / width, centre_indi[1] / height]
        area_down = area_indi / (width * height)
        
        contour_indi = contour_indi.tolist()
        logging.info("Iterating through individual contours")
        for j in range(len(contour_indi)):
            contour_indi[j][0] = float(float(contour_indi[j][0]) / width)
            contour_indi[j][1] = float(float(contour_indi[j][1]) / height)

        logging.info("End contour iteration ")
        send_contour.append({"coordinates": contour_indi, "centroid": centre_down, "area": area_down})
        
    logging.info("computed all metrics!!")

    if not area:
        flag = True
    else:
        max_value = max(area)
    if flag is True:
        return ([0, 0], [0, 0], 0)
    
    logging.info("generating overall centroid and area")
    centre1 = centres[area.index(max_value)][0] / width
    centre2 = centres[area.index(max_value)][1] / height
    centre = [centre1, centre2]
    totArea = totArea / (width * height)
    result = np.concatenate(contours, dtype=np.float32)

    # if contour is very small then delete it
    if totArea < 0.05:
        return ([0, 0], [0, 0], 0)
    
    result = np.squeeze(result)
    result = np.swapaxes(result, 0, 1)
    result[0] = result[0] / float(width)
    result[1] = result[1] / float(height)
    # send = np.swapaxes(result, 0, 1).tolist()
    return send_contour, centre, totArea