ARG PYTORCH="1.11.0"
ARG CUDA="11.3"
ARG CUDNN="8"
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-devel

# NVIDIA APT KEYS
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/3bf863cc.pub
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/7fa2af80.pub

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    ca-certificates \
    g++ \
    openjdk-11-jre-headless \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY /preprocessors/action-recognition/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY /schemas /app/schemas
WORKDIR /app
COPY /preprocessors/action-recognition /app

RUN wget https://image.a11y.mcgill.ca/models/action_recognition/model.pth


EXPOSE 8080
ENV FLASK_APP=action-recognition.py
USER python
CMD [ "gunicorn", "action-recognition:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]