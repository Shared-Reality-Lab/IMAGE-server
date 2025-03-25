
# Object Detection Preprocessor

Beta quality: Useful enough for testing by end-users.

This preprocessor detects objects present in images using YOLOv11. 
The implementation builds upon the [Ultralytics](https://github.com/ultralytics/ultralytics) framework.

## Overview

The preprocessor identifies various objects in images and returns their positions, classifications, and confidence scores in a standardized JSON format.

## Docker Setup

This preprocessor uses the [Ultralytics image](https://hub.docker.com/r/ultralytics/ultralytics) as a base. The image is versioned with tag 'latest' and digest 'sha256:3d52e286bc345343b1a7a66dd38c44bb412bf418eb97d14298b8d8deb077f2e4'.

To build and run the container:

```bash
docker build -t object-detection .
docker run -p 5000:5000 object-detection
```

## Configuration

The preprocessor can be configured using the following environment variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| YOLO_MODEL_PATH | Path to the YOLOv11 model file | /usr/src/app/models/yolo11x.pt |
| CONF_THRESHOLD | Minimum confidence threshold for detection (0-1) | 0.75 |
| MAX_IMAGE_SIZE | Maximum image dimension for processing | 640 |

Example with custom configuration:

```bash
docker run -p 5000:5000 \
  -e CONF_THRESHOLD=0.65 \
  -e MAX_IMAGE_SIZE=320 \
  object-detection
```

## GPU Acceleration

For improved performance, the preprocessor supports GPU acceleration when run on a system with NVIDIA GPUs:

```bash
docker run --gpus all -p 5000:5000 object-detection
```

## Dependencies

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT |
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT |
| Flask | [Link](https://github.com/pallets/flask) | BSD 3-Clause |
| Pillow | [Link](https://github.com/python-pillow/Pillow) | MIT-CMU |
| Ultralytics (YOLO) | [Link](https://github.com/ultralytics/ultralytics) | AGPL-3.0 | 

The versions for each of these libraries is specified `requirements.txt`

## API Endpoints

### POST /preprocessor

Processes an image and returns detected objects.

**Input**: JSON object with a base64-encoded image in the "graphic" field.  
**Output**: JSON object containing detected objects with their positions and classifications.

### GET /health

Returns preprocessor status

**Output**: JSON object containing preprocessor status and timestamp