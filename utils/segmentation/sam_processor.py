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

"""
SAM (Segment Anything Model) processor for image segmentation.
"""

import logging
import os
from typing import List, Dict, Optional, Any
from PIL import Image
import numpy as np
from ultralytics import SAM
from .contour_utils import (
    extract_normalized_contours,
    update_data_with_contours
)


class SAMClient:
    """
    Client for Segment Anything Model (SAM) segmentation.
    Follows the same initialization pattern as LLMClient.
    """

    def __init__(self):
        """
        Initialize SAM client using environment variables.
        Similar to LLMClient initialization pattern.
        """
        self.model_path = os.getenv('SAM_MODEL_PATH')
        if not self.model_path:
            raise ValueError(
                "SAM_MODEL_PATH environment variable must be set. "
                "Please set it to the path of your SAM model file."
            )

        self.model = None
        self._initialize_model()
        logging.debug(
            f"SAMClient initialized with model from {self.model_path}"
            )

    def _initialize_model(self):
        """Initialize the SAM model."""
        try:
            self.model = SAM(self.model_path)
            logging.debug("SAM model loaded successfully.")
        except Exception as e:
            logging.error(
                f"Failed to load SAM model from {self.model_path}: {e}"
                )
            raise RuntimeError(f"Could not initialize SAM model: {e}")

    def segment_with_boxes(
        self,
        image: Image.Image,
        bounding_boxes: List[Dict[str, Any]] = None,
        use_prompts: bool = False,
        aggregate_by_label: bool = True,
        return_structured: bool = False,
        base_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Segment image regions using bounding boxes.

        Args:
            image: PIL Image to segment
            bounding_boxes: List of dicts with 'bbox_2d' and 'label' keys
                           bbox_2d format: [x1, y1, x2, y2]
            use_prompts: Whether to use labels as text prompts for SAM
            aggregate_by_label: Whether to aggregate contours by label
            return_structured: If True, returns data in the format produced by
                             update_data_with_contours (for schema validation)
            base_data: Base data structure to update
                    (required if return_structured=True)

        Returns:
            If return_structured=False: Dictionary mapping labels to lists
                of normalized contours
            If return_structured=True: Updated base_data with contours
        """
        if not bounding_boxes:
            logging.info("No bounding boxes provided for segmentation")
            if return_structured and base_data:
                return update_data_with_contours(base_data, {})
            return {}

        width, height = image.size
        logging.pii(f"Processing image with dimensions: {width}x{height}")

        if width <= 0 or height <= 0:
            logging.error(
                f"Invalid image dimensions: {width}x{height}."
                "Cannot perform segmentation."
                )
            if return_structured and base_data:
                return update_data_with_contours(base_data, {})
            return {}

        # Validate and extract bounding boxes
        bboxes = []
        labels = []

        for item in bounding_boxes:
            if not isinstance(item, dict):
                logging.pii(
                    f"Skipping non-dictionary item in bbox list: {item}"
                    )
                continue

            label = item.get("label")
            bbox = item.get("bbox_2d")

            if not label or not isinstance(label, str):
                logging.pii(
                    f"Skipping item with missing or invalid label: {item}"
                    )
                continue
            if (
                not bbox
                or not isinstance(bbox, (list, tuple))
                or len(bbox) != 4
            ):
                logging.pii(
                    f"Skipping item with missing or invalid 'bbox_2d': {item}"
                    )
                continue

            logging.pii(
                f"Processing bounding box for label: '{label}' "
                f"(normalized coords: {bbox})"
            )

            # Convert normalized coordinates (0-1000) received from Qwen 3
            # to pixel coordinates
            bbox_pixels = [
                (bbox[0] / 1000.0) * width,
                (bbox[1] / 1000.0) * height,
                (bbox[2] / 1000.0) * width,
                (bbox[3] / 1000.0) * height
            ]

            logging.pii(
                f"Converted to pixel coords: {bbox_pixels}"
            )

            bboxes.append(bbox_pixels)
            labels.append(label)

        if not bboxes:
            logging.warning("No valid bounding boxes found after validation")
            if return_structured and base_data:
                return update_data_with_contours(base_data, {})
            return {}

        # Run SAM segmentation
        aggregated_contour_data = {}

        try:
            # Run SAM with all bounding boxes at once
            if use_prompts:
                # Use labels as prompts to help SAM understand what to segment
                # The exact parameter name may vary by ultralytics version
                results = self.model(image, bboxes=bboxes, labels=labels)
                logging.debug(
                    f"Running SAM with {len(bboxes)} boxes and text prompts"
                    )
            else:
                results = self.model(image, bboxes=bboxes)
                logging.debug(f"Running SAM with {len(bboxes)} boxes")

            if not results or len(results) == 0:
                logging.warning("SAM returned no results")
                if return_structured and base_data:
                    return update_data_with_contours(base_data, {})
                return {}

            # Process results
            if aggregate_by_label:
                aggregated_contour_data = {label: [] for label in labels}

                # Process each result with its corresponding label
                for i, label in enumerate(labels):
                    try:
                        if i < len(results[0]):
                            # Create a wrapper list for the single result
                            result_wrapper = [results[0][i]]
                            normalized_contours = extract_normalized_contours(
                                result_wrapper, width, height
                            )
                            aggregated_contour_data[label].extend(
                                normalized_contours
                                )
                            l_c = len(normalized_contours)
                            logging.pii(
                                f"Extracted {l_c} contours for label '{label}'"
                                )
                        else:
                            logging.warning(
                                f"No result for label '{label}' at index {i}"
                                )
                    except Exception as e:
                        logging.pii(
                            f"Error processing result for label '{label}': "
                            f"{e}",
                            exc_info=True
                            )
                        continue
            else:
                # Return with unique keys for each detection
                for i, label in enumerate(labels):
                    try:
                        if i < len(results[0]):
                            result_wrapper = [results[0][i]]
                            normalized_contours = extract_normalized_contours(
                                result_wrapper, width, height
                            )
                            key = f"{label}_{i}"
                            aggregated_contour_data[key] = normalized_contours
                    except Exception as e:
                        logging.pii(
                            f"Error processing result for label '{label}': "
                            f"{e}",
                            exc_info=True
                            )
                        continue

        except Exception as e:
            logging.error(f"Error during SAM processing: {e}", exc_info=True)
            # Return empty contours rather than raising
            aggregated_contour_data = {}

        # Log summary
        logging.pii("--- Aggregated Contour Data Summary ---")
        for lbl, contours in aggregated_contour_data.items():
            logging.pii(f"Label: '{lbl}', Number of Contours: {len(contours)}")
        logging.pii("---------------------------------------")

        # Return in requested format
        if return_structured and base_data:
            return update_data_with_contours(
                base_data,
                aggregated_contour_data
                )
        else:
            return aggregated_contour_data

    def segment_stages(
        self,
        bounding_boxes_data: List[Dict[str, Any]],
        image: Image.Image,
        use_prompts: bool = False
    ) -> Dict[str, List[List[List[float]]]]:
        """
        Process bounding box JSON and run SAM segmentation.
        This method maintains backward compatibility with the original
        function signature.

        Args:
            bounding_boxes_data: List of dicts with 'bbox_2d' and 'label' keys
            image: PIL Image to segment
            use_prompts: Whether to use labels as text prompts

        Returns:
            Dictionary mapping labels to lists of normalized contours
        """
        return self.segment_with_boxes(
            image,
            bounding_boxes_data,
            use_prompts=use_prompts,
            aggregate_by_label=True,
            return_structured=False
        )

    def warmup(self) -> bool:
        """
        Warm up the SAM model with a dummy image.

        Returns:
            True if warmup successful, False otherwise
        """
        try:
            logging.info("Warming up SAM...")

            # Create dummy image
            dummy_cv2 = np.zeros((512, 512, 3), dtype=np.uint8)
            dummy_pil = Image.fromarray(dummy_cv2)

            # Run dummy inference
            _ = self.model(dummy_pil, bboxes=[[100, 100, 200, 200]])

            logging.debug("SAM model warmed up successfully")
            return True

        except Exception as e:
            logging.info(f"SAM warmup failed: {str(e)}")
            return False


# Convenience functions for backward compatibility and single-use cases
# not used in the main SAMClient class or preprocessors
def segment_stages(
    bounding_boxes_data: List[Dict[str, Any]],
    im: Image.Image,
    use_prompts: bool = False
) -> Dict[str, List[List[List[float]]]]:
    """
    Backward-compatible function matching the original segment_stages
    signature.

    Args:
        bounding_boxes_data: List of dicts with 'bbox_2d' and 'label' keys
        im: PIL Image to segment
        use_prompts: Whether to use labels as text prompts

    Returns:
        Dictionary mapping labels to lists of normalized contours
    """
    client = SAMClient()
    return client.segment_stages(bounding_boxes_data, im, use_prompts)


def segment_image_with_boxes(
    image: Image.Image,
    bounding_boxes: List[Dict[str, Any]],
    use_prompts: bool = False,
    aggregate_by_label: bool = True
) -> Dict[str, List[List[List[float]]]]:
    """
    Convenience function to segment an image without creating a client
    instance.

    Args:
        image: PIL Image to segment
        bounding_boxes: List of dicts with 'bbox_2d' and 'label' keys
        use_prompts: Whether to use labels as text prompts
        aggregate_by_label: Whether to aggregate contours by label

    Returns:
        Dictionary mapping labels to lists of normalized contours
    """
    client = SAMClient()
    return client.segment_with_boxes(
        image,
        bounding_boxes,
        use_prompts=use_prompts,
        aggregate_by_label=aggregate_by_label,
        return_structured=False
    )
