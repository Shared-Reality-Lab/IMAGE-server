Beta quality: Useful enough for testing by end-users.

This preprocessor generates a text-only response
to a followup query that contains the original graphic
and a question posed by the user.
A brief and a full response are included, and together
form the full response.

The preprocessor keeps the memory of the conversation
allowing users to ask follow-up questions about the original graphic.
The period of history storage is defined by
the `HISTORY_EXPIRY` environment variable (default is 1 hour).

The `MAX_HISTORY_LENGTH` environment variable defines how many 
messages will be passed to the model for context 
(including system message, user requests, and LLM responses).

>Example: if `MAX_HISTORY_LENGTH=100` and there are 120 interactions 
>in the history, the model will receive the system message, 
>the first user message (with graphic), and the most recent 98 interactions 
>between the user and the model.


It uses an LLM model running via ollama fronted by open-webui.
There are several mandatory environment variables you must set.
Example ollama.env file:

```
OLLAMA_URL=https://ollama.myserver.com/ollama/api
OLLAMA_API_KEY=sk-[YOUR_OLLAMA_SECRET KEY]
OLLAMA_MODEL=llama3.2-vision:latest
```
Note these are not unique to this preprocessor. Due to
GPU memory limitations, we assume that all preprocessors
will use the same ollama model, to prevent them swapping
in and out of memory.

Logging personal information should only be done on test
servers. The environment variable LOG_PII can be set
to allow this information to be logged.
In addition, you can override the prompt used by
the LLM. Example:

```
  text-followup:
    ...
    environment:
      LOG_PII: "true"
      TEXT_FOLLOWUP_PROMPT_OVERRIDE: |-
              The prompt I really want to use is...
              Here is my request:
              [user followup query will be added here]
```

## Libraries Used

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Requests  | [Link](https://pypi.org/project/requests/)  | Apache 2.0|
| Flask | [Link](https://pypi.org/project/Flask/)  | BSD-3-Clause License|
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License|
| Werkzeug | [Link](https://pypi.org/project/Werkzeug/) | BSD-3 |
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |

The versions for each of these libraries is specified `requirements.txt`
