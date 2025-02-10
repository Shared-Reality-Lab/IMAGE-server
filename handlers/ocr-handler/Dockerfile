FROM python:3.9.5-alpine

RUN apk add --no-cache curl && adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY /handlers/ocr-handler/requirements.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas
COPY /config /app/config
COPY /handlers/ocr-handler/ /app

EXPOSE 80

ENV FLASK_APP=server.py
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD [ "gunicorn", "server:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug" ]
