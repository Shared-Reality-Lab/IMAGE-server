FROM python:3.8-alpine

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip
RUN apk add --no-cache curl

COPY /preprocessors/grouping/requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/grouping/ /app

COPY /preprocessors/grouping/healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

EXPOSE 5000

ENV FLASK_APP=grouping.py
USER python

# Healthcheck: Run the healthcheck.sh script every 30 seconds
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD /app/healthcheck.sh 

CMD [ "gunicorn", "grouping:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
