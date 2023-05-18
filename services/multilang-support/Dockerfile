FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

COPY services/multilang-support/requirements.txt ./
RUN apt-get update && apt-get install python3 python3-pip -y
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY schemas ./schemas
COPY services/multilang-support/src ./src

EXPOSE 5000
ENV FLASK_APP=src/app.py
CMD [ "python3", "src/app.py" ]