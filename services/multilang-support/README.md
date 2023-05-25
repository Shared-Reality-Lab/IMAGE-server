# multilang-support

> author: Antoine Phan (@notkaramel)

## Description
Language Translation Service for IMAGE project. The service translate segments of text from English (IMAGE default language) to other languages.

## Implementation
### Tokenizer & Model
- To avoid confusion on which tokenizer/model to use, we use `AutoTokenizer` and `AutoModelFOrSeq2SeqLM` from `transformers` library to automatically select the correct tokenizer/model based on the model (checkpoint) name.
```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
```
- If the model is based on `t5`, such as [`t5-small`](https://huggingface.co/t5-small) or [`flan-t5-small`](https://huggingface.co/google/flan-t5-small), the tokenizer is a `T5Tokenizer`.
- Similarly, `t5`-based models will use `T5ForConditionalGeneration` models.

- If the model is based on `Marian`, such as [`Helsinki-NLP/opus-mt-en-fr`](https://huggingface.co/Helsinki-NLP/opus-mt-en-fr) or [`Helsinki-NLP/opus-mt-en-de`](https://huggingface.co/Helsinki-NLP/opus-mt-en-de), the tokenizer and model are  `MarianTokenizer` and `MarianMTModel` respectively.
### Translation App (Flask/Gunicorn)

### Docker Image
- Here is how the docker image is organized:
```
/app
├── requirements.txt
└── src
    ├── translate.py
    └── utils.py
```
- `gunicorn` will be called from the `app` repository.


### Docker Compose as an IMAGE service
- [IMAGE-server/wiki on Services](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#services)
- 


## Overview
- Using [`t5-small`](https://huggingface.co/t5-small) model from HuggingFace, there are available 4 languages: English, French, Romanian, German

- Using Google's [`flan-t5-small`](https://huggingface.co/google/flan-t5-small) model, there are lots of languages to choose from: **English**, **Spanish**, **French**, **Chinese**, **Italian**, **Russian**, etc.

## Attribution
- License: https://creativecommons.org/licenses/by-nc-sa/4.0/
- Model from https://github.com/Helsinki-NLP/Tatoeba-Challenge/tree/master/models
- 