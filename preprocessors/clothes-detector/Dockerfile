FROM pytorch/pytorch:1.13.1-cuda11.7-cudnn8-runtime 

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y python3-opencv wget && rm -rf /var/lib/apt/lists/*

COPY /preprocessors/clothes-detector/requirements.txt /app/requirements.txt
# COPY ./requirements.txt /app/requirements.txt

RUN  apt-get update -y && \
     apt-get upgrade -y && \
     apt-get dist-upgrade -y && \
     apt-get -y autoremove && \
     apt-get clean
RUN apt-get install -y p7zip \
    p7zip-full \
    unace \
    zip \
    unzip
RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt
RUN wget https://image.a11y.mcgill.ca/models/clothesDetector/yolo.zip
RUN unzip yolo.zip

COPY /schemas /app/schemas
# COPY ./schemas /app/schemas
WORKDIR /app
COPY /preprocessors/clothes-detector /app
# COPY ./ /app


EXPOSE 5000
ENV FLASK_APP=clothes.py
USER python
CMD [ "gunicorn", "clothes:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
