#will come back to this and sorting
FROM python:3.9-alpine

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/object-detection-azure/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/object-detection-azure /app

EXPOSE 5000
ENV FLASK_APP=objdetect.py
USER python
CMD [ "gunicorn", "objdetect:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
