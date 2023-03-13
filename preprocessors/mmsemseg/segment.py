import torch
from mmseg.apis import inference_segmentor, init_segmentor
import mmseg
import mmcv

from time import time
import argparse
import logging
import os


BEIT_CONFIG = "upernet_beit-base_8x2_640x640_160k_ade20k.py"
BEIT_CHECKPOINT = "upernet_beit-base_8x2_640x640_160k_ade20k-eead221d.pth"

VIT_CONFIG = "mmsegmentation/configs/vit/upernet_vit-b16_mln_512x512_80k_ade20k.py"
VIT_CHECKPOINT = "mmsegmentation/models/upernet_vit-b16_mln_512x512_80k_ade20k_20210624_130547-0403cee1.pth"

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

def main(config_file, checkpoint_file, image_folder, output_folder):
    # empty gpu cache
    torch.cuda.empty_cache()

    # create output folder
    os.makedirs(output_folder, exist_ok=True)

    # init logger
    logging.basicConfig(filename=os.path.join(output_folder, "log.txt"), level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
    logging.info(f"Starting segmentation with config file {config_file} and checkpoint file {checkpoint_file}.")


    # build the model from a config file and a checkpoint file
    model = init_segmentor(config_file, checkpoint_file, device='cuda:1')

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