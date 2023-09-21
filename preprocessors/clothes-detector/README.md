# Clothes Detection Preprocessor

This preprocessor detects clothes of individual person in an image. The following are the steps performed by the preprocessor

1. We first crop individual people from the image, then detect the clothes worn by each individual. We have used YOLOv3 in the backend to detect and localise the clothes worn by each individual. The weights were obtained from [[another github repository](https://github.com/simaiden/Clothing-Detection)](https://github.com/simaiden/Clothing-Detection)
2. The localised clothes are further cropped to determine the color of those clothes. The cropped clothes are passed through a `webcolors` library, that provides the dominant color of the assiciated cloth.


The code to use this module as an API can be found in `clothes.py`. This module is fully versioned. The versions of the libraries used can be found in `requirements.txt`. The weights for the model and the procedure to convert the model to image could be found in `Dockerfile`. 



## Installation

In order to use this module as an API, first build the image using :

```bash
docker build -t <image-name>
```

Then run the container with :

```bash
docker run -d --rm --gpus all -p <port>:5000 <image-name>
```
