FROM pytorch/pytorch:1.8.1-cuda11.1-cudnn8-runtime

RUN apt-get update && apt-get install -y libsndfile1 build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
RUN pip install espnet==0.9.7
RUN pip install parallel_wavegan==0.4.8
RUN pip install espnet_model_zoo

WORKDIR /run/tts
COPY tts.py .
