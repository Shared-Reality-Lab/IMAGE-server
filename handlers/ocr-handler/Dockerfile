FROM python:3.9.5-alpine

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY /handlers/ocr-handler/requirements.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas

COPY /handlers/ocr-handler/ /app

EXPOSE 80

ENV FLASK_APP=server.py
USER python
CMD [ "gunicorn", "server:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug" ]
