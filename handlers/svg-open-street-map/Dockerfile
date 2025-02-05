FROM python:3.11

RUN apt-get install libcairo2

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /handlers/svg-open-street-map/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /usr/src/app/schemas
COPY /config /app/config
COPY /handlers/svg-open-street-map/ /usr/src/app

EXPOSE 5000
USER python
CMD ["gunicorn", "osm-svg:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]