# Celebrity Detection Preprocessor

This preprocessor detects the celebrities present in an image. The code crops individual people in an image and uses Azure Computer Vision API to determine if the cropped individual is a celebrity. 
The code performing all these operations can be found in `celebrity-detector.py`


## Installation

 In order to use this module as an API, first build the image using :

 ```bash
 docker build -t <image-name>
 ```

 Then run the container with :

 ```bash
 docker run -d --rm --gpus all -p <port>:5000 <image-name>
 ```
