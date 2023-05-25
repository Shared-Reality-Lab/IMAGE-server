#!/usr/bin/env python3

# Importing Tokenizer and Model library, and torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch, time

# Depending on the model chosen from HuggingFace,
# the tokenizer and model will be different.
# See README.md#Implementation for more details.

MODEL_CHECKPOINT = "Helsinki-NLP/opus-mt-en-fr"

# For t5 based models, we required a prefix to be added to the input text.
# This prefix is the task we want to perform.
T5_TASK_PREFIX = "Translate English to French: "

# Set device to GPU if available
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'DETECTED: {DEVICE}')
DEVICE_NAME = torch.cuda.get_device_name(device=DEVICE) if DEVICE.type == 'cuda' else 'CPU'


# Tokenizer and Model ready to be instantiated
def instantiate():
    global TOKENIZER, MODEL
    print(f"~~ Instantiating {MODEL_CHECKPOINT} tokenizer and model ~~")
    TOKENIZER = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT)
    print(f'Finished instantiating {MODEL_CHECKPOINT} tokenizer.')

    MODEL = AutoModelForSeq2SeqLM.from_pretrained(MODEL_CHECKPOINT)
    print(f'Finished instantiating {MODEL_CHECKPOINT} model.')
    MODEL = MODEL.to(DEVICE)
    print(f'Model is running on {DEVICE_NAME}.')
    
def log(func):
    '''
    Timing & logging decorator for functions.
    '''
    def wrapper(*args, **kwargs):
        start_time = time.time()
        function_output = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"--- {func.__name__} takes {elapsed_time:.3f} seconds ---\n")
        with open('logs.txt', 'a') as f:
            f.write(f'Called {func.__name__} with {[str(arg) for arg in args]}\n')
            f.write(f'Elapsed time for {func.__name__}: {elapsed_time:.3f} seconds\n')
        return function_output, elapsed_time
    return wrapper
   
@log
def tokenize_query_to_tensor(query:str):
    '''
    STEP 1: Tokenize the query using the tokenizer.
    @param query: The query (type<str>) to be tokenized.
    @return: The tokenized query as a torch.Tensor.
    '''
    return TOKENIZER(query, return_tensors="pt").to(DEVICE).input_ids
    
@log
def generate_new_tensor(input_ids:torch.Tensor, MAX_NEW_TOKENS:int=5) -> torch.Tensor:
    '''
    STEP 2: Translate the input_ids tensor to an output query.
    @param input_ids: The decoded tensor (type<torch.Tensor>) to be passed through the model.
    @return: Newly generated tensor using the model (type<torch.Tensor>).
    '''
    return MODEL.generate(input_ids, max_new_tokens=MAX_NEW_TOKENS)
    
@log
def decode_generated_tensor(translated_tensor:torch.Tensor) -> str:
    '''
    STEP 3: Decode the translated tensor to a string.
    @param translated_tensor: <class 'torch.Tensor'>
    @return: <class 'str'>
    '''
    translated_result = TOKENIZER.decode(translated_tensor[0],\
        skip_special_tokens=True, \
        clean_up_tokenization_spaces=True \
    )
    return translated_result

@log
def translate_helsinki(segment:list) -> list:
    '''
    Translate the segment - (a list of strings) - using Helsinki-NLP models.
    Steps:
    @param segment: The segment (type<list>) to be translated.
    1. Tokenize the segment to a tensor.
    2. Pass tokenized tensor through the model.
    3. Decode the translated tensor to a string.
    4. Append the translated string to a list.
    '''
    result = []
    for input_query in segment:
        # 1. Input query -> tensor
        print(f'(1) Translating: {input_query}')
        input_tensor, _ = tokenize_query_to_tensor(input_query)
        
        # 2. Input tensor -> output tensor
        print(f'(2) Generating new tensor.')
        if len(input_query) < 3:
            MAX_NEW_TOKENS = 3
        else:
            MAX_NEW_TOKENS = len(input_query)
        output_tensor, _ = generate_new_tensor(input_tensor, MAX_NEW_TOKENS=MAX_NEW_TOKENS)
        
        # 3. Output tensor -> query
        print(f'(3) Decoding translated tensor.')
        output_query, _ = decode_generated_tensor(output_tensor)
        
        # 4. Translated query -> result
        print(f'(4) Appending {output_query} to result.')
        result.append(output_query)
    
    return result
