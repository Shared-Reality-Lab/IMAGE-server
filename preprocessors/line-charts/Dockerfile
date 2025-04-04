FROM python:3.11-alpine3.20

RUN apk add --no-cache curl && \
    adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"
ENV FLASK_APP=charts.py

COPY /preprocessors/line-charts/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /config /app/config
COPY /preprocessors/line-charts/ /app

EXPOSE 5000
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "charts:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
