FROM pytorch/pytorch:1.13.0-cuda11.6-cudnn8-runtime

COPY /preprocessors/content-categoriser/requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y python3-opencv wget && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install pip==24.0
RUN pip3 install -r /app/requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/content-categoriser/ /app

RUN wget https://image.a11y.mcgill.ca/models/categoriser/latest-0.ckpt
RUN wget https://download.pytorch.org/models/densenet121-a639ec97.pth
RUN mkdir -p /app/hub/checkpoints/
RUN mv densenet121-a639ec97.pth /app/hub/checkpoints/

EXPOSE 5000
ENV FLASK_APP=categoriser.py
ENV TORCH_HOME=/app
USER python
CMD [ "gunicorn", "categoriser:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
