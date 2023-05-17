FROM python:3-slim

# Set working directory for the container
WORKDIR /usr/src/app

COPY services/multilang-support/requirements.txt ./
RUN apt-get update && apt-get install python3 python3-pip -y
RUN pip3 install --upgrade pip
RUN pip install -r requirements.txt

COPY schemas ./schemas_image
COPY services/multilang-support/app.py ./

EXPOSE 5000
ENV FLASK_APP=app.py
CMD [ "python3", "app.py" ]