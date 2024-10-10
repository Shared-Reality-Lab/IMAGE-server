FROM python:3.8-alpine

# Install curl as root
RUN apk add --no-cache curl && \
    adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY /preprocessors/grouping/requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/grouping/ /app

EXPOSE 5000

ENV FLASK_APP=grouping.py
USER python
CMD [ "gunicorn", "grouping:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
