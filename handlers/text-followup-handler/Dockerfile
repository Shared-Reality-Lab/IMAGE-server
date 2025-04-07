FROM python:3.13

RUN apt-get update && apt-get install -y libcairo2 curl

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /handlers/text-followup-handler/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /usr/src/app/schemas
COPY /config /usr/src/app/config
COPY /handlers/text-followup-handler/ /usr/src/app

EXPOSE 80
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD ["gunicorn", "followup:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug" ]
