# Multistage Diagram Segmentation Preprocessor

Alpha quality: not yet ready for use by end-users.

This preprocessor analyzes flow diagrams and process charts to extract structured information about stages, their dependencies, and visual representations. It produces a comprehensive JSON output containing:

1. Stage information (names, descriptions)
2. Connection information (links between stages)
3. Segmentation data (contours, centroids, and areas for each identified stage)

The preprocessor uses computer vision AI models to:
- Identify diagram elements using Google's Gemini API
- Generate precise segmentation masks using SAM 2.1 (Segment Anything Model)

## Environment Variables

Environment variables to be set for :

```
GOOGLE_API_KEY=[Your Google API Key]
SAM_MODEL_PATH=[Path to SAM model file]
GEMINI_MODEL=gemini-2.5-pro-exp-03-25
PII_LOGGING_ENABLED=[true or false]
BASE_SCHEMA=[location of the schema used by Gemini for the initial data extraction]
```

Note: For production use, it's strongly recommended to set PII_LOGGING_ENABLED=false to prevent security risks.
Logging personal information should only be done on test servers. The preprocessor uses a 'logging.pii()' function that should be properly configured by the logging utilities module.

## Libraries Used

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Flask | [Link](https://pypi.org/project/Flask/) | BSD-3-Clause License |
| requests | [Link](https://pypi.org/project/requests/) | Apache 2.0 |
| jsonschema | [Link](https://pypi.org/project/jsonschema/) | MIT License |
| gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License |
| pillow | [Link](https://pypi.org/project/Pillow/) | MIT-CMU |
| google-genai | [Link](https://pypi.org/project/google-genai/) | Apache 2.0 |
| google-api-core | [Link](https://pypi.org/project/google-api-core/) | Apache 2.0 |
| opencv-python | [Link](https://pypi.org/project/opencv-python/) | Apache 2.0 |
| ultralytics | [Link](https://pypi.org/project/ultralytics/) | AGPL-3.0 License |

The versions for each of these libraries are specified in `requirements.txt`

## API Endpoints

- `/preprocessor` (POST): Main endpoint for diagram processing
- `/health` (GET): Health check endpoint

## Processing Pipeline

1. Image decoding from base64
2. Initial diagram analysis with Gemini API
3. Bounding box detection for identified stages
4. Segmentation using SAM model
5. Contour extraction and normalization
6. JSON response construction with validation