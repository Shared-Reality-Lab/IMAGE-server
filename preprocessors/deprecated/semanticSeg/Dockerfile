FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime


RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"


COPY /preprocessors/semanticSeg/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt


COPY /schemas /app/schemas
COPY /preprocessors/semanticSeg/ /app

RUN wget https://image.a11y.mcgill.ca/models/semanticSegmentation/decoder_epoch_20.pth
RUN wget https://image.a11y.mcgill.ca/models/semanticSegmentation/encoder_epoch_20.pth

EXPOSE 5000
ENV FLASK_APP=segment.py
USER python
CMD [ "gunicorn", "segment:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
