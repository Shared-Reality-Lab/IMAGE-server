#!/usr/bin/env python3

# Importing Tokenizer and Model library, and torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import time
import logging

# list of supported languages in ISO 639-1 code
SUPPORTED_LANGS = ["fr", "es", "de"]

# Configure the logging settings
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%y-%m-%d %H:%M %Z",
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


# A logging wrapper function/decorator
def log(func):
    """
    Timing & logging decorator for functions.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        function_output = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_time = int(elapsed_time*1000)  # convert [s] to [ms]
        return function_output, elapsed_time
    return wrapper


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
        self.CHECKPOINT = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
        try:
            self.TOKENIZER = AutoTokenizer.from_pretrained(self.CHECKPOINT)
            self.MODEL = AutoModelForSeq2SeqLM.from_pretrained(self.CHECKPOINT)
            LOGGER.info(f"Translator({src_lang}, {tgt_lang}) instantiated!")
            # set device
            self.set_model_device()
            LOGGER.info(
                f"Model {self.CHECKPOINT} running on {self.DEVICE_NAME}")
            Translator.Translators.append(self)
        except Exception as e:
            LOGGER.error(e)
            LOGGER.info(
                f"Failed to instantiate Translator({src_lang}, {tgt_lang})!")
            LOGGER.debug(f"Failed to start model: {self.CHECKPOINT}")

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

    def translate(self, segment: list) -> list:
        """
        Translate the segment - (a list of strings)
        Steps:
        @param segment: The segment (type<list>) to be translated.
        1. Tokenize the segment to a tensor.
        2. Pass tokenized tensor through the model.
        3. Decode the translated tensor to a string.
        4. Append the translated string to a list.
        """
        # output list
        result = []
        for input_query in segment:
            # 1. Input query -> tensor
            input_tensor = self.tokenize_query_to_tensor(input_query)

            # 2. Input tensor -> output tensor
            output_tensor = self.generate_output_tensor(input_tensor)

            # 3. Output tensor -> query
            output_query = self.decode_generated_tensor(output_tensor)

            # 4. Translated query -> result
            LOGGER.info(f'Translated: "{input_query}" --> "{output_query}"')
            result.append(output_query)

        return result

    @staticmethod
    def get_translator(src_lang: str, tgt_lang: str):
        """
        Get the Translator object
        """
        try:
            for tr in Translator.Translators:
                target_tr = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
                if tr.CHECKPOINT == target_tr:
                    return tr
        except Exception as e:
            LOGGER.error(e)
            LOGGER.debug(f"Failed to get Translator({src_lang}, {tgt_lang})!")
            return None


@log
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
    # Dummy translation to test the service
    for lang in SUPPORTED_LANGS:
        LOGGER.info(Translator.get_translator("en", lang)
                    .translate([ready_message]).pop())
