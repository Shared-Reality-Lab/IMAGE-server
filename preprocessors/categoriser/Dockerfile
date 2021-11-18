FROM schemas:latest AS schemas
FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime

COPY ./requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y python3-opencv && rm -rf /var/lib/apt/lists/*
RUN pip3 install --upgrade pip
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*
RUN pip install -r /app/requirements.txt


COPY --from=schemas /schemas /app/schemas
WORKDIR /app
COPY . /app


RUN wget https://image.a11y.mcgill.ca/models/categoriser/latest-0.ckpt 
RUN wget https://download.pytorch.org/models/densenet121-a639ec97.pth
RUN mkdir -p /app/hub/checkpoints/
RUN mv densenet121-a639ec97.pth /app/hub/checkpoints/

EXPOSE 5000
ENV FLASK_APP=categoriser.py
ENV TORCH_HOME=/app
CMD [ "gunicorn", "categoriser:app", "-b", "0.0.0.0:5000" ]