FROM python:3.11-slim

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git curl && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app

COPY /preprocessors/object-depth-calculator/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /config /app/config
COPY /preprocessors/object-depth-calculator/ /app

EXPOSE 5000
ENV FLASK_APP=object-depth-calculator.py
ENV TORCH_HOME=/app
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "object-depth-calculator:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
