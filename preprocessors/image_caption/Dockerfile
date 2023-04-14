FROM python:3.7


RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"

ENV REPLICATE_API_TOKEN=


# COPY /preprocessors/image_caption/requirements.txt /app/requirements.txt
# COPY ./requirements.txt /app/requirements.txt
COPY ./ /app
RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt


# COPY /schemas /app/schemas
# COPY /preprocessors/image_caption/ /app


#RUN wget https://image.a11y.mcgill.ca/models/semanticSegmentation/decoder_epoch_20.pth
#RUN wget https://image.a11y.mcgill.ca/models/semanticSegmentation/encoder_epoch_20.pth

EXPOSE 5000
ENV FLASK_APP=caption_api.py
USER python
CMD [ "gunicorn", "caption_api:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
