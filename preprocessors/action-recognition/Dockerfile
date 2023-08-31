ARG PYTORCH="2.0.1"
ARG CUDA="11.7"
ARG CUDNN="8"
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-runtime

ENV PYTHONUNBUFFERED=TRUE
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python

WORKDIR /app

ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --no-cache-dir --upgrade pip
COPY --chown=python:python /preprocessors/action-recognition/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY --chown=python:python /schemas /app/schemas

COPY --chown=python:python /preprocessors/action-recognition /app

RUN wget https://image.a11y.mcgill.ca/models/action_recognition/model.pth

EXPOSE 5000
USER python
ENTRYPOINT [ "gunicorn", "action-recognition:app", "-b", "0.0.0.0:5000","--capture-output" ]
