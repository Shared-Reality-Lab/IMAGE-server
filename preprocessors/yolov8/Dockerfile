FROM ultralytics/ultralytics@sha256:3d52e286bc345343b1a7a66dd38c44bb412bf418eb97d14298b8d8deb077f2e4

WORKDIR /usr/src/app
RUN adduser --disabled-password python 
ENV PATH="/usr/src/app/.local/bin:${PATH}"

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    wget curl && \
    rm -rf /var/lib/apt/lists/*

COPY /preprocessors/yolov8/requirements.txt /usr/src/app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r /usr/src/app/requirements.txt

COPY /schemas /usr/src/app/schemas
COPY /config /usr/src/app/config

# Create model directory
RUN mkdir -p /usr/src/app/models

# Download YOLOv11 model
RUN wget -O /usr/src/app/models/yolo11x.pt https://image.a11y.mcgill.ca/models/objectDetectionWeights/yolo11x.pt

COPY /preprocessors/yolov8 /usr/src/app 

EXPOSE 5000

ENV FLASK_APP=detect.py 

USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "detect:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]