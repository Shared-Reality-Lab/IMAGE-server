ARG PYTORCH="2.5.1"
ARG CUDA="12.4"
ARG CUDNN="9"
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-runtime

#system dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git curl && rm -rf /var/lib/apt/lists/*

#user/environment setup
RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}:./AdelaiDepth/LeReS/Minist_Test/"
ENV FLASK_APP=depth-map-generator.py
ENV TORCH_HOME=/app

#python dependencies
COPY /preprocessors/depth-map-gen/requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r /app/requirements.txt

#schema
COPY /schemas /app/schemas
#config for pii
COPY /config /app/config
COPY /utils /app/utils

#model download, app code
RUN git clone https://github.com/aim-uofa/AdelaiDepth && \
    wget -O ./res101.pth https://huggingface.co/ffranchina/LeReS/resolve/main/res101.pth
COPY /preprocessors/depth-map-gen/ /app

EXPOSE 5000
USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "depth-map-generator:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
