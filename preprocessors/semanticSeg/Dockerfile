FROM schemas:latest AS schemas
FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime

COPY ./requirements.txt /app/requirements.txt


RUN apt-get update && apt-get install -y python3-opencv && rm -rf /var/lib/apt/lists/*
RUN pip3 install --upgrade pip
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y git
RUN pip install -r /app/requirements.txt
RUN pip install gunicorn

COPY --from=schemas /schemas /app/schemas
WORKDIR /app
COPY . /app

RUN wget bach.cim.mcgill.ca/atp/models/semanticSegmentation/decoder_epoch_20.pth
RUN wget bach.cim.mcgill.ca/atp/models/semanticSegmentation/encoder_epoch_20.pth

EXPOSE 5000
ENV FLASK_APP=segment.py
CMD [ "gunicorn", "segment:app", "-b", "0.0.0.0:5000" ]
