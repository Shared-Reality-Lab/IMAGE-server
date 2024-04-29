
Alpha quality: Insufficiently refined to be tested by end-users.

FROM python:3.9.5-alpine

RUN adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY ./preprocessors/openstreetmap/requirements.txt /app/requirements.txt


RUN pip3 install -r requirements.txt

COPY ./schemas /app/schemas

COPY ./preprocessors/openstreetmap/ /app

EXPOSE 5000

ENV FLASK_APP=main.py
USER python
CMD [ "gunicorn", "main:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]