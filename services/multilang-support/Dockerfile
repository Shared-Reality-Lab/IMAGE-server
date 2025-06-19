ARG PYTORCH="2.7.1"
ARG CUDA="11.8"
ARG CUDNN="9"
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-runtime

# See README.md#docker-image for visualisation of the directory structure
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip git git-lfs curl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements 
COPY services/multilang-support/requirements.txt /app/

# Upgrade pip and install requirements
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt 

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
