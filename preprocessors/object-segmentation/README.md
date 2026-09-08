# Object Segmentation Preprocessor

Alpha quality: not yet ready for use by end-users.

This preprocessor segments objects already found by `object-detection-llm` using SAM 3 (Segment Anything Model), producing precise per-object polygon outlines rather than just bounding boxes. It does not run its own LLM inference - it consumes `object-detection-llm`'s existing bounding boxes as SAM prompts.

SAM 3's weights (`facebook/sam3` on Hugging Face) are gated: building this image requires an `HF_TOKEN` build secret from an account with approved access, passed via BuildKit's `--secret` (see the `Dockerfile` and `.github/workflows/object-segmentation.yml`). Never bake the token into an `ARG` - that would persist it in the image's layer history.

Output is shaped identically to the existing `semanticSegmentation` preprocessor's `segments` output (`schemas/preprocessors/segmentation.schema.json`), with an additional `objectID` field on each segment that ties it back to the detected object it came from.

## Environment Variables

```
SAM_MODEL_PATH=[Path to SAM model file]
MIN_CONTOUR_AREA=[Minimum normalized contour area to keep, default 0.0001]
PII_LOGGING_ENABLED=[true or false]
```

**Note**: For production use, it's strongly recommended to set `PII_LOGGING_ENABLED=false` to prevent security risks. Logging personal information should only be done on test servers. The preprocessor uses a `logging.pii()` function that should be properly configured by the logging utilities module.

## Libraries Used

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Flask | [Link](https://pypi.org/project/Flask/) | BSD-3-Clause License |
| jsonschema | [Link](https://pypi.org/project/jsonschema/) | MIT License |
| gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License |
| pillow | [Link](https://pypi.org/project/Pillow/) | MIT-CMU |
| opencv-python | [Link](https://pypi.org/project/opencv-python/) | Apache 2.0 |
| ultralytics | [Link](https://pypi.org/project/ultralytics/) | AGPL-3.0 License |

The versions for each of these libraries are specified in `requirements.txt`.

## API Endpoints

- `/preprocessor` (POST): Main endpoint for object segmentation
- `/health` (GET): Health check endpoint
- `/warmup` (GET): Warms up the SAM model with a dummy inference

## Processing Pipeline

1. Read `object-detection-llm`'s bounding boxes for the request (required; this preprocessor is a no-op without them).
2. Decode the graphic from base64 to a PIL image. No additional resizing is performed here - the upstream `resize-graphic` pseudo-preprocessor already caps every incoming graphic to a fixed maximum dimension, so this preprocessor and `object-detection-llm` share the same pixel space.
3. Segment each detected object's box with SAM, using the object's unique ID (not its type) as the SAM label to keep same-type objects (e.g. two people) from being merged into one contour set.
4. Filter out contours below `MIN_CONTOUR_AREA`.
5. Build a `segments` list matching `schemas/preprocessors/segmentation.schema.json`, with each segment tagged with the `objectID` it came from.
