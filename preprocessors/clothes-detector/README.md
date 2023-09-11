# Clothes Detection Preprocessor

This preprocessor detects clothes of individual person in an image. The preprocessor uses YOLOv3 trained on DeepFashion2 datastet. Following the clothes detection we try to detect the color of clothes using `webcolors` library.
The code to use this module as an API can be found in `clothes.py`. This module is fully versionned, the versions of the libraries used can be found in `requirements.txt`. The weights for the model and the procedure to convert the model to image could be found in `Dockerfile`. 
The weights were obtained from [another github repository](https://github.com/simaiden/Clothing-Detection)


## Installation

In order to use this module as an API, first build the image using :

```bash
docker build -t <image-name>
```

Then run the container with :

```bash
docker run -d --rm --gpus all -p <port>:5000 <image-name>
```
