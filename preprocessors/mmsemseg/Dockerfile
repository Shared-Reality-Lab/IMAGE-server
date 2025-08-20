# Dockerfile partially and adapted from the official MMsegmentation Dockerfile at https://github.com/open-mmlab/mmsegmentation/blob/master/docker/serve/Dockerfile
ARG PYTORCH="1.11.0"
ARG CUDA="11.3"
ARG CUDNN="8"
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-devel

ARG MMCV="1.5.0"
ARG MMSEG="0.30.0"

ENV PYTHONUNBUFFERED TRUE

# NVIDIA APT KEYS
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/3bf863cc.pub
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/7fa2af80.pub

# Install required packages as root
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    ca-certificates \
    g++ \
    openjdk-11-jre-headless \
    wget \
    # MMDet Requirements
    ffmpeg libsm6 libxext6 git ninja-build libglib2.0-0 libsm6 libxrender-dev libxext6 curl && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/conda/bin:$PATH"
RUN export FORCE_CUDA=1 

# MMLAB
ARG PYTORCH
ARG CUDA
RUN ["/bin/bash", "-c", "pip install mmcv-full==${MMCV} -f https://download.openmmlab.com/mmcv/dist/cu${CUDA//./}/torch${PYTORCH}/index.html"]
RUN pip install mmsegmentation==${MMSEG}

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/mmsemseg/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/mmsemseg/ /app
COPY /utils /app/utils
COPY /config /app/config

# Download the model checkpoint
RUN wget https://image.a11y.mcgill.ca/resources/models/mmsemseg/upernet_beit-base_8x2_640x640_160k_ade20k-eead221d.pth

EXPOSE 5000
ENV FLASK_APP=segment.py
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 \
  CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "segment:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
