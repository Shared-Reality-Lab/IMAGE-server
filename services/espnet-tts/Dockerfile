FROM schemas:latest AS schemas

FROM pytorch/pytorch:1.8.1-cuda11.1-cudnn8-runtime

RUN apt-get update && apt-get install -y libsndfile1 build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /run/tts
RUN adduser --disabled-password python
RUN chown python:python .
USER python
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
RUN pip install espnet==0.10.0
RUN pip install parallel_wavegan==0.4.8
RUN pip install espnet_model_zoo
RUN pip install Flask gunicorn
RUN pip install jsonschema

COPY src/predownload.py .
RUN python predownload.py

COPY src/* ./
COPY --from=schemas /schemas/services/tts/* ./
ENV TORCH_DEVICE="cpu"
EXPOSE 80

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:80"]
