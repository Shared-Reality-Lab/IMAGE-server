# OCR Preprocessor
## What is OCR?
OCR is an acronym for Optical Character Recognition which is the process of extracting machine-readable text pictured in graphics or documents.
## About this preprocessor
This preprocessor is used to extract text from any graphics that we process to further the user's understanding of its contents.
The preprocessor can use one of the following API options:
* [Microsoft Azure OCR API](https://westus.dev.cognitive.microsoft.com/docs/services/computer-vision-v3-2/operations/56f91f2e778daf14a499f20d)
* [Microsoft Azure Read API](https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/how-to/call-read-api)
* [Google Cloud Vision API](https://cloud.google.com/vision/docs/ocr)
* [Free OCR API](https://ocr.space/OCRAPI)
Either way, it returns regions of text with corresponding bounding boxes in normalized pixel coordinates.
Note that the return codes and body used by the APIs do not necessarily match [those specified for IMAGE preprocessors](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#preprocessors=).
## API selection feature
The desired cloud service is determined by an environment variable called `CLOUD_SERVICE`, it is a string and the possible values are:
* `CLOUD_SERVICE="OCR_AZURE"`
* `CLOUD_SERVICE="READ_AZURE"`
* `CLOUD_SERVICE="VISION_GOOGLE"`
* `CLOUD_SERVICE="OCR_FREE"`
The path to an environment file containing this variable should be provided in the `docker-compose.yml`, right in the `env_file` field of the `ocr-clouds-preprocessor` service.
## Environment setup
The environment file should also include the necessary keys for using the desired cloud service(s). The format is provided since the specific variable names are used in the code.
```
AZURE_API_KEY = [INSERT KEY STRING]
FREEOCR_API_KEY = [INSERT KEY STRING]
GOOGLE_APPLICATION_CREDENTIALS = [INSERT KEY FILE PATH AS STRING]
CLOUD_SERVICE = [INSERT OPTION STRING (see options above)]
```