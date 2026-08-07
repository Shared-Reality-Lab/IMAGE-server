# Object Detection LLM Preprocessor

Beta quality: Useful enough for testing by end-users.

This preprocessor detects and localizes objects in images using LLM-based computer vision. It analyzes photos, collages, and illustrations to produce structured JSON output containing:

1. Detected objects with labels and descriptions
2. Normalized bounding box coordinates for each object
3. Confidence scores for detection accuracy

## Environment Variables

Environment variables to be set:

```
CONF_THRESHOLD=[Minimum confidence threshold for object detection, default: 0.9]
PII_LOGGING_ENABLED=[true or false]
```
**Note**: For production use, it's strongly recommended to set PII_LOGGING_ENABLED=false to prevent security risks. Logging personal information should only be done on test servers. The preprocessor uses a 'logging.pii()' function that should be properly configured by the logging utilities module.

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
| jsonschema | [Link](https://pypi.org/project/jsonschema/) | MIT License |
| Werkzeug | [Link](https://pypi.org/project/Werkzeug/) | BSD-3-Clause License |
| gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License |
| requests | [Link](https://pypi.org/project/requests/) | Apache 2.0 |
| openai | [Link](https://pypi.org/project/openai/) | Apache 2.0 |
| pillow | [Link](https://pypi.org/project/Pillow/) | MIT-CMU |
| qwen-vl-utils | [Link](https://pypi.org/project/qwen-vl-utils/) | Apache 2.0 |
| torch | [Link](https://pytorch.org/) | BSD-3-Clause License |
| torchvision | [Link](https://pytorch.org/) | BSD-3-Clause License |

The versions for each of these libraries are specified in `requirements.txt`

## API Endpoints

- `/preprocessor` (POST): Main endpoint for object detection
- `/health` (GET): Health check endpoint
- `/warmup` (GET): Model warmup endpoint

## Processing Pipeline

1. Request validation and content type checking
2. Content categorization filter (processes only photos, collages, and illustrations)
3. Image decoding from base64 and resizing
4. Object detection using LLM vision model
5. Bounding box normalization to [0,1] coordinate range
6. Confidence-based filtering of detections
7. Schema validation and JSON response construction