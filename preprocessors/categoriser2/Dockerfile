FROM python:3.9-alpine

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/categoriser2/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY /schemas /app/schemas
WORKDIR /app
COPY /preprocessors/categoriser2 /app


EXPOSE 5000
ENV FLASK_APP=azure_api.py
USER python
CMD [ "gunicorn", "azure_api:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
