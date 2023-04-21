# Semantic Segmentation module

This preprocessor is used for semantically segmenting images. The code for this preprocessor heavily relies on the [MMSegmentation](https://github.com/open-mmlab/mmsegmentation) framework.

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
