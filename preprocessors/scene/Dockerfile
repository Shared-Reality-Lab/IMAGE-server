FROM python:3.7

RUN apt-get update && apt-get install -y python3-opencv && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN wget http://places2.csail.mit.edu/models_places365/wideresnet18_places365.pth.tar

RUN pip3 install --upgrade pip

COPY /preprocessors/scene/requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

COPY /schemas /app/schemas

COPY /preprocessors/scene /app

EXPOSE 5000


#CMD [ "python", "./run_placesCNN_unified.py" ]

ENV FLASK_APP=run_placesCNN_unified.py
USER python
CMD [ "flask", "run", "--host=0.0.0.0" ]
