# Named Entity Recognition (NER)

This preprocessor takes alt text and a photograph. It uses [CLIPScore](https://arxiv.org/abs/2104.08718) to determine whether or not the alt text describes the content of the photo (rather than adding additional context or the photo being for "flavor", as is often done in news articles).
If the score is above a certain threshold, the [Stanford Named Entity Recognizer](https://nlp.stanford.edu/software/CRF-NER.shtml) is used to find and tag named entities in this alt text.
The results are included in the response.

![The First family and Bo, their new Portuguese water dog, walk on the South Lawn of the White House.](https://upload.wikimedia.org/wikipedia/commons/3/3c/Obama_family_walks_with_First_Dog_Bo_4-14-09.jpg)

For example, if the above photo had the alt text "Michelle Obama and her oldest daughter walk behind a small black dog whilst Barack Obama and their youngest daughter walk a short distance behind them.", the photo and text could both be used as inputs to this preprocessor.
The preprocessor would run CLIPScore and yield a high mark since the caption accurately describes the photo.
Then, it would use the NER module to identify the named entities in the caption (i.e., Michelle and Barack Obama). All of these data would be returned as part of the data field in the preprocessor's response, shown below.
```json
{
  "alttxt": "\"Michelle Obama and her oldest daughter walk a small black dog whilst Barack Obama and their youngest daughter walk a short distance behind them.\"",
  "clipscore": 0.941,
  "ner": [
    {
      "index": 1,
      "tag": "PERSON",
      "value": "Michelle"
    },
    {
      "index": 2,
      "tag": "PERSON",
      "value": "Obama"
    },
    {
      "index": 13,
      "tag": "PERSON",
      "value": "Barack"
    },
    {
      "index": 14,
      "tag": "PERSON",
      "value": "Obama"
    }
  ]
}
```
A handler could then incorporate these named entities (the people Barack and Michelle Obama) into the representation of the photo, for example by saying that the photo contains Barack Obama and Michelle Obama and two other people, rather than that the photo contains four people.
