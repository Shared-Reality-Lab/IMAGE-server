FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv gcc wget git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/ner/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/ner/ /app

EXPOSE 5000
ENV FLASK_APP=ner.py

USER python
CMD [ "gunicorn", "ner:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]

