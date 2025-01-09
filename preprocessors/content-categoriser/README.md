Beta quality: Useful enough for testing by end-users.

This preprocessor classifies whether the input image is a photograph, chart, text, or other.
Currently, the IMAGE reference server is <a href="https://www.llama.com/">Built with Llama</a> (and is subject to their <a href="https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/USE_POLICY.md">Acceptable Use Policy</a> and <a href="https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE">License</a>), but any other ollama-compatible model can be chosen.
It uses an LLM model running via ollama fronted by open-webui.
There are several mandatory environment variables you must set.
Example ollama.env file:

```
OLLAMA_URL=https://ollama.myserver.com/ollama/api/generate
OLLAMA_API_KEY=sk-[YOUR_OLLAMA_SECRET KEY]
OLLAMA_MODEL=llava:latest
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



# Deprecated self-trained categoriser
An earlier version of this preprocessor used a self-trained model, but the accuracy was limited compared to current LLM technology.
For reference, the documentation is being preserved since this earlier version can be used by going back in git history.

The preprocessor is trained from scratch using transfer learning. The following datasets were used in training our preprocessor
## Datasets used 


| Dataset Name  | Link | Distribution License |
| ------------- | ------------- | -------------|
| COCO  | [Link](https://cocodataset.org/#termsofuse)  | Creative Commons Attribution 4.0 License.|
| Cartoon Dataset  | [Link](https://google.github.io/cartoonset/download.html)  | Creative Commons Attribution 4.0 International License |
| Comics Dataset  | [Link]( https://www.kaggle.com/cenkbircanoglu/comic-books-classification)  | Open Data Commons |
| Sketches Dataset  | Sangkloy, Patsorn, et al. "The sketchy database: learning to retrieve badly drawn bunnies." ACM Transactions on Graphics (TOG) 35.4 (2016): 1-12.  | - |
| Sketches Dataset  | [Link](http://mmlab.ie.cuhk.edu.hk/archive/cufsf/#Downloads)  | - |
| Sketches Dataset  | [Link](http://cybertron.cg.tu-berlin.de/eitz/projects/classifysketch/)  | Creative Commons Attribution 4.0 International License |
| Sketches Dataset  | [Link]( https://www.kaggle.com/wanghaohan/imagenetsketch)  | Open Data Commons |
| Tom and Jerry Dataset  | [Link](https://www.kaggle.com/vijayjoyz/tom-jerry-detection)  | Open Data Commons |
| Anime Dataset  | [Link](https://www.kaggle.com/splcher/animefacedataset)  | Open data Commons |
| Places365 Dataset  | [Link](http://places2.csail.mit.edu/download.html)  | - |
| ADE20K  | [Link](https://groups.csail.mit.edu/vision/datasets/ADE20K/terms/)  | BSD3 |
| ImageNet  | [Link]( https://www.kaggle.com/c/imagenet-object-localization-challenge/overview/description)  | Open data Commons |
| Chart Dataset  | [Link](https://github.com/soap117/DeepRule)  | BSD3 |
| Text Dataset  | [Link](https://github.com/doc-analysis/DocBank)  | Apache-2.0 |

The following libraries were used for creating this preprocessor

## Libraries Used

| Library | Link | Distribution License |
| ------------- | ------------- | -------------|
| Requests  | [Link](https://pypi.org/project/requests/)  | Apache 2.0|
| Flask | [Link](https://pypi.org/project/Flask/)  | BSD-3-Clause License|
| Numpy | [Link](https://pypi.org/project/numpy/)  | BSD-3-Clause License|
| Pillow | [Link](https://pypi.org/project/Pillow/)  | Historical Permission Notice and Disclaimer (HPND)|
| Jsonschema | [Link](https://pypi.org/project/jsonschema/)  | MIT License|
| Werkzeug | [Link](https://pypi.org/project/Werkzeug/) | BSD-3 |
| Pytorch Lightning | [Link](https://pypi.org/project/Werkzeug/) | Apache Software License (Apache-2.0) |
| opencv-python | [Link](https://github.com/skvark/opencv-python) | MIT License(MIT) |
| Gunicorn | [Link](https://github.com/benoitc/gunicorn) | MIT License(MIT) |

The versions for each of these libraries has been mentioned in the requirements.txt
