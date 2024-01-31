# Expression Recognition Preprocessor

This preprocessor has been designed to recognize human expressions and categorize them as `happy, neutral, or sad`. It is built on the Deepface library, which offers a variety of models like `FaceNet, Openface, DeepFace,` and more. The models can be easily switched by specifying the `detector_backend` parameter when calling the `Deepface.analyze` function. For more information on model selection, please refer to the [Deepface Readme](https://github.com/serengil/deepface).

To use this module as an API, you can follow the example provided in the `emotion-recognition.py` file. The necessary dependencies and their associated versions are clearly specified in the `requirements.txt`

However, it's crucial to be aware that AI models can inherit biases present in the training data, which may lead to inaccurate predictions. For instance, a well-known emotion recognition model once incorrectly detected that African-American NBA players appeared twice as angry as their white counterparts [1]. Consequently, it's essential to exercise caution when using such models, as they can produce offensive or biased results.


## Installation

In order to use this module as an API, first build the image using :

```bash
docker build -t <image-name>
```

Then run the container with :

```bash
docker run -d --rm --gpus all -p <port>:5000 <image-name>
```

## References
[1] Rhue, Lauren. "Racial influence on automated perceptions of emotions." Available at SSRN 3281765 (2018), DOI: https://dx.doi.org/10.2139/ssrn.3281765
