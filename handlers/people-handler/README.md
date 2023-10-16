This handler manages information generated by several preprocessors: `object-detector`, `expression-recognition`, `clothes-detector`, `celebrity-detector`, and `caption-recognition`.

 The handler follows these steps:

 ## Step 1
 Initially, it determines whether the input image contains people by referring to the output generated by `object-detector`, `semantic-segmentation`, and `graphic-tagger`. The code for this determination can be found in `check.py`.

 ## Step 2
 If the aforementioned AI models detect people, it then determines the number of people in the image. For a single person in the image, `single_person.py` processes the information. For two people, `two_people.py` processes the information, and for other cases with multiple people, `multiple.py` handles the processing. This involves combining outputs from specialized AI models such as `expression-recognition`, `clothes-detector`, and `celebrity-detector` to form a coherent sentence.

 ## Step 3
 The processed sentence is then concatenated with a generated caption in `people_handler.py.` Only the portion of the caption containing information about actions and scenes in the image is appended. This information is obtained from [`find_subject_object.py.`](https://github.com/rock3125/enhanced-subject-verb-object-extraction/blob/master/subject_verb_object_extract_test.py)

 The following is a pictorial representation of the handler
 ![Sample Image](system.png)


## A few things to note
This handler would not work if the followng preprocessors are disabled:
1. Semantic Segmentation
2. Object Detection
