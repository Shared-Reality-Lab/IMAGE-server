FROM python:3.11-alpine3.20

RUN apk add supercronic curl

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /services/monarch-link-app/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /services/monarch-link-app/ /usr/src/app

RUN chown -R python:python /usr/src/app

EXPOSE 80
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD supercronic -quiet /usr/src/app/cronjob \
    & gunicorn app:app -b 0.0.0.0:80 --capture-output --log-level=debug