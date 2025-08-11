"""
Segmentation utilities.
"""

from .sam_processor import (
    SAMClient,
    segment_stages,
    segment_image_with_boxes
)

from .contour_utils import (
    extract_normalized_contours,
    normalize_contour,
    calculate_contour_properties,
    create_segment_from_contours,
    update_data_with_contours,
    filter_contours_by_area,
    simplify_contour
)

__all__ = [
    # SAM client and functions
    'SAMClient',
    'segment_stages',
    'segment_image_with_boxes',
    'extract_normalized_contours',
    'normalize_contour',
    'calculate_contour_properties',
    'create_segment_from_contours',
    'update_data_with_contours',
    'filter_contours_by_area',
    'simplify_contour'
]
