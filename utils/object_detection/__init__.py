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
Shared helper for reading object-detection preprocessor output.
"""

GENERIC_OBJECT_DETECTION_NAME = \
    "ca.mcgill.a11y.image.preprocessor.objectDetection"
LLM_OBJECT_DETECTION_NAME = \
    "ca.mcgill.a11y.image.preprocessor.objectDetectionLLM"


def get_object_detection_data(preprocessors):
    """Prefer the generic (YOLO/Azure) key; fall back to the LLM key."""
    return preprocessors.get(GENERIC_OBJECT_DETECTION_NAME) \
        or preprocessors.get(LLM_OBJECT_DETECTION_NAME)
