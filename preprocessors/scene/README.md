This preprocessor tries to detect the scene of the image. The entire code for the preprocessor has been refered from [CSAILVision github repository](https://github.com/CSAILVision/places365).

The github repository has been converted into an API and the code for the same can be found in ``` run_placesCNN_unified.py ```. 

The following libraries are used to convert the [CSAILVision github repository](https://github.com/CSAILVision/places365) to an API

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

The versions for the librraies can be found in ```requirements.txt```
