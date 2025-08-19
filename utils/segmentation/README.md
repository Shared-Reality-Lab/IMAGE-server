# Segmentation Utilities

This module provides reusable image segmentation utilities using the Segment Anything Model (SAM) for the IMAGE project. The module follows the same initialization pattern as `LLMClient` for consistency across the codebase.

## Features

- **Bounding box-based segmentation**: Segment image regions using bounding boxes
- **Prompted segmentation**: Optional text prompts using labels to improve segmentation quality
- **Schema-compatible output**: Direct generation of outputs that pass schema validation
- **Backward compatibility**: Maintains compatibility with existing `segment_stages` function
- **Consistent patterns**: Follows the same initialization and error handling patterns as other project modules

## Installation

Ensure you have the required dependencies:

```bash
pip install ultralytics opencv-python pillow numpy
```

Set the SAM model path environment variable:

```bash
export SAM_MODEL_PATH="/path/to/sam_model.pt"
```

## Quick Start

### Basic Usage

```python
from PIL import Image
from utils.segmentation import segment_image_with_boxes

# Load image
image = Image.open("diagram.jpg")

# Define bounding boxes
bounding_boxes = [
    {'bbox_2d': [100, 100, 200, 200], 'label': 'Object A'},
    {'bbox_2d': [300, 150, 400, 250], 'label': 'Object B'}
]

# Segment image
results = segment_image_with_boxes(image, bounding_boxes)

# Process results
for label, contours in results.items():
    print(f"{label}: {len(contours)} contours found")
```

### Using SAMClient (Recommended)

```python
from utils.segmentation import SAMClient

# Initialize client (follows LLMClient pattern)
sam_client = SAMClient()

# Segment with text prompts enabled
results = sam_client.segment_with_boxes(
    image,
    bounding_boxes,
    use_prompts=True,  # Use labels as text prompts to help SAM
    aggregate_by_label=True
)
```

### Getting Schema-Compatible Output

```python
# For outputs that need to pass schema validation
final_data = sam_client.segment_with_boxes(
    image,
    bounding_boxes,
    use_prompts=True,
    aggregate_by_label=True,
    return_structured=True,  # Returns schema-compatible format
    base_data=initial_data   # base data structure
)
```

## API Reference

### SAMClient

Main client for SAM-based segmentation, following the same pattern as `LLMClient`.

#### Methods

##### `__init__()`
Initialize the SAM client using environment variables.
- Uses `SAM_MODEL_PATH` environment variable for model path
- Raises `ValueError` if environment variable is not set

##### `segment_with_boxes(image, bounding_boxes, use_prompts=False, aggregate_by_label=True, return_structured=False, base_data=None)`
Segment image using bounding boxes.
- `image`: PIL Image object
- `bounding_boxes`: List of dicts with 'bbox_2d' and 'label' keys
- `use_prompts`: Use labels as text prompts to help SAM understand what to segment
- `aggregate_by_label`: Group contours by label
- `return_structured`: Return data in schema-compatible format
- `base_data`: Base data structure to update (required if return_structured=True)

Returns:
- If `return_structured=False`: Dictionary mapping labels to lists of normalized contours
- If `return_structured=True`: Updated base_data with contours integrated in schema-compatible format

##### `segment_stages(bounding_boxes_data, image, use_prompts=False)`
Backward-compatible method matching the original function signature.

##### `warmup()`
Warm up the model with a dummy image for faster first inference.

### Convenience Functions

#### `segment_image_with_boxes(image, bounding_boxes, use_prompts=False, aggregate_by_label=True)`
Quick segmentation without creating a client instance.

#### `segment_stages(bounding_boxes_data, im, use_prompts=False)`
Backward-compatible function with original signature.

### Contour Utilities

#### `update_data_with_contours(base_data, contours_by_label, ...)`
Update existing data structure with segmentation results in schema-compatible format.

#### `extract_normalized_contours(results, img_width, img_height, min_points=3)`
Extract and normalize contours from SAM results.

#### `calculate_contour_properties(contour)`
Calculate geometric properties (centroid, area) of a contour.

#### `filter_contours_by_area(contours, min_area=0.0001, max_area=1.0)`
Filter contours based on their normalized area.

#### `simplify_contour(contour, epsilon_factor=0.01)`
Simplify contour points using Douglas-Peucker algorithm.

## Input Format

The segmentation utilities expect bounding boxes in the following format:

```json
[
    {
        "bbox_2d": [x1, y1, x2, y2],
        "label": "Object Name"
    },
    ...
]
```

Where:
- `bbox_2d`: Bounding box coordinates in pixels [left, top, right, bottom]
- `label`: String identifier for the object (used as text prompt when `use_prompts=True`)

## Output Format

### Standard Output
```python
{
    "label1": [
        [[x1, y1], [x2, y2], ...],  # First contour
        [[x1, y1], [x2, y2], ...],  # Second contour
    ],
    "label2": [...],
    ...
}
```

### Structured Output (for schema validation)
When using `return_structured=True`, the output follows the exact format required for schema validation, with segments added to the base data structure.

## Configuration

### Environment Variables

- `SAM_MODEL_PATH`: Path to the SAM model file (required)

### Optional Parameters

- `use_prompts`: Enable text prompts using labels (default: False)
- `aggregate_by_label`: Group contours by label (default: True)
- `return_structured`: Return schema-compatible output (default: False)


## Error Handling

Following project patterns:
- Returns empty results on failure rather than raising exceptions
- Logs errors appropriately
- Supports partial results when some operations succeed

## Performance Considerations

1. **Client Initialization**: Initialize `SAMClient` once and reuse for multiple images
2. **Warmup**: Call `warmup()` after initialization for faster first inference
3. **Batch Processing**: Process multiple bounding boxes in a single call


## Troubleshooting

### Common Issues

1. **No contours found**: Check image dimensions and bounding box coordinates
2. **Poor segmentation quality**: Enable `use_prompts=True` to use labels as text prompts
3. **Schema validation errors**: Use `return_structured=True` with proper `base_data`
4. **Model not found**: Ensure `SAM_MODEL_PATH` environment variable is set