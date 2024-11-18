FROM python:alpine3.20

COPY /preprocessors/graphic-caption/requirements.txt /app/requirements.txt

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/graphic-caption/ /app

EXPOSE 5000
ENV FLASK_APP=caption.py
USER python
CMD [ "gunicorn", "caption:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
