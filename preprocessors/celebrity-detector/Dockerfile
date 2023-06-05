FROM python:3.9-buster

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y python3-opencv wget && rm -rf /var/lib/apt/lists/*

COPY /preprocessors/celebrity-detector/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY /schemas /app/schemas
WORKDIR /app
COPY /preprocessors/celeb-detector /app


EXPOSE 5000
ENV FLASK_APP=celeb.py
USER python
CMD [ "gunicorn", "celebrity-detector:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
