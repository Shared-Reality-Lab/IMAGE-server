Beta quality: Useful enough for testing by end-users.

This preprocessor generates a brief caption for the graphic.
It uses an LLM model running via ollama fronted by open-webui.
There are several mandatory environment variables you must set.
Example ollama.env file:

```
OLLAMA_URL=https://ollama.myserver.com/ollama/api/generate
OLLAMA_API_KEY=sk-[YOUR_OLLAMA_SECRET KEY]
OLLAMA_MODEL=llava:latest
```
Note these are not unique to this preprocessor. Due to
GPU memory limitations, we assume that all preprocessors
will use the same ollama model, to prevent them swapping
in and out of memory.

## Libraries Used

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Requests  | [Link](https://pypi.org/project/requests/)  | Apache 2.0|
| Flask | [Link](https://pypi.org/project/Flask/)  | BSD-3-Clause License|
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License|
| Werkzeug | [Link](https://pypi.org/project/Werkzeug/) | BSD-3 |
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |

The versions for each of these libraries is specified `requirements.txt`