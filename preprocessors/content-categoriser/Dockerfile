FROM python:alpine3.20

COPY /preprocessors/content-categoriser/requirements.txt /app/requirements.txt

RUN apk add --no-cache python3-opencv wget curl

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/content-categoriser/ /app

EXPOSE 5000
ENV FLASK_APP=categoriser.py
USER python
CMD [ "gunicorn", "categoriser:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]