# OCR Handler [DEMONSTRATION]
## What is OCR?
OCR is an acronym for Optical Character Recognition which is the process of extracting machine-readable text pictured in graphics or documents.
We expect that in the future the OCR preprocessor results will likely be rolled
into the [photo audio handler](../photo-audio-handler).
## About this handler
The OCR handler takes data output from our [OCR preprocessor](../../preprocessors/ocr) 
as well as other preprocessors that provide data regarding objects or segments in a graphic. The handler reconciles the bounding boxes of the discovered
text regions with the bounding boxes of other graphic elements to provide a text rendering of the text contained within a graphic, as well the elements
in which they are contained.
## Observations
As it is, the handler only checks the object-text relationships, not considering the object-object relationships, which sometimes gives a weird reading depending on the order in the detected objects array. This happens because the lines of text stick to the first object that encloses them.
For example: if an image shows a hand holding a bottle with text on it, the handler's output will output one of the following cases.
* The bottle is first in the detected objects array:
```
The following objects were detected: a bottle containing the text "skin lotion". A person.
```
* The person is first in the detected objects array:
```
The following objects were detected: a person containing the text "skin lotion". A bottle.
```