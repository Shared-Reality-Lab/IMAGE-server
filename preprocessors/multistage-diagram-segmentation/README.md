# Multistage Diagram Segmentation Preprocessor

Alpha quality: not yet ready for use by end-users.

This preprocessor analyzes flow diagrams and process charts to extract structured information about stages, their dependencies, and visual representations. It produces a comprehensive JSON output containing:

1. Stage information (names, descriptions)
2. Connection information (links between stages)
3. Segmentation data (contours, centroids, and areas for each identified stage)

The preprocessor uses computer vision AI models to:
- Identify diagram elements
- Generate precise segmentation masks using SAM 2.1 (Segment Anything Model)

## Environment Variables

Environment variables to be set for :

```
SAM_MODEL_PATH=[Path to SAM model file]
PII_LOGGING_ENABLED=[true or false]
BASE_SCHEMA=[location of the schema used by Gemini for the initial data extraction]
```

**Note**: For production use, it's strongly recommended to set PII_LOGGING_ENABLED=false to prevent security risks.
Logging personal information should only be done on test servers. The preprocessor uses a 'logging.pii()' function that should be properly configured by the logging utilities module.

Additional environment variables required for the LLM client (`utils/llm/client.py`):
```
LLM_API_KEY=sk-[your-api-key]
LLM_URL=[OpenAI-compatible VLM endpoint]
LLM_MODEL=[Model name]
```
**Note**: This preprocessor supports the Qwen (currently Qwen 3 VL onwords) and Gemma VL model families for bounding box detection, and can be extended to additional model families by adding an entry to `MODEL_BBOX_FORMATS` in `utils/llm/coordinate_convention.py`. The active model's bounding-box key name and coordinate order are detected automatically from `LLM_MODEL`; an unsupported model will cause the service to fail at startup with a clear error.

**Tech Debt**: Coordinate format is currently resolved at the model-*family* level (e.g., all "Qwen" models), not per version. This is safe for the versions currently in use, but Qwen's own coordinate convention has changed across versions (Qwen 2.5 VL uses absolute pixel coordinates, while Qwen 3 VL and later (including Qwen 3.5) use normalized 0–1000 coordinates, matching what this preprocessor currently assumes for the "qwen" family). If any future model families or model versions with differing coordinate conventions need to be supported, `get_model_family()`/`MODEL_BBOX_FORMATS` in `utils/llm/coordinate_convention.py` would need to be extended to resolve by specific model version, not just family.

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
2. Initial diagram analysis
3. Bounding box detection for identified stages
4. Segmentation using SAM model
5. Contour extraction and normalization
6. JSON response construction with validation