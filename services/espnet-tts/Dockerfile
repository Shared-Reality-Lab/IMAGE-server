FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime

RUN apt-get update && apt-get install -y libsndfile1 build-essential wget curl && rm -rf /var/lib/apt/lists/*

WORKDIR /run/tts
RUN adduser --disabled-password python && chown python:python .
USER python
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /services/espnet-tts/requirements.txt .
RUN pip install -r requirements.txt

COPY /services/espnet-tts/src/predownload.py .
RUN python predownload.py && \
    mkdir -p /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2 && \
    wget https://image.a11y.mcgill.ca/models/espnet/train_nodev_ljspeech_full_band_melgan.v2.tar.gz -O /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2.tar.gz && \
    tar xzvf /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2.tar.gz -C /home/python/.cache/parallel_wavegan/ljspeech_full_band_melgan.v2/

COPY /services/espnet-tts/src/* ./
COPY /schemas/services/tts/* ./
ENV TORCH_DEVICE="cpu"
EXPOSE 80

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug"]
