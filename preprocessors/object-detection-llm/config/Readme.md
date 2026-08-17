# OPTIONAL Preprocessor Config

If a specific preprocessor needs to use a different LLM endpoint or model than the global default at `config/llm.env` (e.g. running a smaller model for a specific preprocessor), create an override file at:
preprocessors/<preprocessor-name>/config/<preprocessor-name>.env

Set the following fields in the `.env` file:
LLM_API_KEY = [INSERT KEY STRING]
LLM_URL = [INSERT OPENAI-COMPATIBLE ENDPOINT URL]
LLM_MODEL = [INSERT MODEL NAME]

*Note:* This file is optional. If it doesn't exist, the preprocessor falls back to the global `config/llm.env`. If it does exist, any variable set in it takes priority over the global config for that preprocessor only.

**Important:** if you override any one of `LLM_API_KEY`, `LLM_URL`, or 
`LLM_MODEL`, you must set **all three** in the override file. These three variables are tied to a single endpoint. Partially overriding (e.g. only changing `LLM_URL` but leaving the global `LLM_API_KEY`) will send the wrong credentials to the new endpoint and fail authentication.