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
* `CLOUD_SERVICE="AZURE_OCR"`
* `CLOUD_SERVICE="AZURE_READ"`
* `CLOUD_SERVICE="GOOGLE_VISION"`
* `CLOUD_SERVICE="FREE_OCR"`

The path to an environment file containing this variable should be provided in the `docker-compose.yml`, right in the `env_file` field of the `ocr-clouds-preprocessor` service.
## Environment setup
The environment file (apis-and-selection.env) should contain the desired cloud service to be used, and the corresponding api keys.

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

## Recommended API
According to the tests, the best APIs for the preprocessor's needs are Microsoft Azure Read and Google Cloud Vision. However, the `Read API` has been selected as the default one because it gets the correct order of the words or lines of text, as opposed to Vision API. This matters because currently there is no structure that corrects the order of the recognized text; the output from the API is used as it is in the handler.

Another downside of the Vision API is that it recognizes more words than the Read API, but it is mostly noise or forms in the background recognized as characters.
## More about the used cloud services
Here are some helpful facts about the APIs that can be used for this preprocessor.
### Microsoft Azure OCR API
* Accepts only image files.
* It's synchronous, which means it obtains an immediate response.
* It can recognize text from a wide variety of languages.
* Uses older recognition models.
* Extracts small text quickly.
### Microsoft Azure Read API
* Accepts image files and PDFs.
* It's asynchronous, which means there is a small waiting time for the response.
* It recognizes text from many languages, but less than with Azure's OCR API.
* Uses the latest recognition models.
* It is optimized for files with significant amount of text and visual noise, as well as handwriting.
* [Here](https://learn.microsoft.com/en-us/rest/api/computervision/3.1/get-read-result/get-read-result?tabs=HTTP) is a sample response.

[Here](https://learn.microsoft.com/en-us/training/modules/read-text-computer-vision/2-ocr-azure) is more information on the differences between Microsoft Azure's APIs.
### Google Cloud Vision API
* Accepts only image files.
* It's synchronous, which means it obtains an immediate response.
* It can also be used asynchronously with the `DOCUMENT_TEXT_DETECTION` feature, which is very similar to Azure's Read API.
* Language hints can be given to get better results.
### Free OCR API
* There is a daily limit for the requests sent from the same computer.
* Performance can be checked in the API status page.
* The Engine to use can be changed, they have different characteristics.
* Language can be specified optionally. The default is English in Engine1, only Engine2 has automatic western language detection.
