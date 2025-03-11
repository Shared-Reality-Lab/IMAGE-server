FROM ultralytics/ultralytics:latest@sha256:af4572bf0df164d5708e4a1f50bddb5a74cb7d793fe46b7daf42b1768fbec608

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
COPY /config /app/config

RUN wget https://image.a11y.mcgill.ca/models/objectDetectionWeights/yolov8x.pt

COPY /preprocessors/yolov8 /usr/src/app 

EXPOSE 5000

ENV FLASK_APP=detect.py 

USER python

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "gunicorn", "detect:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]