FROM python:3.11-alpine3.20

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"
ENV FLASK_APP=azure_api.py

COPY /preprocessors/graphic-tagger/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/graphic-tagger /app

EXPOSE 5000
USER python
CMD [ "gunicorn", "azure_api:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
