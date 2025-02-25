#will come back to this and sorting
FROM python:3.9-alpine

RUN apk add --no-cache curl && \
    adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/object-detection-azure/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /config /app/config
COPY /preprocessors/object-detection-azure /app

EXPOSE 5000
ENV FLASK_APP=objdetect.py
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "objdetect:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
