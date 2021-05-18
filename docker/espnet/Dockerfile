FROM pytorch/pytorch:1.8.1-cuda11.1-cudnn8-runtime

RUN apt-get update && apt-get install -y libsndfile1 build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
RUN pip install espnet==0.9.7
RUN pip install parallel_wavegan==0.4.8
RUN pip install espnet_model_zoo
RUN pip install Flask

WORKDIR /run/tts
COPY predownload.py .
RUN python predownload.py

COPY *.py ./

ENV TORCH_DEVICE="cpu"
EXPOSE 80
