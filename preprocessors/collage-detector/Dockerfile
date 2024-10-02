FROM python:3

COPY /preprocessors/collage-detector/requirements.txt /app/requirements.txt

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    wget \
    curl \  # Add curl to the installation
    && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/collage-detector/ /app

EXPOSE 5000
ENV FLASK_APP=detect.py
USER python
CMD [ "gunicorn", "detect:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]