#FROM pytorch/pytorch:1.13.0-cuda11.6-cudnn8-runtime
FROM python:alpine3.20

COPY /preprocessors/content-categoriser/requirements.txt /app/requirements.txt

#RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/content-categoriser/ /app

EXPOSE 5000
ENV FLASK_APP=categoriser.py
#ENV TORCH_HOME=/app
USER python
CMD [ "gunicorn", "categoriser:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
