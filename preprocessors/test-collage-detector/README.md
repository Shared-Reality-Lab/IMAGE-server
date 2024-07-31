# Per-image Classifier for Identifying Collages or Non-collages

Alpha quality: Insufficiently refined to be tested by end-users.

## Overview

This preprocessor classifies whether the input image is a collage or a non-collage. The Dockerfile builds a fully functioning IMAGE preprocessor.

This preprocessor contains the implementation of a collage classification algorithm called SbRIF (Strong-biased Regional Identity Filtering for Collage Detection). The algorithm requires an image of any size as an input, and returns a boolean result. The diagrams below illustrate the 
SbRIF pipeline and its performance on a small dataset ([link](https://drive.google.com/drive/folders/1EdXZ4889YC5iMV1Pa8UzF_KMybvACxjC?usp=sharing)).

![](images/SBRIF(whitebkgd).png)  
*The block diagram of SbRIF.*

![](images/cm(whitebkgd).png)  
*The testing results on 220 images (110 collages as positive samples, 110 non-collages as negative samples).*

## Usage as a Standalone Module

The below example illustrates how to use the function generally (not as an IMAGE Preprocessor). For a legal IMAGE Preprocessor, please refer to detect.py and you can see similar function calls there. 

    # This is an example usage
    from SBRIF import SbRIF
    import cv2
    
    # Instantiating an object with the sugguesting hyper-parameter
    model = SbRIF(t=0.75)
    
    # Reading the image and perform inference
    img = cv2.imread('image.jpg', 0)
    is_collage = model.inference(img)
    
    # Parsing the result
    if is_collage:
        print('The image is identified as a collage.')
    else:
        print('The image does not be identified as a collage.')

## Libraries Used

The following libraries were used for creating this preprocessor.

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Requests  | [Link](https://pypi.org/project/requests/)  | Apache 2.0|
| Flask | [Link](https://pypi.org/project/Flask/)  | BSD-3-Clause License|
| Numpy | [Link](https://pypi.org/project/numpy/)  | BSD-3-Clause License|
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License|
| Werkzeug | [Link](https://pypi.org/project/Werkzeug/) | BSD-3 |
| opencv-python | [Link](https://github.com/skvark/opencv-python) | MIT License(MIT) |
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |

The versions for each of these libraries has been mentioned in the requirements.txt.
