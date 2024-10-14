FROM python:3.9.5-alpine

# Install curl as root
RUN apk add --no-cache curl && \
    adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY --chown=python:python /preprocessors/autour/requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY --chown=python:python /schemas /app/schemas
COPY --chown=python:python /preprocessors/autour/ /app

EXPOSE 5000

ENV FLASK_APP=autour.py
USER python
CMD [ "gunicorn", "autour:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
