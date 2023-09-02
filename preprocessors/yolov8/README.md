This preprocessor detects the objects present in the image. The entire code for this preprocessor has been refered from [ultralytics Repository](https://github.com/ultralytics/ultralytics).

In order to run this preprocessor we have used the [ultralytics YOLOv8 image](https://hub.docker.com/r/ultralytics/ultralytics) as a base docker image. The image is versioned with tag 'latest' and digest 'sha256:af4572bf0df164d5708e4a1f50bddb5a74cb7d793fe46b7daf42b1768fbec608'. The following commands import the base docker image:

```docker build -t <image-name>``` 

```docker run -p <port-number>:5000 <image-name>```

The confidence threshold can be adjusted in the Dockerfile by changing the variable 'c_thres' at the top of detect.py

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License |

The versions of the above mentioned library can be found in ```Dockerfile```


