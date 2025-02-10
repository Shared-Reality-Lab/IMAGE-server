FROM python:3.11-slim

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y python3-opencv wget curl && rm -rf /var/lib/apt/lists/*

COPY /preprocessors/celebrity-detector/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /config /app/config
COPY /preprocessors/celebrity-detector /app

EXPOSE 5000
ENV FLASK_APP=celebrity-detector.py
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "celebrity-detector:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
