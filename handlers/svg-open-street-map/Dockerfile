FROM python:3.11

RUN apt-get install libcairo2 curl

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /handlers/svg-open-street-map/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /usr/src/app/schemas
COPY /config /usr/src/app/config
COPY /handlers/svg-open-street-map/ /usr/src/app

EXPOSE 5000
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD ["gunicorn", "osm-svg:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]