FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/object-detection-llm/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip && \
    pip3 install --root-user-action=ignore -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /config /app/config
COPY /utils /app/utils
COPY /preprocessors/object-detection-llm/ /app

EXPOSE 5000
USER python
ENV FLASK_APP=object-detection-llm.py

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "object-detection-llm:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]