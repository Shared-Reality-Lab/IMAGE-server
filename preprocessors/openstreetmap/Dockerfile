#did not test this change!
FROM python:3.11-alpine3.20

RUN adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY ./preprocessors/openstreetmap/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt

COPY ./schemas /app/schemas
COPY /config /app/config
COPY ./preprocessors/openstreetmap/ /app

EXPOSE 5000

ENV FLASK_APP=main.py
USER python
CMD [ "gunicorn", "main:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
