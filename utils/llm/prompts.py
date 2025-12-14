# Copyright (c) 2025 IMAGE Project, Shared Reality Lab, McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""
Prompt templates for LLM interactions in the IMAGE project.
"""
# Object detection
OBJECT_DETECTION_PROMPT = """
Step 1:
Determine from 0 to 10 major and important objects in the image.
Focus ONLY on the objects that are clearly visible and identifiable.

Step 2:
Give the bounding boxes for the objects determined in the first step.
Output a only JSON list of bounding boxes where each entry contains:
- the pixel coordinates of a 2D bounding box in the key "bbox_2d",
- the object label in the key "label".

Example:
```json
[
    {
        "bbox_2d": [120, 200, 300, 450],
        "label": "car",
    },
    {
        "bbox_2d": [50, 100, 120, 300],
        "label": "person",
    }
]
```
Ensure that the bounding boxes are in the format [x1, y1, x2, y2].

Rules:
1. Focus ONLY on the major and important objects in the image.
2. The graphic can contain any number of objects, from zero to many.
3. If no objects are detected, return an empty list: [].
4. Use simple and common object labels (e.g., "car", "person", "tree").
5. Include ONLY objects that are clearly visible and identifiable.
6. Multiple objects can have the same confidence score.
"""
###

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
###

# Content categoriser
CATEGORISER_PROMPT = """
Your task is to categorise the content of an image.
Answer only in JSON.
The JSON should contain a single key "categories" with a value
containing the object with the boolean values for each category.
For example:
```json
{
    "categories": {
        "photo": True,
        "diagram": False,
        "multistage_diagram": False,
        "contains_text": False,
        "collage": False,
        "chart_or_graph": False,
        "illustration": False,
    }
}
```

Assign boolean values (true or false) to each of the following categories:
"""
###

# Followup
FOLLOWUP_PROMPT = """
The user cannot see this image. Answer user's questions about it.

Answer in a single JSON object containing two keys.
The first key is "response_brief" and its value is a single
sentence that can stand on its own. It directly answers the
specific request at the end of this prompt.
The second key is "response_full" and its value provides maximum
three sentences of additional detail,
without repeating the information in the first key.
If there is no more detail you can provide,
omit the "response_full" key instead of having an empty key.
IMPORTANT: answer only in JSON.
Example response:
{
"response_brief": "One sentence response to the user request.",
"response_full": "Further details. Maximum three sentences."
}
"""
OLD_END_OF_FOLLOWUP_PROMPT = """
The user may add a note to focus on a specific part of the image
and an updated picture with the area of interest marked with a red rectangle.
In this case, answer the question ONLY about the contents
of this part of the image.
Do not mention the red rectangle in your answer.
"""

FOLLOWUP_PROMPT_FOCUS = """
IMPORTANT NOTE:
The graphic contains a red rectangle
outlining a specific part of the image.
Answer the question ONLY about the contents of this part of the image.
Do not mention the red rectangle in your answer.
It is not part of the original image,
and was programmatically added for you only to highlight the area of interest.
"""
###

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
Include in the bounding boxes only the illustrations of the objects themselves,
not any surrounding text or arrows.

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
###
