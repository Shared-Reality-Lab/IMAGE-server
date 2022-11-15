FROM ubuntu:20.04

ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/

RUN apt-get update -y \
        && apt-get install -y software-properties-common \
        && add-apt-repository ppa:deadsnakes/ppa \
        && apt-get install openjdk-8-jdk -y \
        && apt-get install python3-pip -y \
        && export JAVA_HOME \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/* \
        && apt install python3-pip

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /schemas /app/schemas
COPY /preprocessors/ner/ /app

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv gcc wget git && rm -rf /var/lib/apt/lists/*

RUN pip3 install -r requirements.txt

EXPOSE 5000
ENV FLASK_APP=ner.py

USER python
CMD [ "gunicorn", "ner:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
