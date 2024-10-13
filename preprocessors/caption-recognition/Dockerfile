FROM pytorch/pytorch:1.13.0-cuda11.6-cudnn8-runtime

# Install required packages as root
RUN apt-get update && apt-get install -y python3-opencv wget git gcc mono-mcs curl && rm -rf /var/lib/apt/lists/*

# Setup environment
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"

# Download model
RUN wget https://storage.googleapis.com/sfr-vision-language-research/LAVIS/models/BLIP/blip_coco_caption_base.pth -P /home/python/.cache/torch/hub/checkpoints
WORKDIR /app

COPY --chown=python:python . $HOME/app
COPY --chown=python:python /preprocessors/caption-recognition/huggingface /home/python/.cache/huggingface/
COPY --chown=python:python /preprocessors/caption-recognition/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/caption-recognition/ /app
COPY --chown=python:python /preprocessors/caption-recognition/huggingface/hub /home/python/.cache/
RUN chmod 777 /home/python/.cache/huggingface/hub/models--bert-base-uncased/

EXPOSE 5000
ENV FLASK_APP=caption.py
USER python
CMD [ "gunicorn", "caption:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
