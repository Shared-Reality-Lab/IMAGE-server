FROM python:3.10

RUN apt-get install libcairo2 curl

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /handlers/svg-depth-map/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /usr/src/app/schemas
COPY /config /usr/src/app/config
COPY /handlers/svg-depth-map/ /usr/src/app

EXPOSE 80
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD ["gunicorn", "svg-depth-map:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug" ]
