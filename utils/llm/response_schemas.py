"""
A complete set of response models for structured outputs
in LLM-based preprocessors.
"""

# text-followup
FOLLOWUP_RESPONSE_SCHEMA = {
    "properties": {
        "response_brief": {
            "title": "Response Brief",
            "type": "string",
            "description": "One sentence response to the user request"
        },
        "response_full": {
            "title": "Response Full",
            "type": "string",
            "description": "Further details. Maximum three sentences"
        }
    },
    "required": ["response_brief", "response_full"],
    "title": "ResponseModel",
    "type": "object"
}
###

# content-categoriser
CATEGORISER_RESPONSE_SCHEMA = {
    "$defs": {
        "CategoryType": {
            "enum": ["photograph", "chart", "text", "other"],
            "title": "CategoryType",
            "type": "string",
        }
    },
    "properties": {
        "category": {
            "$ref": "#/$defs/CategoryType",
            "description": "The type of content being categorized",
        }
    },
    "required": ["category"],
    "title": "ResponseModel",
    "type": "object",
}
###

# multistage-diagram-segmentation

# stage/link schema
STAGE_RESPONSE_SCHEMA = {
    "$defs": {
        "Link": {
            "description": "Links between the various stages "
            "based on the arrow directions",
            "properties": {
                "source": {
                    "description": "id of the stage at which the link starts. "
                    "Randomly chosen if the arrow is bidirectional",
                    "title": "Source",
                    "type": "string",
                },
                "target": {
                    "description": "id of the stage at which the link ends. "
                    "Randomly chosen if the arrow is bidirectional",
                    "title": "Target",
                    "type": "string",
                },
                "directed": {
                    "description": "true indicates that the link is "
                    "unidirectional",
                    "title": "Directed",
                    "type": "boolean",
                },
            },
            "required": ["source", "target", "directed"],
            "title": "Link",
            "type": "object",
        },
        "Stage": {
            "description": "Description of the stage in the flow diagram",
            "properties": {
                "id": {
                    "description": "unique identifier for the stage",
                    "title": "Id",
                    "type": "string",
                },
                "label": {
                    "description": "name of the stage",
                    "title": "Label",
                    "type": "string",
                },
                "description": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                    "description": "One/two-sentence description of the stage",
                    "title": "Description",
                },
            },
            "required": ["id", "label"],
            "title": "Stage",
            "type": "object",
        },
    },
    "description": "Root model representing a flow diagram with stages and "
    "links",
    "properties": {
        "stages": {
            "description": "Array of stages in the flow diagram",
            "items": {"$ref": "#/$defs/Stage"},
            "title": "Stages",
            "type": "array",
        },
        "links": {
            "description": "Array of links between stages",
            "items": {"$ref": "#/$defs/Link"},
            "title": "Links",
            "type": "array",
        },
    },
    "required": ["stages", "links"],
    "title": "StageModel",
    "type": "object",
}

# bounding box response schema
BBOX_RESPONSE_SCHEMA = {
    "$defs": {
        "BoundingBoxItem": {
            "properties": {
                "bbox_2d": {
                    "items": {"type": "number"},
                    "maxItems": 4,
                    "minItems": 4,
                    "title": "Bbox 2D",
                    "type": "array",
                    "description": "Bounding box coordinates [x1, y1, x2, y2]"
                },
                "label": {
                    "title": "Label",
                    "type": "string",
                    "description": "Label for the bounding box"
                }
            },
            "required": ["bbox_2d", "label"],
            "title": "BoundingBoxItem",
            "type": "object"
        }
    },
    "items": {
        "$ref": "#/$defs/BoundingBoxItem"
    },
    "title": "BoundingBoxResponse",
    "type": "array"
}
###
