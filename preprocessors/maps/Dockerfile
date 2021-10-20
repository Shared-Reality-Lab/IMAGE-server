FROM schemas:latest AS schemas

FROM python:3.9.5

RUN pip3 install --upgrade pip

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY --from=schemas /schemas /app/schemas

COPY . /app

EXPOSE 5000

ENV FLASK_APP=maps.py
CMD [ "flask", "run", "--host=0.0.0.0" ]