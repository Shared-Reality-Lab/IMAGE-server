FROM pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime

COPY services/multilang-support/requirements.txt ./
RUN apt-get update && apt-get install python3 python3-pip -y
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY schemas ./schemas
COPY services/multilang-support/src ./src

EXPOSE 5000
ENV FLASK_APP=src/app.py
CMD [ "python3", "src/app.py" ]
