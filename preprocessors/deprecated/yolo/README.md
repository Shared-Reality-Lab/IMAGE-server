# [DEPRECATED]: This preprocessor is no longer used in production. IMAGE uses yolov8 preprocessor present [here](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/yolov8)

This preprocessor detects the objects present in the image. The entire code for this preprocessor has been refered from [YOLOv5 Repository](https://github.com/ultralytics/yolov5).

In order to run this preprocessor we have used the [YOLOv5 image](https://hub.docker.com/r/ultralytics/yolov5) as a base docker image.The following commands import the base docker image:

```docker build -t <image-name>``` (pulls in the YOLOv6 version) 

```docker run -p <port-number>:5000 <image-name>```


The above mentioned commands will run the YOLOv6 version avalable in Docker Hub. In order to make the v6 version compatible with our architecture we have made a few changes in detect.py. The detect.py has been commented approprately to highlight the changes.

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License |

The versions of the above mentioned library can be found in ```Dockerfile```


