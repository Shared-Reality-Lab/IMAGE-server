FROM pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime

RUN apt-get update && apt-get install -y libsndfile1 espeak-ng build-essential curl && rm -rf /var/lib/apt/lists/*


## phonemizedf
WORKDIR /run/tts
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*
RUN adduser --disabled-password python
RUN chown python:python .
USER python
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip

COPY /services/espnet-tts-fr/requirements.txt .
# COPY /services/espnet-tts/requirements.txt .
RUN pip install -r requirements.txt


# COPY /services/espnet-tts/src/predownload.py .
# COPY ./src/predownload.py .
# RUN python predownload.py


RUN mkdir -p /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2
RUN wget https://image.a11y.mcgill.ca/models/espnet/train_nodev_ljspeech_full_band_melgan.v2.tar.gz -O /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2.tar.gz

RUN tar xzvf /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2.tar.gz -C /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2/

RUN mkdir -p /home/python/.cache/models


RUN wget https://image.a11y.mcgill.ca/resources/models/espnet/siwis-tacotron-300epoch.pth -O /home/python/.cache/models/siwis-tacotron-300epoch.pth

RUN mkdir -p /home/python/.cache/conf

COPY /services/espnet-tts-fr/conf/* /home/python/.cache/conf/

COPY /services/espnet-tts-fr/conf/model-conf/config.yaml /home/python/.cache/models/

COPY /services/espnet-tts-fr/src/* ./
COPY /schemas/services/tts/* ./

COPY /services/espnet-tts-fr/conf/model-conf/feats_stats.npz ./

ENV TORCH_DEVICE="cpu"
EXPOSE 80

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug"]

