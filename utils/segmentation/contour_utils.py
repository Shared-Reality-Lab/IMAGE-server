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
Utilities for contour extraction and processing.
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
import cv2
import numpy as np
import copy


def extract_normalized_contours(
    results: list,
    img_width: int,
    img_height: int,
    min_points: int = 3
) -> List[List[List[float]]]:
    """
    Extract and normalize contours from SAM results.
    
    Args:
        results: SAM model results containing masks
        img_width: Image width for normalization
        img_height: Image height for normalization
        min_points: Minimum number of points required for a valid contour
    
    Returns:
        List of normalized contours, where each contour is a list of [x, y] points
        with values in range [0, 1]
    """
    if not results or len(results) == 0:
        logging.info("No masks found in SAM results.")
        return []
    
    # Handle different result formats
    if hasattr(results[0], 'masks') and results[0].masks is not None:
        masks_data = results[0].masks.data
    elif hasattr(results[0], 'masks'):
        # Sometimes masks might be directly accessible
        masks_data = results[0].masks
    else:
        logging.warning("No masks found in results")
        return []
    
    if masks_data is None:
        logging.debug("Masks data is None")
        return []
    
    # Ensure we have numpy array
    if hasattr(masks_data, 'cpu'):
        masks = masks_data.cpu().numpy()
    else:
        masks = np.array(masks_data)
    
    # Ensure masks is at least 2D
    if masks.ndim == 2:
        masks = masks[np.newaxis, ...]
    
    normalized_contours_list = []
    
    for i, mask in enumerate(masks):
        try:
            # Convert mask to uint8
            mask_uint8 = (mask * 255).astype(np.uint8)
            
            # Find contours
            contours, _ = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            if contours:
                for contour in contours:
                    if len(contour) < min_points:
                        continue
                    
                    # Normalize contour points
                    normalized_contour = normalize_contour(
                        contour, img_width, img_height
                    )
                    
                    if normalized_contour:
                        normalized_contours_list.append(normalized_contour)
            else:
                logging.debug(f"No contours found for mask with index {i}.")
                    
        except Exception as e:
            logging.error(f"Error extracting normalized contours for mask {i}: {e}", exc_info=True)
            continue
    
    return normalized_contours_list


def normalize_contour(
    contour: np.ndarray,
    img_width: int,
    img_height: int
) -> List[List[float]]:
    """
    Normalize a single contour to [0, 1] range.
    
    Args:
        contour: OpenCV contour array
        img_width: Image width for normalization
        img_height: Image height for normalization
    
    Returns:
        List of normalized [x, y] points
    """
    if img_width <= 0 or img_height <= 0:
        logging.error(f"Invalid image dimensions: {img_width}x{img_height}")
        return []
    
    normalized_points = []
    
    for point in contour.reshape(-1, 2):
        x_norm = float(point[0]) / img_width
        y_norm = float(point[1]) / img_height
        
        # Clamp to [0, 1] range
        x_norm = max(0.0, min(1.0, x_norm))
        y_norm = max(0.0, min(1.0, y_norm))
        
        normalized_points.append([x_norm, y_norm])
    
    return normalized_points


def calculate_contour_properties(
    contour: List[List[float]]
) -> Dict[str, Any]:
    """
    Calculate geometric properties of a normalized contour.
    
    Args:
        contour: List of normalized [x, y] points
    
    Returns:
        Dictionary with centroid and area properties
    """
    if not contour or len(contour) < 3:
        return {"centroid": [0.0, 0.0], "area": 0.0}
    
    try:
        contour_np = np.array(contour, dtype=np.float32)
        
        # Calculate moments
        moments = cv2.moments(contour_np)
        
        # Calculate centroid
        if moments['m00'] != 0:
            cx = float(moments['m10'] / moments['m00'])
            cy = float(moments['m01'] / moments['m00'])
        else:
            # Fallback to geometric center
            cx = float(np.mean(contour_np[:, 0]))
            cy = float(np.mean(contour_np[:, 1]))
        
        # Clamp centroid to [0, 1]
        centroid = [
            max(0.0, min(1.0, cx)),
            max(0.0, min(1.0, cy))
        ]
        
        # Calculate area (normalized)
        area = float(cv2.contourArea(contour_np))
        area = max(0.0, min(1.0, area))
        
        return {
            "centroid": centroid,
            "area": area
        }
        
    except Exception as e:
        logging.error(f"Error calculating contour properties: {e}")
        return {"centroid": [0.0, 0.0], "area": 0.0}


def create_segment_from_contours(
    contours: List[List[List[float]]],
    name: str,
    calculate_properties: bool = True
) -> Dict[str, Any]:
    """
    Create a segment object from contours.
    
    Args:
        contours: List of contours (each contour is a list of [x, y] points)
        name: Name for the segment
        calculate_properties: Whether to calculate geometric properties
    
    Returns:
        Segment dictionary with contours and optional properties
    """
    segment = {"name": name, "contours": []}
    
    for contour in contours:
        contour_obj = {"coordinates": contour}
        
        if calculate_properties:
            properties = calculate_contour_properties(contour)
            contour_obj.update(properties)
        
        segment["contours"].append(contour_obj)
    
    # Calculate overall segment properties if requested
    if calculate_properties and segment["contours"]:
        # Use the first contour's properties or calculate combined
        if len(segment["contours"]) == 1:
            segment["centroid"] = segment["contours"][0].get("centroid", [0.0, 0.0])
            segment["area"] = segment["contours"][0].get("area", 0.0)
        else:
            # Calculate combined properties
            total_area = sum(c.get("area", 0.0) for c in segment["contours"])
            
            # Weighted centroid
            if total_area > 0:
                weighted_x = sum(
                    c.get("centroid", [0.0, 0.0])[0] * c.get("area", 0.0)
                    for c in segment["contours"]
                ) / total_area
                weighted_y = sum(
                    c.get("centroid", [0.0, 0.0])[1] * c.get("area", 0.0)
                    for c in segment["contours"]
                ) / total_area
                segment["centroid"] = [weighted_x, weighted_y]
            else:
                segment["centroid"] = [0.0, 0.0]
            
            segment["area"] = total_area
    
    return segment


