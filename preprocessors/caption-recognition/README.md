# Caption Recognition Preprocessor

This preprocessor provides a single sentence caption for the image. Currently the code uses [BLIP](https://github.com/salesforce/BLIP), which is a huggingface based vision transformer that can generate accurate captions.

The code to use this module as an API can be found in `caption.py`. This module is fully versionned, the versions of the libraries used can be found in `requirements.txt` and in the `Dockerfile`.


## Installation

In order to use this module as an API, first build the image using :

```bash
docker build -t <image-name>
```

Then run the container with :

```bash
docker run -d --rm --gpus all -p <port>:5000 <image-name>
```
