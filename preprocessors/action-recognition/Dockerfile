ARG PYTORCH="2.5.1"
ARG CUDA="12.4"
ARG CUDNN="9"
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-runtime

ENV PYTHONUNBUFFERED=TRUE
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends wget -y && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password python

WORKDIR /app

RUN wget https://image.a11y.mcgill.ca/models/action_recognition/model.pth

ENV PATH="/home/python/.local/bin:${PATH}"

COPY --chown=python:python /preprocessors/action-recognition/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r /app/requirements.txt

COPY --chown=python:python /schemas /app/schemas
COPY --chown=python:python /config /app/config
COPY --chown=python:python /preprocessors/action-recognition /app

EXPOSE 5000
USER python
ENTRYPOINT [ "gunicorn", "action-recognition:app", "-b", "0.0.0.0:5000","--capture-output" ]