# Semantic Segmentation module

Beta quality: Useful enough for testing by end-users.

This preprocessor semantically segments images using the [MMSegmentation](https://github.com/open-mmlab/mmsegmentation) framework, but only returns "stuff"/background-type segments (e.g. sky, wall, floor, road) as classified by [ADE20K SceneParsing150](https://github.com/CSAILVision/sceneparsing/blob/master/objectInfo150.csv) - environmental elements that an object detector wouldn't catch. Foreground objects (people, furniture, vehicles, etc.) are segmented with far more precise outlines by `object-detection-llm` + `object-segmentation` (SAM 3) instead.

The code to use this module as an API can be found in `segment.py`, additional functions are located in `utils.py`. This module is fully versionned, the versions of the libraries used can be found in `requirements.txt` and in the `Dockerfile`.

## Installation

In order to use this module as an API, first build the image using :

```bash
docker build -t <image-name>
```

Then run the container with :

```bash
docker run -d --rm --gpus all -p <port>:5000 <image-name>
```

## How to change the model used

Currently the model used is [BEIT base](https://github.com/open-mmlab/mmsegmentation/tree/master/configs/beit). However, this module allows for a great modularity, here are the instructions to modify the semantic segmentation model used :

* Download both the config and the checkpoint files for the new model, using [MIM](https://github.com/open-mmlab/mmsegmentation/blob/master/docs/en/get_started.md#installation).
* Put the new model checkpoint on pegasus.
* Update `line 47` in the `Dockerfile` with the location of the new checkpoint file.
* Put the config file for the new model in the `config` folder.
* Change the config and checkpoint paths used, at the top of the `segment.py` file.
