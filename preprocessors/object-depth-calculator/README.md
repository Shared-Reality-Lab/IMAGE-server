# Object Depth Calculator

This preprocessor aims at combining the outputs from the depth-map-generator preprocessor and the obejct-detection preprocessor. 
It calculates the depth of an object by taking the median pixel depth value within the bounding box coordinates as seen in:

[Absolute distance prediction based on deep learning object detection and monocular depth estimation models](https://www.researchgate.net/publication/355872639_Absolute_distance_prediction_based_on_deep_learning_object_detection_and_monocular_depth_estimation_models)

The output will contain a series of object IDs which match the IDs generarated by the object detection [preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/object-detection-azure) as well as the median depth value of the object's bounding box. The depth is generatred by the depth-map-gen [preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/depth-map-gen) and will contain a number between 0 and 1, 0 being at the very front of the image plane and 1 being the furthest point. 

![image](https://user-images.githubusercontent.com/25232146/235528519-132d48e7-10a1-4ab4-a098-9fe3b734a422.png)
