""" This is the main file for the segmentation preprocessor, it should be remained 'segment.py' once it's working properly."""


import torch
from mmseg.apis import inference_segmentor, init_segmentor
import mmseg
import mmcv

import cv2
import numpy as np

from time import time
import argparse
import logging
import os

# configuration and checkpoint files
BEIT_CONFIG = "upernet_beit-base_8x2_640x640_160k_ade20k.py"
BEIT_CHECKPOINT = "upernet_beit-base_8x2_640x640_160k_ade20k-eead221d.pth"

# get the color palette used and class names
COLORS = mmseg.core.evaluation.get_palette("ade20k")
CLASS_NAMES = mmseg.core.evaluation.get_classes("ade20k")

def get_args():
    parser = argparse.ArgumentParser(
        description="Run the demo on all images in the dataset. And with all possible configurations. Logs are saved in a logfile."
    )
    parser.add_argument(
        "-i",
        "--image_folder",
        type=str,
        required=True,
        help="Path to the folder containing the images.",
    )
    parser.add_argument(
        "-o",
        "--output_folder",
        type=str,
        required=True,
        help="Path to the folder where the output will be saved.",
    )
    parser.add_argument(
        "--config_file",
        type=str,
        default=BEIT_CONFIG,
        help="Path to the folder containing the config files.",
    )
    parser.add_argument(
        "--checkpoint_file",
        type=str,
        default=BEIT_CHECKPOINT,
    )
    args = parser.parse_args()
    return args

# Removes the remaining segments and only highlights the segment of
# interest with a particular color.
def visualize_result(img, pred, index=None):
    if index is not None:
        pred = pred.copy()
        pred[pred != index] = -1

    logging.info("encoding detected segmets with unique colors")

    pred_color = colorEncode(pred, COLORS).astype(np.uint8) # TODO : Ask Rohan what it does 
    nameofobj = CLASS_NAMES[index + 1]

    return pred_color, nameofobj

# takes the colored segment(determined in visualise_reslt function and
# compressed the segment to 100 pixels


def findContour(pred_color, width, height):
    image = pred_color
    dummy = pred_color.copy()
   
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(gray_image, 10, 255, cv2.THRESH_BINARY)

    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

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

def main(config_file, checkpoint_file, image_folder, output_folder):
    # empty gpu cache
    torch.cuda.empty_cache()

    # create output folder
    os.makedirs(output_folder, exist_ok=True)

    # init logger
    logging.basicConfig(filename=os.path.join(output_folder, "log.txt"), level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
    logging.info(f"Starting segmentation with config file {config_file} and checkpoint file {checkpoint_file}.")


    # build the model from a config file and a checkpoint file
    model = init_segmentor(config_file, checkpoint_file, device='cuda:1') # TODO : change the device to cuda:0 after changing the container gpu to 1

    # test a single image and show the results
    img_files = [os.path.join(image_folder, image_file) for image_file in os.listdir(image_folder)]

    for img_file in img_files:
        # load image with opneCV
        img = mmcv.imread(img_file)

        # rescale the image 
        img = mmcv.imrescale(img, 0.5) # TODO : rescale based on the size of the image

        # infer the segmentation
        start = time()
        result = inference_segmentor(model, img)
        end = time()

        # get the color palette used and class names
        palette = mmseg.core.evaluation.get_palette("ade20k")
        class_names = mmseg.core.evaluation.get_classes("ade20k")

        # find classes that are on the image and save them in a list with their color
        classes = []
        for i in range(len(class_names)):
            if i in result[0]:
                classes.append((class_names[i], palette[i]))
        
        
        # logs the time it took to segment the image
        img_name = os.path.basename(img_file).split(".")[0]
        logging.info(f"Segmented {img_name} in {end - start:.2f} seconds. Classes found: {[class_name for class_name, _ in classes]}")

        # save image with overlapping segmentation
        model.show_result(img, result, out_file=os.path.join(output_folder, f"{img_name}_segmented.png"), opacity=0.7)
    
    # empty gpu cache
    torch.cuda.empty_cache()



if __name__ == "__main__":
    args = get_args()
    
    main(args.config_file, args.checkpoint_file, args.image_folder, args.output_folder)