FROM pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime

RUN apt-get update && apt-get install -y libsndfile1 build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /run/tts
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*
RUN adduser --disabled-password python
RUN chown python:python .
USER python
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY ./requirements.txt .
# COPY /services/espnet-tts/requirements.txt .
RUN pip install -r requirements.txt

# COPY /services/espnet-tts/src/predownload.py .
COPY ./src/predownload.py .
RUN python predownload.py
RUN mkdir -p /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2
RUN wget https://image.a11y.mcgill.ca/models/espnet/train_nodev_ljspeech_full_band_melgan.v2.tar.gz -O /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2.tar.gz

RUN tar xzvf /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2.tar.gz -C /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2/

RUN mkdir -p /home/python/.cache/models

RUN wget https://image.a11y.mcgill.ca/resources/models/espnet/siwis-tacotron-300epoch.pth -O /home/python/.cache/models/siwis-tacotron-300epoch.pth


# COPY /services/espnet-tts/src/* ./
COPY ./src/* ./
# COPY /schemas/services/tts/* ./

COPY ./segment.request.json ./
COPY ./segment.response.json ./

ENV TORCH_DEVICE="cpu"
EXPOSE 80

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug"]

