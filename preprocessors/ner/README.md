# Named Entity Recognition (NER)

This preprocessor takes alt text and a photograph. It uses [CLIPScore](https://arxiv.org/abs/2104.08718) to determine whether or not the alt text describes the content of the photo (rather than adding additional context or the photo being for "flavor", as is often done in news articles).
If the score is above a certain threshold, the [Stanford Named Entity Recognizer](https://nlp.stanford.edu/software/CRF-NER.shtml) is used to find and tag named entities in this alt text.
The results are included in the response.
