FROM python:3.8-alpine

RUN adduser --disabled-password python && \
    apk add --no-cache curl && \
    pip3 install --upgrade pip

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"


COPY /preprocessors/grouping/requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/grouping/ /app

EXPOSE 5000

ENV FLASK_APP=grouping.py
USER python

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=1 \
  CMD curl -f http://localhost:5000/fake || exit 1
  
CMD [ "gunicorn", "grouping:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
