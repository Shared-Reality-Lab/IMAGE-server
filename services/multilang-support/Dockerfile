FROM pytorch/pytorch:latest

COPY services/multilang-support/requirements.txt ./
RUN apt-get update && apt-get install python3 python3-pip -y

# Upgrade pip and install requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY schemas/services/translation.schema.json ./
COPY services/multilang-support/src/* ./src

EXPOSE 5000
ENV FLASK_APP=src/app.py
CMD [ "gunicorn", "src.app:app" ]
