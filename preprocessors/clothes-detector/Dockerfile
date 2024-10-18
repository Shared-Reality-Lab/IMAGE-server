FROM pytorch/pytorch:2.4.1-cuda11.8-cudnn9-runtime

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

#install system dependencies
RUN apt-get update && \
    apt-get install -y python3-opencv wget && \
    apt-get install -y build-essential libfreetype6-dev libpng-dev libharfbuzz-dev libcairo2-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY /preprocessors/clothes-detector/requirements.txt /app/requirements.txt
# COPY ./requirements.txt /app/requirements.txt

RUN  apt-get update -y && \
     apt-get upgrade -y && \
     apt-get dist-upgrade -y && \
     apt-get -y autoremove && \
     apt-get clean
RUN apt-get install -y p7zip p7zip-full unace zip unzip

RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt

RUN wget https://image.a11y.mcgill.ca/models/clothesDetector/yolo.zip && \
    unzip yolo.zip

COPY /schemas /app/schemas
# COPY ./schemas /app/schemas
COPY /preprocessors/clothes-detector /app
# COPY ./ /app


EXPOSE 5000
ENV FLASK_APP=clothes.py
USER python
CMD [ "gunicorn", "clothes:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
