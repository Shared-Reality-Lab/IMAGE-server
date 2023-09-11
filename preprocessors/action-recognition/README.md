# About

This preprocessor is used for detecting human action from images. The preprocessor was trained using transfer learning with a pretrained DINOv2 model as a base and a linear head trained from scratch on action images. DINOv2 ViT-S/14 distilled was released by Meta AI Research (https://github.com/facebookresearch/dinov2). Output from object detection is used to find all instances of 'person' in a graphic and classify each instance individually

## Datasets Used

The following datasets were used to train the model:

| Dataset Name                       | Link                                                                             |
| ---------------------------------- | -------------------------------------------------------------------------------- |
| BU101                              | [Link](https://cs-people.bu.edu/sbargal/BU-action/)                              |
| Stanford 40 Actions                | [Link](http://vision.stanford.edu/Datasets/40actions.html)                       |
| Pascal VOC                         | [Link](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/shape/action/) |
| Action-net                         | [Link](https://github.com/OlafenwaMoses/Action-Net)                              |
| Willow Actions                     | [Link](https://www.di.ens.fr/willow/research/stillactions/)                      |
| People Playing Musical Instruments | [Link](http://ai.stanford.edu/~bangpeng/ppmi.html)                               |

## Output

The preprocessor outputs any actions detected with confidence over 70% with the object ID of the person from the object detection preprocessor.

The actions that can currently be detected are the following :

- baby_crawling
- blowing_candles
- brushing_teeth
- clapping
- climbing
- drinking
- eating
- fighting
- fishing
- gardening
- jumping
- lunging
- playing_instrument
- doing_push_ups
- reading
- riding_bike
- riding_horse
- running
- shaving_beard
- sitting
- sleeping
- taking_photos
- walking
- watching_tv
- writing_on_board
