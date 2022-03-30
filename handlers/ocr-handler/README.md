# OCR Handler
## What is OCR?
OCR is an acronym for Optical Character Recognition which is the process of extracting machine-readable text pictured in graphics or documents.
## About this handler
The OCR handler takes data output from our [OCR preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/ocr) 
as well as other preprocessors that provide data regarding objects or segments in a graphic. The handler reconciles the bounding boxes of the discovered
text regions with the bounding boxes of other graphic elements to provide a text rendering of the text contained within a graphic, as well the elements
in which they are contained.
