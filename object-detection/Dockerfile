FROM schemas:latest AS schemas

FROM python:3.7

RUN apt-get update && apt-get install -y python3-opencv && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

COPY ./requirements.txt /app/requirements.txt

COPY --from=schemas /schemas app/schemas

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

EXPOSE 5000


#CMD [ "python", "./final.py" ]

ENV FLASK_APP=final.py
CMD [ "flask", "run", "--host=0.0.0.0" ]
