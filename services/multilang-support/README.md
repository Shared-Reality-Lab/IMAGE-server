# multilang-support

> author: Antoine Phan (@notkaramel)

## Description
Translation Service for IMAGE project. The service translate segments of text from English (IMAGE default language) to other languages.

## Overview
- All models used within the Helsinki-NLP/opus-mt family are licensed under **CC-BY 4.0 License**. See **[Attribution](#attribution)** below.
- The model is a `MarianMTModel` from `transformers` library.
- Models are downloaded at program start-up, see `instantiate()` in `src/utils.py`. Each model is weighted around ~300MB.
- To extend support for other languages, developer can add language code(s) in ISO 639-1 format to `SUPPORTED_LANGS` list in `src/utils.py`. The service must be restarted for the changes to take effect.

## Behaviour/Response Codes
- `200`: Success, translation is returned.
- `204`: No content returned, source and target languages are the same.
- `500`: Service Error: Unexpected edge cases.
- `501`: Not implemented, source or target language is not supported yet. The debug log would show the attempted request to the service.

## Implementation
### Tokenizer & Model
- To avoid confusion on which tokenizer/model to use, we use `AutoTokenizer` and `AutoModelFOrSeq2SeqLM` from `transformers` library to automatically select the correct tokenizer/model based on the model (checkpoint) name.
  ```python
  from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
  ```
  - If the model is based on `t5`, such as [`t5-small`](https://huggingface.co/t5-small) or [`flan-t5-small`](https://huggingface.co/google/flan-t5-small), the tokenizer is a `T5Tokenizer`.
  - Similarly, `t5`-based models will use `T5ForConditionalGeneration` models.

- The model used for this service is based on `MarianMT`. Documentation can be found here [MarianMT on HuggingFace](https://huggingface.co/docs/transformers/main/en/model_doc/marian). For example:
  - For French translation, we use [`Helsinki-NLP/opus-mt-en-fr`](https://huggingface.co/Helsinki-NLP/opus-mt-en-fr).
  - For German translation, we can use [`Helsinki-NLP/opus-mt-en-de`](https://huggingface.co/Helsinki-NLP/opus-mt-en-de) model.
- Tokenizer and model are  `MarianTokenizer` and `MarianMTModel` respectively.


### Translation Sequential Flow (from `src/utils.py`)
1. For each segment/query (a string), we tokenize it using the `TOKENIZER`.(`tokenize_query_to_tensor`)
   - `Helsinki-NLP/opus-mt` models use `MarianTokenizer` which is a slow tokenizer. See [HuggingFace Tokenizers](https://huggingface.co/docs/transformers/v4.30.0/en/main_classes/tokenizer#tokenizer)
2. We then use the `MODEL` to take in the tokenized segment/query, and generate an output tensor (`generate_output_tensor`)
   - Documentation on `generate()` method parameter: [Text Generation#GenerationConfig](https://huggingface.co/docs/transformers/v4.30.0/en/main_classes/text_generation#transformers.GenerationConfig)
3. Decode the output tensor into a string using the `TOKENIZER` (`decode_generated_tensor`)
4. Append the decoded string to a list to be returned.

### Docker Image
- Here is how the docker image is organized:
```
/app
├── requirements.txt
└── src
    ├── translate.py
    └── utils.py
├── translation.schema.json
```
- `gunicorn` will be called from the `app` repository.


### Docker Compose as an IMAGE service
- [IMAGE-server/wiki on Services](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#services)
- Model repo from HuggingFace: [Helsinki-NLP/opus-mt-en-fr](https://huggingface.co/Helsinki-NLP/opus-mt-en-fr/tree/main)

  
## Attribution
- LICENSE: https://creativecommons.org/licenses/by-nc-sa/4.0/
  - Free to:
    - **Share**: copy and redistribute the material in any medium or format
    - **Adapt**: remix, transform, and build upon the material
  - Under the following terms:
    - **Attribution**:  You must give appropriate credit, provide a link to the license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.
    - **NonCommercial**:  You may not use the material for commercial purposes.
    - **ShareAlike**: If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.
    - **No additional restrictions**: You may not apply legal terms or technological measures that legally restrict others from doing anything the license permits.
- LICENSE legal code: https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode
- Model from https://github.com/Helsinki-NLP/Tatoeba-Challenge/tree/master/models

## Old trials
- Using general purpose models:
  - [`t5-small`](https://huggingface.co/t5-small)  from HuggingFace.
    - Only 4 available languages: English, French, Romanian, German
    - Moderately faster than `Google/flan-t5-small`, but very inaccurate.
    - Other larger `t5` models can perform better, but takes a great amount of time to translate.

  - [`Google/flan-t5-small`](https://huggingface.co/google/flan-t5-small):
    - Can translate to and from lots of languages.
    - Moderately slower than `t5-small`, but more accurate. Still, takes a lots of time to translate.

  - Other larger `t5`-based models from HuggingFace or Google: 
    - Heavy weight, even the *`base`* version takes ~1GB of memory.
    - Do not perform as well as `Helinski-NLP/opus-mt` models.