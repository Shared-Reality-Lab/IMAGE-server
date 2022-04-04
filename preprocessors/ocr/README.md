# OCR Preprocessor
## What is OCR?
OCR is an acronym for Optical Character Recognition which is the process of extracting machine-readable text pictured in graphics or documents.
## About this preprocessor
This preprocessor is used to extract text from any graphics that we process to further the user's understanding of its contents. The preprocessor makes use
of the [Microsoft Azure OCR API](https://westus.dev.cognitive.microsoft.com/docs/services/computer-vision-v3-2/operations/56f91f2e778daf14a499f20d) and returns
regions of text with corresponding bounding boxes in normalized pixel coordinates.
Note that the return codes and body used by Azure do not necessarily match [those specified for IMAGE preprocessors](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#preprocessors=).
