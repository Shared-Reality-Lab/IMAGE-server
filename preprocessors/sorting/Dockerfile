#will come back to this and object detection
FROM python:3.8-alpine

RUN apk add --no-cache curl && \
    adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/sorting/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/sorting/ /app

EXPOSE 5000

ENV FLASK_APP=sorting.py
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "sorting:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
