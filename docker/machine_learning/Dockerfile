FROM schemas:latest AS schemas

FROM python:3.7

RUN pip3 install --upgrade pip

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

COPY --from=schemas /schemas app/schemas


CMD [ "python", "./final.py" ]