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