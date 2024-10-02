FROM python:3.10

COPY /preprocessors/object-depth-calculator/requirements.txt /app/requirements.txt

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3-opencv wget git curl && \
    rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/object-depth-calculator/ /app

EXPOSE 5000
ENV FLASK_APP=object-depth-calculator.py
ENV TORCH_HOME=/app
USER python
CMD [ "gunicorn", "object-depth-calculator:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
