# IMAGE Config

This Folder (Config) should contain the .env files required for IMAGE server preprocessors to run precisely.

## Environment Files

### maps.env
This env file is required by the following preprocessors:
* [autor preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/autour)
* [openstreetmap preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/openstreetmap)

Following is the sample format of maps.env file:
```
GOOGLE_PLACES_KEY = [INSERT KEY STRING]
```

### apis-and-selection.env
This env file is required by the following preprocessors:
* [ocr-clouds-preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/ocr)

The desired cloud service is determined by an environment variable called CLOUD_SERVICE, it is a string and the possible values are:
"AZURE_OCR" / "AZURE_READ" / "GOOGLE_VISION" / "FREE_OCR"

Following is the sample format of apis-and-selection.env file:

```
AZURE_API_KEY = [INSERT KEY STRING]
FREEOCR_API_KEY = [INSERT KEY STRING]
GOOGLE_APPLICATION_CREDENTIALS = [INSERT KEY FILE PATH AS STRING]
CLOUD_SERVICE = [INSERT OPTION STRING (see options above)]
```

### azure-api.env
This env file is required by the following preprocessors:
* [graphic tagger](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/graphic-tagger)

Following is the sample format of azure-api.env file:
```
AZURE_API_KEY = [INSERT KEY STRING]
```
