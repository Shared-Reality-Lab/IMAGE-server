""" This is the main file for the segmentation preprocessor, it should be remained 'segment.py' once it's working properly."""

from flask import Flask, request, jsonify
import gc
import json
import jsonschema
import base64


import torch
from mmseg.apis import inference_segmentor, init_segmentor
import mmseg
import mmcv
import numpy as np
import cv2

from utils import visualize_result, findContour

from time import time
import logging
import os

# configuration and checkpoint files
BEIT_CONFIG = "/app/upernet_beit-base_8x2_640x640_160k_ade20k.py"
BEIT_CHECKPOINT = "/app/upernet_beit-base_8x2_640x640_160k_ade20k-eead221d.pth"

# get the color palette used and class names
COLORS = mmseg.core.evaluation.get_palette("ade20k")
CLASS_NAMES = mmseg.core.evaluation.get_classes("ade20k")

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

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
        print(result)
        print(f"result length: {len(result)}")
        print(f"Segmentation shape: {result[0].shape}")
        end = time()

        pred = result[0].astype(np.uint8)
        
        predicted_classes = np.bincount(pred.flatten()).argsort()[::-1]
        for class_id in predicted_classes[:5]:
            print(f"Class id: {class_id}")
            print(f"Class name: {CLASS_NAMES[class_id]}")
        
        pred_color = visualize_result(img, pred, index = predicted_classes[0])
        print(f"pred_color shape: {pred_color.shape}")

        # logs the time it took to segment the image
        img_name = os.path.basename(img_file).split(".")[0]
        logging.info(f"Segmented {img_name} in {end - start:.2f} seconds. Classes found: {[class_name for class_name, _ in predicted_classes]}")

        # save image with overlapping segmentation
        model.show_result(img, result, out_file=os.path.join(output_folder, f"{img_name}_segmented.png"), opacity=0.7)
    
    # empty gpu cache
    torch.cuda.empty_cache()


def run_segmentation(url, model, dictionnary):
    # convert an image from base64 format
    # Following 4 lines refered from
    # https://gist.github.com/daino3/b671b2d171b3948692887e4c484caf47
    logging.info("converting base64 to numpy array")

    image_b64 = url.split(",")[1]
    binary = base64.b64decode(image_b64)
    image = np.asarray(bytearray(binary), dtype="uint8")
    image_np = cv2.imdecode(image, cv2.IMREAD_COLOR)
    
    # rescale the image
    height, width, channels = image_np.shape
    scale_factor = float(1500.0 / float(max(height, width)))

    logging.info("graphic oiginal dimension {}".format(image_np.shape))
    
    if scale_factor <= 1.0:
        logging.info("scaling down an image")

        image_np = mmcv.imrescale(image_np, scale_factor)

        logging.info("graphic scaled dimension: {}".format(image_np.shape))

    height, width, channels = image_np.shape

    # infer the segmentation
    logging.info("running segmentation model")
    try :
        result = inference_segmentor(model, image_np)
    except Exception as e:
        logging.error("error while running segmentation model : {}".format(e))
        
    
    logging.info("run finished")

    # extracting contours
    pred = result[0].astype(np.int32)
    predicted_classes = np.bincount(pred.flatten()).argsort()[::-1]
    logging.info("main classes detected : {}".format(predicted_classes[:5]))
    
    for class_id in predicted_classes[:5]:
        logging.info("extracting contours for class: {}".format(str(class_id)))
        
        pred_color, class_name = visualize_result(pred, index = class_id)
        contour, center, area = findContour(pred_color, width, height)
        
        logging.info("contour extraction finished")

        if area == 0:
            continue
        dictionnary.append({
            "name": class_name,
            "area": area,
            "centroid": center,
            "contours": contour
        })
    
    logging.info("segmentation finished")
    return {'segments': dictionnary}


@app.route("/preprocessor", methods=["POST", "GET"])
def segment():
    logging.debug("Received request")
    gc.collect()
    torch.cuda.empty_cache()
    dictionnary = []

    # load the schemas
    with open('./schemas/preprocessors/segmentation.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    # Following 6 lines refered from
    # https://stackoverflow.com/questions/42159346/jsonschema-refresolver-to-resolve-multiple-refs-in-python
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
    logging.info("Schemas loaded")

    # load the model
    try:
        model = init_segmentor(BEIT_CONFIG, BEIT_CHECKPOINT, device='cuda:0')
    except RuntimeError as e:
        if 'out of memory' in str(e):
            logging.error('CUDA out of memory.')
            return jsonify({"error": "CUDA out of memory."}), 500
    logging.info("Model loaded")

    # get the request
    request_json = request.get_json()

    # validate the request
    try:
        validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
        validator.validate(request_json)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(f"Request validation error: {e.message}")
        return jsonify("Invalid Preprocessor JSON format"), 400
    
    if "graphic" not in request_json:
        logging.info("Not image content. Skipping ...")
        return '', 204
    
    request_uuid = request_json["request_uuid"]
    timestamp = time()

    preprocessor_name = "ca.mcgill.a11y.image.preprocessor.semanticSegmentation"
    classifier_1 = "ca.mcgill.a11y.image.preprocessor.contentCategoriser"
    classifier_2 = "ca.mcgill.a11y.image.preprocessor.graphicTagger"
    preprocess_output = request_json["preprocessors"]

    # check if the first classifier and second classifier are present.
    # these steps could be skipped
    # if the architecture is modified appropriately
    if classifier_1 in preprocess_output:
        classifier_1_output = preprocess_output[classifier_1]
        classifier_1_label = classifier_1_output["category"]
        if classifier_1_label != "photograph":
            logging.info(
                "Not photograph content. Skipping...")

            return "", 204
        if classifier_2 in preprocess_output:
            # classifier_2_output = preprocess_output[classifier_2]
            # classifier_2_label = classifier_2_output["category"]
            # if classifier_2_label != "outdoor":
            #     logging.info("Cannot process image")
            #     return "", 204
            segment = run_segmentation(request_json["graphic"], model, dictionnary)
        else:
            """We are providing the user the ability to process an image
            even when the second classifier is absent, however it is
            recommended to the run the semantic segmentation
            model in conjunction with the second classifier."""
            segment = run_segmentation(request_json["graphic"], model, dictionnary)
    else:
        """We are providing the user the ability to process an image
        even when the first classifier is absent, however it is
        recommended to the run the semantic segmentation
        model in conjunction with the first classifier."""
        segment = run_segmentation(request_json["graphic"], model, dictionnary)

    torch.cuda.empty_cache()

    # validate the data format for the output
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(segment)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    
    response = {
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": preprocessor_name,
        "data": segment
    }
    
    # validate the output format
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    
    logging.info("Valid response generated")

    return response


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port = 5000, debug = True)