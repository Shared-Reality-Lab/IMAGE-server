FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime

COPY /preprocessors/depth-map-gen/requirements.txt /app/requirements.txt

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv wget git && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"
ENV PYTHONPATH "${PYTHONPATH}:./AdelaiDepth/LeReS/Minist_Test/"

RUN git clone https://github.com/aim-uofa/AdelaiDepth
RUN wget -O ./res101.pth https://cloudstor.aarnet.edu.au/plus/s/lTIJF4vrvHCAI31/download
RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/depth-map-gen/ /app

EXPOSE 5000
ENV FLASK_APP=depth-map-generator.py
ENV TORCH_HOME=/app
USER python
CMD [ "gunicorn", "depth-map-generator:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
