FROM schemas:latest AS schemas

FROM python:3.7

RUN apt-get update && apt-get install -y python3-opencv

RUN pip3 install --upgrade pip

COPY ./requirements.txt /app/requirements.txt

COPY --from=schemas /schemas app/schemas

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app


CMD [ "python", "./final.py" ]