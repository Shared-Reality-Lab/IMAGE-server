This preprocessor is used to determine if the image is an indoor or an outdoor image. This preprocessor could be used for getting more information about the image as well. This preprocessor has been outsourced to Azure and we access it using the API key.

According to Azure documents the preprocessor can return [86 tags](https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/category-taxonomy), but we have limited the images to just indoor and outdoor.

Once the Azure API returns the values, we have dockerised the container and ensured that the Azure values are returned in an appropriate format. The codefile also has appropriate comments.

```Note: This preprocessor would not work by directly pulling this repository. One would need the API key to run this preprocessor.```
