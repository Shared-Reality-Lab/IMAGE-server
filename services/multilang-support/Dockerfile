FROM pytorch/pytorch:latest

# See README.md#docker-image for visualisation of the directory structure
WORKDIR /app

RUN apt-get update && apt-get install python3 python3-pip -y

# Copy requirements 
COPY services/multilang-support/requirements.txt /app/

# Upgrade pip and install requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY schemas/services/translation.schema.json /app/
COPY services/multilang-support/src/*.py /app/src/

EXPOSE 5000
ENV FLASK_APP=src/app.py
CMD [ "gunicorn", "src.translate:app", "-b", "0.0.0.0", "--log-level=debug"]