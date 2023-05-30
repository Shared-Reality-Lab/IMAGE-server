#!/usr/bin/env python3

# Importing Tokenizer and Model library, and torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import time
import logging

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,
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
        elapsed_time *= 1000  # convert [s] to [ms]
        LOGGER.debug(f"\'{func.__name__}\' takes {int(elapsed_time)} ms")
        return function_output, elapsed_time

    return wrapper


# Only for t5-based models, we required a prefix to be added to the input text.
# This prefix is the task we want to perform.
# T5_TASK_PREFIX = "Translate English to <TARGET_LANGUAGE>: "
T5_TASK_PREFIX = "Translate English to French: "

# Depending on the model chosen from HuggingFace,
# the tokenizer and model will be different.
# See README.md#Implementation for more details.
MODEL_CHECKPOINT = "Helsinki-NLP/opus-mt-en-fr"


# Set device to GPU if available, else CPU
# Issue: torch can detect cuda GPU but will not be able to use it
# if the GPU is out of memory. (Happened during unicorn testing)


@log
def set_device(device_id: int = 0):
    """
    Set the device to GPU if available, else CPU.
    For GPUs: device_id starts from 0 and increments.
    For CPUs: device_id is -1.

    To handle the issue of torch detecting cuda GPU but not able to use it,
    we set the device to try out all GPUs before falling back to CPU.
    """
    global DEVICE, DEVICE_NAME
    if device_id >= 0:
        DEVICE = torch.device(f"cuda:{device_id}")
        DEVICE_NAME = torch.cuda.get_device_name(device=DEVICE)
    else:
        DEVICE = torch.device("cpu")
        DEVICE_NAME = "CPU"

    return True


# Tokenizer and Model ready to be instantiated
@log
def instantiate():
    global TOKENIZER, MODEL
    global DEVICE, DEVICE_NAME
    num_gpus = torch.cuda.device_count()
    LOGGER.info(f"Instantiating: {MODEL_CHECKPOINT} tokenizer and model")

    TOKENIZER = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT)
    LOGGER.debug("Tokenizer instantiated")

    MODEL = AutoModelForSeq2SeqLM.from_pretrained(MODEL_CHECKPOINT)
    LOGGER.debug("Model instantiated")

    device_id = 0
    while device_id < num_gpus:
        try:
            set_device(device_id=device_id)
            device_id += 1
            MODEL = MODEL.to(DEVICE)
            # if it is able to set model to device, it means that GPU is usable
            # otherwise we will try the next GPU
            break
        except Exception as e:
            LOGGER.warning(f'Error using {DEVICE_NAME}: {e}')
            if device_id >= num_gpus:
                LOGGER.warning("No GPU available, using CPU.")
                set_device(device_id=-1)
                break
    LOGGER.debug(f"Model is running on {DEVICE_NAME}.")


@log
def tokenize_query_to_tensor(query: str):
    """
    STEP 1: Tokenize the query using the tokenizer.
    @param query: The query (type<str>) to be tokenized.
    @return: The tokenized query as a torch.Tensor.
    """
    # return TOKENIZER.encode(query).to(DEVICE)
    return TOKENIZER(query, return_tensors="pt").to(DEVICE).input_ids


@log
def generate_output_tensor(input_ids: torch.Tensor) -> torch.Tensor:
    """
    STEP 2: Translate the input_ids tensor to an output query.
    @param input_ids: The decoded tensor (type<torch.Tensor>) to be translated.
    @return: Newly generated tensor using the model (type<torch.Tensor>).
    TODO: Add parameters to control/optimize the translation.
    """
    # Parameters:
    MAX_TIME = 0.5  # seconds
    return MODEL.generate(input_ids, max_time=MAX_TIME)


@log
def decode_generated_tensor(translated_tensor: torch.Tensor) -> str:
    """
    STEP 3: Decode the translated tensor to a string.
    @param translated_tensor: <class 'torch.Tensor'>
    @return: <class 'str'>
    """
    translated_result = TOKENIZER.decode(
        translated_tensor[0],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )
    return translated_result


@log
def translate_helsinki(segment: list) -> list:
    """
    Translate the segment - (a list of strings) - using Helsinki-NLP models.
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
        LOGGER.debug(f'(1) Tokenizing input segment "{input_query}"')
        input_tensor, _time_inTensor = tokenize_query_to_tensor(input_query)

        # 2. Input tensor -> output tensor
        LOGGER.debug("(2) Generating new tensor.")
        output_tensor, _time_outTensor = generate_output_tensor(input_tensor)

        # 3. Output tensor -> query
        LOGGER.debug("(3) Decoding translated tensor.")
        output_query, _time_outQuery = decode_generated_tensor(output_tensor)

        # 4. Translated query -> result
        LOGGER.debug(f'(4) Appending "{output_query}" to result.')
        LOGGER.info(f'Translated: "{output_query}"')
        result.append(output_query)

    return result


if "utils" in __name__ or __name__ == "__main__":
    instantiate()
    LOGGER.debug(f"Using {DEVICE} on {DEVICE_NAME}")
    LOGGER.info('Service is instantiated and ready.')


class Translator:
    """
    (Not yet implemented fully)
    A Translator class that handles the translation process, containing:
    - MODEL_CHECKPOINT: the model checkpoint to be used (from Helsinki-NLP)
    - TOKENIZER
    - MODEL
    - DEVICE: the device to be used (CPU or cuda GPU)
    - DEVICE_NAME: the device name to be used (CPU or GPU)
    ! Public models: https://github.com/Helsinki-NLP/Opus-MT#public-mt-models
    Make sure to attribute properly (CC-BY 4.0 License) when using the models.
    """

    def __init__(self, src_lang: str, tgt_lang: str) -> None:
        self.MODEL_CHECKPOINT = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
        # expecting something like 'en-fr'

    def set_model_checkpoint(self, model_checkpoint: str) -> None:
        try:
            self.MODEL_CHECKPOINT = model_checkpoint
        except Exception as e:
            LOGGER.error(e)
            LOGGER.debug(
                "Exception occured, maybe the model checkpoint\
                    is invalid/unavailable")

    def get_model_checkpoint(self):
        return self.MODEL_CHECKPOINT

    def get_tokenizer(self):
        return self.TOKENIZER

    def get_model(self):
        return self.MODEL
