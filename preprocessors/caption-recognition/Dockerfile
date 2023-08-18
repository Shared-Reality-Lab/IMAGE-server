FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git gcc mono-mcs && rm -rf /var/lib/apt/lists/*

COPY /preprocessors/caption-recognition/huggingface /home/python/.cache/huggingface/
RUN wget https://storage.googleapis.com/sfr-vision-language-research/LAVIS/models/BLIP/blip_coco_caption_base.pth -P /home/python/.cache/torch/hub/checkpoints
WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /preprocessors/caption-recognition/requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt


COPY /schemas /app/schemas
COPY /preprocessors/caption-recognition/ /app


EXPOSE 5000
ENV FLASK_APP=caption.py
USER python
CMD [ "gunicorn", "caption:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
