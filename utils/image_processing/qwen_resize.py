# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# and our Additional Terms along with this program.
# If not, see
# <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.

"""
Image processing utilities for Qwen-compatible image resizing and decoding.
"""

import io
import base64
import logging
from typing import Tuple, Optional
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from qwen_vl_utils import smart_resize


def decode_and_resize_image(
    source: str,
    factor: int = 28,
    min_pixels: Optional[int] = None,
    max_pixels: Optional[int] = None
) -> Tuple[Optional[Image.Image], Optional[str], Optional[dict]]:
    """
    Decode base64 image data and resize it for Qwen model input.

    Args:
        source: Base64 encoded image string with data URI header
        factor: Resize factor for model input (default: 28 for Qwen)
        min_pixels: Minimum pixels for resize (optional)
        max_pixels: Maximum pixels for resize (optional)

    Returns:
        Tuple of:
        - Base64 encoded resized image
        - PIL Image object (RGB format)
        - Error dict with message and code if failed, None if successful
    """
    try:
        # Validate input
        if not isinstance(source, str) or "," not in source:
            error_msg = "Invalid graphic format: expected data URI string."
            logging.error(error_msg)
            return None, None, {"error": error_msg, "code": 400}

        # Extract base64 data from data URI
        graphic_b64 = source.split(',', 1)[1]
        img_data = base64.b64decode(graphic_b64)
        pil_image = Image.open(BytesIO(img_data))

        # Convert to RGB format
        pil_image = pil_image.convert("RGB")
        logging.debug(
            f"Decoded image successfully. Format: {pil_image.format}, "
            f"Size: {pil_image.size}"
        )

        width, height = pil_image.size

        # Calculate resize dimensions using Qwen's smart_resize
        resize_params = {"height": height, "width": width, "factor": factor}
        if min_pixels is not None:
            resize_params["min_pixels"] = min_pixels
        if max_pixels is not None:
            resize_params["max_pixels"] = max_pixels

        input_height, input_width = smart_resize(**resize_params)

        # Resize image to model input size
        pil_image_resized = pil_image.resize((input_width, input_height))
        logging.debug(
            f"Resized image to model input size: {input_width}x{input_height}"
        )

        # Convert resized image to base64
        buffer = io.BytesIO()
        pil_image_resized.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Return resized image (for SAM) and base64 (for LLM)
        return img_base64, pil_image_resized, None

    except (ValueError, TypeError) as e:
        error_msg = f"Failed to decode base64 image data: {e}"
        logging.error(error_msg)
        return None, None, {
            "error": "Invalid base64 image data",
            "code": 400
            }

    except UnidentifiedImageError:
        error_msg = "Cannot identify image file format from decoded data."
        logging.error(error_msg)
        return None, None, {
            "error": "Invalid or unsupported image format",
            "code": 400
            }

    except Exception as e:
        error_msg = f"Unexpected error during image processing: {e}"
        logging.error(error_msg, exc_info=True)
        return None, None, {
            "error": "Internal server error during image processing",
            "code": 500
            }


def get_image_dimensions(image: Image.Image) -> Tuple[int, int]:
    """
    Get image dimensions with validation.

    Args:
        image: PIL Image object

    Returns:
        Tuple of (width, height)

    Raises:
        ValueError: If image dimensions are invalid
    """
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image dimensions: {width}x{height}")
    return width, height
