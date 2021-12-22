FROM schemas:latest AS schemas
FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime


RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"


COPY ./requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt


COPY --from=schemas /schemas /app/schemas
COPY . /app

RUN wget bach.cim.mcgill.ca/atp/models/semanticSegmentation/decoder_epoch_20.pth
RUN wget bach.cim.mcgill.ca/atp/models/semanticSegmentation/encoder_epoch_20.pth

EXPOSE 5000
ENV FLASK_APP=segment.py
USER python
CMD [ "gunicorn", "segment:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
