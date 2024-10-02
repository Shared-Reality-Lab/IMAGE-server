FROM pytorch/pytorch:1.13.0-cuda11.6-cudnn8-runtime

COPY /preprocessors/depth-map-gen/requirements.txt /app/requirements.txt

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git curl && \
    rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"
ENV PYTHONPATH "${PYTHONPATH}:./AdelaiDepth/LeReS/Minist_Test/"

RUN git clone https://github.com/aim-uofa/AdelaiDepth
RUN wget -O ./res101.pth https://huggingface.co/ffranchina/LeReS/resolve/main/res101.pth
RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/depth-map-gen/ /app

EXPOSE 5000
ENV FLASK_APP=depth-map-generator.py
ENV TORCH_HOME=/app
USER python
CMD [ "gunicorn", "depth-map-generator:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
