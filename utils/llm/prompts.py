# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""
Prompt templates for LLM interactions in the IMAGE project.
"""
# Graphic caption
GRAPHIC_CAPTION_PROMPT = """
Describe this image to a person who cannot see it.
Use simple, descriptive, clear, and concise language.
Answer with only one sentence.
Do not give any intro like "Here's what in this image:",
"The image depicts", or "This photograph showcases" unless
the graphic type is significant (like oil painting or aerial photo).
Instead, start describing the graphic right away.
"""

# Content categoriser
CATEGORISER_PROMPT = """
Answer only in JSON with the following format:
'{"category": "YOUR_ANSWER"}.'
Which of the following categories best
describes this image, selecting from this enum:
"""

POSSIBLE_CATEGORIES = "photograph, chart, text, other"

# Base prompts for diagram analysis
MULTISTAGE_DIAGRAM_BASE_PROMPT = """
Look at the attached flow diagram and parse the information
about stages and their dependencies.
Determine phase names, phase descriptions, and connections between phases
(usually marked with arrows or clear from the diagram flow).
Return the response in the JSON format according to provided schema.
Do not include any additional text in your response.
Return only the JSON object.
If some of the properties can't be identified, assign empty value to them.
"""

BOUNDING_BOX_PROMPT_TEMPLATE = """
Give the bounding boxes for the illustrations
of the following stages: {stages}.
Output a only JSON list of bounding boxes where each entry contains
the 2D bounding box in the key "box_2d",
and the stage name in the key "label".

"""

BOUNDING_BOX_PROMPT_EXAMPLE = """
Example:
```json
[
    {
        "bbox_2d": [x1, y1, x2, y2],
        "label": "Label 1"
    },
    {
        "bbox_2d": [x1, y1, x2, y2],
        "label": "Label 2"
    }
]
```
Ensure that the bounding boxes are in the format [x1, y1, x2, y2]
"""
