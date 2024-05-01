Beta quality: Useful enough for testing by end-users.

This preprocessor is used to determine if the image is an indoor or an outdoor image. This preprocessor could be used for getting more information about the image as well. This preprocessor has been outsourced to Azure and we access it using the API key.

According to Azure documents the preprocessor can return [86 tags](https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/category-taxonomy), but we have limited the images to just indoor and outdoor.

Once the Azure API returns the values, we have dockerised the container and ensured that the Azure values are returned in an appropriate format. The codefile also has appropriate comments.

```Note: This preprocessor would not work by directly pulling this repository. One would need the API key to run this preprocessor.```


## Environment setup
The environment file (azure-api.env) should contain the API key used to call Azure API. `AZURE_API_KEY` is found in your [Azure portal](https://portal.azure.com).: 

Following is the sample format of azure-api.env file:
```
AZURE_API_KEY = [INSERT KEY STRING]
```