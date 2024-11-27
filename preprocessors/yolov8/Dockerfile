FROM ultralytics/ultralytics:latest@sha256:af4572bf0df164d5708e4a1f50bddb5a74cb7d793fe46b7daf42b1768fbec608

WORKDIR /usr/src/app
RUN adduser --disabled-password python #
ENV PATH="/usr/src/app/.local/bin:${PATH}"

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    wget && \
    rm -rf /var/lib/apt/lists/*

COPY /preprocessors/yolov8/requirements.txt /usr/src/app/requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install -r /usr/src/app/requirements.txt

COPY /schemas /usr/src/app/schemas

#check if the model exists; download it if not
RUN mkdir -p /usr/src/app/models && \
    if [ ! -f "/usr/src/app/models/yolov8x.pt" ]; then \
    echo "Model not found. Downloading..."; \
    wget -O /usr/src/app/models/yolov8x.pt https://image.a11y.mcgill.ca/models/objectDetectionWeights/yolov8x.pt; \
    else \
    echo "Model already exists. Skipping download."; \
    fi
COPY /preprocessors/yolov8 /usr/src/app 

EXPOSE 5000

ENV FLASK_APP=detect.py 

USER python
CMD [ "gunicorn", "detect:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]