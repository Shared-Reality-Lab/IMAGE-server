# Build with --build-arg DEVICE=cuda for a GPU-enabled image (e.g. pegasus/production),
# or --build-arg DEVICE=cpu for a CPU-only image with no CUDA runtime (e.g. unicorn/test).
# Defaults to cuda to match the original production image if DEVICE is not specified.
ARG DEVICE=cuda
ARG PYTORCH="2.7.1"
ARG CUDA="12.8"
ARG CUDNN="9"

FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-runtime AS base-cuda
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip git git-lfs curl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

FROM python:3.11-slim AS base-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs curl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

FROM base-${DEVICE} AS base

# See README.md#docker-image for visualisation of the directory structure
WORKDIR /app

# Install Python dependencies. The cuda base image already ships a CUDA-matched
# torch build; the cpu base image needs the CPU-only wheel installed explicitly.
ARG DEVICE
COPY services/multilang-support/requirements.txt /app/
RUN pip install --upgrade pip \
 && if [ "$DEVICE" = "cpu" ]; then \
      pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
    else \
      pip install --no-cache-dir "torch>=2.6.0"; \
    fi \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir "transformers[sentencepiece]"

# download english -> french model into the image
RUN python3 -c "\
from transformers import MarianMTModel, MarianTokenizer; \
model = MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-en-fr'); \
tokenizer = MarianTokenizer.from_pretrained('Helsinki-NLP/opus-mt-en-fr'); \
model.save_pretrained('/app/models/opus-mt-en-fr'); \
tokenizer.save_pretrained('/app/models/opus-mt-en-fr')"

# Clone the model
# RUN git lfs install

# English -> French
# RUN git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-fr ./models/opus-mt-en-fr

# English -> German
# RUN git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-de ./models/opus-mt-en-de

# English -> Spanish
# RUN git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-es ./models/opus-mt-en-es

COPY schemas/services/translation.schema.json /app/
COPY services/multilang-support/src/*.py /app/src/

EXPOSE 80
ENV FLASK_APP=src/app.py

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD [ "gunicorn", "src.translate:app", "--bind", "0.0.0.0:80", "--log-level=info", "--timeout=120"]
