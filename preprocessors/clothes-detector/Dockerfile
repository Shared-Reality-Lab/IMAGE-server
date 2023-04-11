FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y python3-opencv wget && rm -rf /var/lib/apt/lists/*

COPY /preprocessors/clothes-detector/requirements.txt /app/requirements.txt
# COPY ./requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY /schemas /app/schemas
# COPY ./schemas /app/schemas
WORKDIR /app
COPY /preprocessors/clothes-detector /app
# COPY ./ /app


EXPOSE 5000
ENV FLASK_APP=clothes.py
USER python
CMD [ "gunicorn", "clothes:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
