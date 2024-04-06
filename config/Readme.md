# IMAGE Config

This Folder (Config) should contain the .env files required for IMAGE server preprocessors to run precisely.

``` Note: Some preprocessors may require other config as well. Refer to 'Environment setup' section inside Readme of each preprocessor for updated documentation.```

## Environment Files

### maps.env
This file contains the API key used to call Google Places API. [Here](https://developers.google.com/maps/documentation/places/web-service/get-api-key) is the documentation for how to obtain a valid API key. This env file is required by the following preprocessors:
* [autour preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/autour)
* [openstreetmap preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/openstreetmap)

Following is the sample format of maps.env file:
```
GOOGLE_PLACES_KEY = [INSERT KEY STRING]
```

### apis-and-selection.env
Entries in this env file are required by the following preprocessors:
* [ocr-clouds-preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/ocr)

Following is the sample format of apis-and-selection.env file:

```
AZURE_API_KEY = [INSERT KEY STRING]
FREEOCR_API_KEY = [INSERT KEY STRING]
GOOGLE_APPLICATION_CREDENTIALS = [INSERT KEY FILE PATH AS STRING]
CLOUD_SERVICE = [INSERT OPTION STRING (see options below)]
```
* `CLOUD_SERVICE` determines the desired cloud service to be used. Its possible values are:
    * `AZURE_OCR` (for [Microsoft Azure OCR API](https://westus.dev.cognitive.microsoft.com/docs/services/computer-vision-v3-2/operations/56f91f2e778daf14a499f20d))
    * `AZURE_READ` (for [Microsoft Azure Read API](https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/how-to/call-read-api))
    * `GOOGLE_VISION` (for [Google Cloud Vision API](https://cloud.google.com/vision/docs/ocr))
    * `FREE_OCR` (for [Free OCR API](https://ocr.space/OCRAPI))
* `AZURE_API_KEY` is found in your [Azure portal](https://portal.azure.com)
* `FREEOCR_API_KEY` can be obtained at [OCR API portal](https://ocr.space/ocrapi)
* `GOOGLE_APPLICATION_CREDENTIALS` contains path to credentials file. Refer [documentation](https://cloud.google.com/docs/authentication/application-default-credentials#GAC) for details.


### azure-api.env
This env file is required by the following preprocessors:
* [graphic tagger](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/graphic-tagger)

Following is the sample format of azure-api.env file:
```
AZURE_API_KEY = [INSERT KEY STRING]
```
