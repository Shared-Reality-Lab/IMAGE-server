# Resize Graphics Pseudo-Preprocessor

Alpha quality: not yet ready for use by end-users.

This pseudo-preprocessor will modify graphic requests in place to use a consistent size and format.
This allows other preprocessors to run more consistently.

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Flask | [Link](https://pypi.org/project/Flask/) | BSD-3-Clause License |
| requests | [Link](https://pypi.org/project/requests/) | Apache 2.0 |
| jsonschema | [Link](https://pypi.org/project/jsonschema/) | MIT License |
| gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License |
| pillow | [Link](https://pypi.org/project/Pillow/) | MIT-CMU |

The versions for each of these libraries are specified in `requirements.txt`

## API Endpoints

- `/preprocessor` (POST): Main endpoint for resizing
- `/health` (GET): Health check endpoint
