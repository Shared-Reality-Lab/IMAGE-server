FROM python:3.11-alpine3.20

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/autour/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/autour/ /app

EXPOSE 5000

ENV FLASK_APP=autour.py
USER python
CMD [ "gunicorn", "autour:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
