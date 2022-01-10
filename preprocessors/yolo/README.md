This preprocessor detects the objects present in the image. The entire code for this preprocessor has been refered from [YOLOv5 Repository](https://github.com/ultralytics/yolov5).

In order to run this preprocessor we have used the [YOLOv5 image](https://hub.docker.com/r/ultralytics/yolov5) as a base docker image. We have also used a few additional libraries in congruence with the YOLOv5 base image

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License |

The versions of the above mentioned library can be found in ```Dockerfile```
