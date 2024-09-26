FROM python:3.8-alpine

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

# Install curl
RUN apk add --no-cache curl

COPY /preprocessors/grouping/requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas

COPY /preprocessors/grouping/ /app

EXPOSE 5000


ENV FLASK_APP=grouping.py
USER python

# -- Healthchecks --

#1. Docker checks the health of the container every 30 seconds. 
#It waits up to 10 seconds for the curl command to complete, and if the check fails, it will retry 3 times before marking as unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "grouping:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]

