This preprocessor is used for segmenting an image. The entire code for this preprocessor has been refered from [CSAILVision Semantic Segmentation Repository](https://github.com/CSAILVision/semantic-segmentation-pytorch/blob/master/LICENSE). 



The code for converting the repository to an API can be found in ```segment.py```. The versions for all the mentioned libraries can be found in ```requirements.txt```


In order to run the API as a docker container use the following commands:
```docker build -t <image-name>```
```docker run --gpus all --publish <port>:5000 <image-name>```


The main code changes have occurred in ```segment.py```. Appropriate comments have been added to the ```segment.py``` to improve the readability. 

The code from [CSAILVision Semantic Segmentation Repository](https://github.com/CSAILVision/semantic-segmentation-pytorch/blob/master/LICENSE) has been converted into API using the following libraries: 

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Flask | [Link](https://pypi.org/project/Flask/)  | BSD-3-Clause License|
| Numpy | [Link](https://pypi.org/project/numpy/)  | BSD-3-Clause License|
| Pillow | [Link](https://pypi.org/project/Pillow/)  | Historical Permission Notice and Disclaimer (HPND)|
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License|
| Werkzeug | [Link](https://pypi.org/project/Werkzeug/) | BSD-3 |
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |
| Flask_API | [Link](https://pypi.org/project/Flask-API/) | OSI Approved: BSD License |
| Requests  | [Link](https://pypi.org/project/requests/)  | Apache 2.0|
| opencv-python | [Link](https://github.com/skvark/opencv-python) | MIT License(MIT) |
| Torch | [Link](https://github.com/pytorch/pytorch/blob/master/LICENSE) | BSD License (BSD-3)|
| Torchvision | [Link](https://github.com/pytorch/vision/blob/main/LICENSE) | BSD-3-Clause License |
| Scipy | [Link](https://github.com/scipy/scipy) | BSD License | 
