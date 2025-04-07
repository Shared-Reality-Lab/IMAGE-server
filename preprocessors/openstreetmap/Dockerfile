FROM python:3.11-alpine3.20

RUN apk add --no-cache curl && \
    adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY ./preprocessors/openstreetmap/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt

COPY ./schemas /app/schemas
COPY ./preprocessors/openstreetmap/ /app
COPY ./config /app/config

EXPOSE 5000

ENV FLASK_APP=main.py
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "main:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
