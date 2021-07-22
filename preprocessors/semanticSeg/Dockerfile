FROM schemas:latest AS schemas
FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime

COPY ./requirements.txt /app/requirements.txt


RUN apt-get update && apt-get install -y python3-opencv && rm -rf /var/lib/apt/lists/*
RUN pip3 install --upgrade pip
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y git
RUN pip install -r requirements.txt

COPY --from=schemas /schemas /app/schemas
WORKDIR /app
COPY . /app

RUN wget bach.cim.mcgill.ca/atp/models/semanticSegmentation/decoder_epoch_20.pth
RUN wget bach.cim.mcgill.ca/atp/models/semanticSegmentation/encoder_epoch_20.pth
RUN mv decoder_epoch_20.pth /app
RUN mv encoder_epoch_20.pth /app

EXPOSE 5000
ENV FLASK_APP=segment.py
CMD [ "flask", "run", "--host=0.0.0.0" ]
