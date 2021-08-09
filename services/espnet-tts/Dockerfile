FROM schemas:latest AS schemas

FROM pytorch/pytorch:1.8.1-cuda11.1-cudnn8-runtime

RUN apt-get update && apt-get install -y libsndfile1 build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
RUN pip install espnet==0.10.0
RUN pip install parallel_wavegan==0.4.8
RUN pip install espnet_model_zoo
RUN pip install Flask gunicorn
RUN pip install jsonschema

WORKDIR /run/tts
COPY src/predownload.py .
RUN python predownload.py

COPY src/* ./
COPY --from=schemas /schemas/services/tts/* ./
ENV TORCH_DEVICE="cpu"
EXPOSE 80

COPY src/entrypoint .
RUN chmod +x entrypoint
ENTRYPOINT ["/run/tts/entrypoint"]
