ARG PYTORCH="2.5.1"
ARG CUDA="12.4"
ARG CUDNN="9"
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-runtime

ENV DEBIAN_FRONTEND=noninteractive

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

#install system dependencies in one layer
RUN apt-get update && \
    apt-get install -y \
    python3-opencv wget build-essential \
    libfreetype6-dev libpng-dev libharfbuzz-dev \
    libcairo2-dev python3-dev p7zip p7zip-full \
    unace zip unzip && \
    apt-get -y autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY /preprocessors/clothes-detector/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt
# COPY ./requirements.txt /app/requirements.txt

COPY /schemas /app/schemas
# COPY ./schemas /app/schemas

# good practice to remove the archive 
RUN wget https://image.a11y.mcgill.ca/models/clothesDetector/yolo.zip && \
    unzip yolo.zip && \
    rm yolo.zip 

COPY /preprocessors/clothes-detector /app
# COPY ./ /app

EXPOSE 5000
ENV FLASK_APP=clothes.py
USER python
CMD [ "gunicorn", "clothes:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
