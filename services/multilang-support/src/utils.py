#!/usr/bin/env python3

# Importing Tokenizer and Model library, and torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import time
import logging

# list of supported languages in ISO 639-1 code
SUPPORTED_LANGS = ["fr"]

# Configure the logging settings
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%y-%m-%d %H:%M %Z",
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class Translator:
    """
    A Translator class that handles the translation process, containing:
    - CHECKPOINT: the checkpoint to be used
    - TOKENIZER: to tokenize the input text
    - MODEL: to generate translation
    - DEVICE: the device to be used (CPU or GPU)
    - DEVICE_NAME: the device name to be used (CPU or GPU)
    ! Public models: https://github.com/Helsinki-NLP/Opus-MT#public-mt-models
    ! Models license: CC-BY 4.0 License
    """
    # Static variable to keep track of all Translator instances
    Translators = []  # list of translator instances

    def __init__(self, src_lang: str, tgt_lang: str) -> None:
        """
        Instantiate the Translator class.
        @param:
        - src_lang: the source language in ISO 639-1 code
        - tgt_lang: the target language in ISO 639-1 code
        """
        # Getting model checkpoint from downloaded folder (see Dockerfile)
        # self.CHECKPOINT = f"/app/models/opus-mt-{src_lang}-{tgt_lang}"
        self.NAME = f"Translator({src_lang}, {tgt_lang})"
        try:
            model_path = f"/app/models/opus-mt-{src_lang}-{tgt_lang}"
            LOGGER.info(f"Loading model from local path: {model_path}")
            self.TOKENIZER = AutoTokenizer.from_pretrained(
                model_path, local_files_only=True)
            self.MODEL = AutoModelForSeq2SeqLM.from_pretrained(
                model_path, local_files_only=True)

            LOGGER.info(f"{self.NAME} instantiated!")
            self.set_model_device()
            LOGGER.info(f"{self.NAME} running on {self.DEVICE_NAME}")
            Translator.Translators.append(self)
        except Exception as e:
            LOGGER.error(e)
            LOGGER.info(f"Failed to instantiate {self.NAME}!")
            LOGGER.debug(f"Expected model path: {model_path}")

    def set_model_device(self):
        num_gpus = torch.cuda.device_count()
        device_id = 0
        while num_gpus > 0 and device_id < num_gpus:  # There is at least 1 GPU
            try:
                self.DEVICE = torch.device(f"cuda:{device_id}")
                self.DEVICE_NAME = torch.cuda.get_device_name(device_id)
                device_id += 1
                self.MODEL.to(self.DEVICE)
            except Exception as e:
                LOGGER.warning(f'Error using {self.DEVICE_NAME}: {e}')
                if device_id >= num_gpus:
                    LOGGER.warning("No GPU available, using CPU.")
                    break

    def tokenize_query_to_tensor(self, query: str):
        """
        STEP 1: Tokenize the query using the tokenizer.
        @param query: The query (type<str>) to be tokenized.
        @return: The tokenized query as a torch.Tensor.
        """
        # return TOKENIZER.encode(query).to(DEVICE)
        LOGGER.debug('(1) Tokenizing input.')
        return self.TOKENIZER(query, return_tensors="pt")\
            .to(self.DEVICE)["input_ids"]

    def generate_output_tensor(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        STEP 2: Translate the input_ids tensor to an output query.
        @param
        input_ids: The decoded tensor (type<torch.Tensor>) to be translated.
        """
        # TODO: Add parameters to control/optimize the translation.
        LOGGER.debug("(2) Generating tensor.")
        return self.MODEL.generate(input_ids,
                                   max_time=1,
                                   max_length=256,
                                   num_beams=4,
                                   use_cache=True,
                                   temperature=0.7,
                                   ).to(self.DEVICE)

    def decode_generated_tensor(self, translated_tensor: torch.Tensor) -> str:
        """
        STEP 3: Decode the translated tensor to a string.
        @param translated_tensor: <class 'torch.Tensor'>
        @return: <class 'str'>
        """
        LOGGER.debug("(3) Decoding tensor.")
        translated_result = self.TOKENIZER.decode(
            translated_tensor[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        return translated_result

    def translate(self, segment: list):
        """
        Translate the segment - (a list of strings)
        Steps:
        @param segment: The segment (type<list>) to be translated.
        @return:
        - `translations`: list of translated segments (type<list>)
        - `translate_time`: time taken in ms (type<int>)
        """
        # output list
        translations = []
        start_translate = time.time()
        for input_query in segment:
            # 1. Input query -> tensor
            input_tensor = self.tokenize_query_to_tensor(input_query)

            # 2. Input tensor -> output tensor
            output_tensor = self.generate_output_tensor(input_tensor)

            # 3. Output tensor -> query
            output_query = self.decode_generated_tensor(output_tensor)

            # 4. Translated query -> result
            # LOGGER.info(f'Translated: "{input_query}" --> "{output_query}"')
            translations.append(output_query)
        finish_translate = time.time()
        translate_time = int((finish_translate - start_translate)*1000)
        return [translations, translate_time]

    @staticmethod
    def get_translator(src_lang: str, tgt_lang: str):
        """
        Get the Translator object
        """
        target_Translator_name = f"Translator({src_lang}, {tgt_lang})"
        try:
            for tr in Translator.Translators:
                if tr.NAME == target_Translator_name:
                    return tr
        except Exception as e:
            LOGGER.error(e)
            LOGGER.debug(f"Failed to get {target_Translator_name}!")
            return None


def instantiate():
    """
    Instantiate a list of Translator objects
    """
    source_lang_default = "en"
    target_langs = SUPPORTED_LANGS
    for tgt_lang in target_langs:
        Translator(source_lang_default, tgt_lang)


if "utils" in __name__ or __name__ == "__main__":
    instantiate()
    ready_message = "Translation service is instantiated and ready!"
    LOGGER.info(ready_message)
    # Dummy translation to test if the service is ready
    for lang in SUPPORTED_LANGS:
        LOGGER.info(Translator.get_translator("en", lang)
                    .translate([ready_message])[0].pop())