def update_data_with_contours(
    base_data: Dict[str, Any],
    contours_by_label: Dict[str, List[List[List[float]]]],
    stages_key: str = "stages",
    label_key: str = "label",
    segments_key: str = "segments"
) -> Dict[str, Any]:
    """
    Update a data structure with segmentation contours.
    This function maintains the exact format required for schema validation.
    
    Args:
        base_data: Base data structure to update
        contours_by_label: Dictionary mapping labels to contours
        stages_key: Key for stages/items in base_data
        label_key: Key for label in each stage/item
        segments_key: Key for segments in each stage/item
    
    Returns:
        Updated data structure with contours added in the exact format
        required for schema validation
    """
    updated_data = copy.deepcopy(base_data)
    
    if stages_key not in updated_data:
        logging.warning(f"Key '{stages_key}' not found in base data")
        return updated_data
    
    # Create lookup for stages by label
    stages_by_label = {}
    for stage in updated_data[stages_key]:
        if isinstance(stage, dict) and label_key in stage:
            stages_by_label[stage[label_key]] = stage
    
    # Add contours to matching stages
    for label, contours_list in contours_by_label.items():
        if label not in stages_by_label:
            logging.pii(f"Found contours for label '{label}', but no matching stage found in base_json.")
            continue
        
        stage = stages_by_label[label]
        
        # Initialize segments if not present
        if segments_key not in stage or not isinstance(stage[segments_key], list):
            stage[segments_key] = []
        
        # Add segments for each contour
        for i, contour_coords in enumerate(contours_list):
            if not contour_coords or len(contour_coords) < 3:
                logging.pii(f"Skipping invalid contour {i+1} for label '{label}' (too few points)")
                continue
            
            try:
                # Convert to numpy array for calculations
                contour_np = np.array(contour_coords, dtype=np.float32)
                
                # Calculate centroid
                moments = cv2.moments(contour_np)
                if moments['m00'] != 0:
                    cx = float(moments['m10'] / moments['m00'])
                    cy = float(moments['m01'] / moments['m00'])
                else:
                    # Fallback to geometric center
                    cx = float(np.mean(contour_np[:, 0]))
                    cy = float(np.mean(contour_np[:, 1]))
                
                # Clamp centroid to [0, 1]
                contour_centroid = [
                    max(0.0, min(1.0, cx)),
                    max(0.0, min(1.0, cy))
                ]
                
                # Calculate area (normalized)
                contour_area = float(cv2.contourArea(contour_np))
                contour_area = max(0.0, min(1.0, contour_area))
                
                # Format coordinates as list of [x, y] pairs
                formatted_coordinates = [
                    [float(p[0]), float(p[1])] for p in contour_coords
                ]
                
                # Create contour object
                contour_object = {
                    "coordinates": formatted_coordinates,
                    "centroid": contour_centroid,
                    "area": contour_area
                }
                
                # Create segment
                segment_name = f"{label} Part {i + 1}" if len(contours_list) > 1 else label
                segment = {
                    "name": segment_name,
                    "contours": [contour_object],
                    "centroid": contour_centroid,
                    "area": contour_area
                }
                
                stage[segments_key].append(segment)
                
            except Exception as e:
                logging.pii(f"Error processing contour {i+1} for label '{label}': {e}", exc_info=True)
                continue
    
    # Ensure all stages have segments key (even if empty)
    for stage in updated_data[stages_key]:
        if isinstance(stage, dict) and segments_key not in stage:
            stage[segments_key] = []
    
    return updated_data


def filter_contours_by_area(
    contours: List[List[List[float]]],
    min_area: float = 0.0001,
    max_area: float = 1.0
) -> List[List[List[float]]]:
    """
    Filter contours based on their area.
    
    Args:
        contours: List of contours
        min_area: Minimum area threshold (normalized)
        max_area: Maximum area threshold (normalized)
    
    Returns:
        Filtered list of contours
    """
    filtered = []
    
    for contour in contours:
        properties = calculate_contour_properties(contour)
        area = properties.get("area", 0.0)
        
        if min_area <= area <= max_area:
            filtered.append(contour)
        else:
            logging.debug(f"Filtered out contour with area {area}")
    
    return filtered


def simplify_contour(
    contour: List[List[float]],
    epsilon_factor: float = 0.01
) -> List[List[float]]:
    """
    Simplify a contour using Douglas-Peucker algorithm.
    
    Args:
        contour: List of [x, y] points
        epsilon_factor: Factor for approximation accuracy (relative to perimeter)
    
    Returns:
        Simplified contour
    """
    if len(contour) < 3:
        return contour
    
    try:
        contour_np = np.array(contour, dtype=np.float32)
        
        # Calculate epsilon based on perimeter
        perimeter = cv2.arcLength(contour_np, True)
        epsilon = epsilon_factor * perimeter
        
        # Approximate contour
        approx = cv2.approxPolyDP(contour_np, epsilon, True)
        
        # Convert back to list format
        simplified = approx.reshape(-1, 2).tolist()
        
        return simplified
        
    except Exception as e:
        logging.error(f"Error simplifying contour: {e}")
        return contour