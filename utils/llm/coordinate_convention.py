# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""
LLM-specific bounding box format configuration.
Add new model families here as they're supported.
"""
MODEL_BBOX_FORMATS = {
    "qwen": {
        "bbox_key": "bbox_2d",
        "coord_order": ("x1", "y1", "x2", "y2"),
    },
    "gemma": {
        "bbox_key": "box_2d",
        "coord_order": ("y1", "x1", "y2", "x2"),
    },
}

DEFAULT_FAMILY = "qwen"

def get_model_family(llm_model_env):
    """Determine model family from the LLM_MODEL env value."""
    llm_model_env = (llm_model_env or "").lower()
    for family in MODEL_BBOX_FORMATS:
        if family in llm_model_env:
            return family
    return DEFAULT_FAMILY

def get_bbox_format(model_family):
    """Return the bbox config dict for a given model family."""
    return MODEL_BBOX_FORMATS.get(model_family, MODEL_BBOX_FORMATS[DEFAULT_FAMILY])