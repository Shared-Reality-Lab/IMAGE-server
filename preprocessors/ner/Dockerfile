FROM ubuntu:20.04

ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    openjdk-8-jdk \
    python3-pip \
    gcc \
    git \
    curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/ner/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /config /app/config
COPY /preprocessors/ner/ /app

EXPOSE 5000
ENV FLASK_APP=ner.py

USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "ner:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
