FROM python:3.8

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"
RUN apt-get update && apt-get install -y python3-opencv wget && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip

COPY /preprocessors/emotion-recognition/requirements.txt /app/requirements.txt
#COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /app/schemas

COPY /preprocessors/emotion-recognition/ /app
#COPY ./ /app

#RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host=files.pythonhosted.org -e .

EXPOSE 5000


ENV FLASK_APP=emotion-recognition.py
USER python
CMD [ "gunicorn", "emotion-recognition:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]

