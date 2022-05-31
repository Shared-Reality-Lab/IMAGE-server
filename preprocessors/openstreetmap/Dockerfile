FROM python:3.9.5-alpine

RUN adduser --disabled-password python

WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY ./preprocessors/openstreetmap/requirements.txt /app/requirements.txt


RUN pip3 install -r requirements.txt

COPY ./schemas /app/schemas

COPY ./preprocessors/openstreetmap/ /app

EXPOSE 5000

ENV FLASK_APP=main.py
USER python
CMD [ "gunicorn", "main:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]





#FROM python:3.9.5-alpine

#RUN adduser --disabled-password python
#WORKDIR /app
#ENV PATH="/home/python/.local/bin:${PATH}"

#RUN pip3 install --upgrade pip

#COPY ./requirements.txt /app/requirements.txt


#RUN pip3 install -r requirements.txt

#COPY ./ /app

#EXPOSE 5000

#ENV FLASK_APP=main.py
#USER python
#CMD [ "gunicorn", "main:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]



##FROM python:3.9.5-alpine

##WORKDIR /code

##COPY ./requirements.txt /code/requirements.txt

#COPY /preprocessors/openstreetmap/requirements.txt /code/requirements.txt

##RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

##COPY ./app /code/app
#COPY /schemas /code/schemas
#COPY /preprocessors/openstreetmap/ /code

##EXPOSE 8000

##CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
#CMD [ "uvicorn", "app.main:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
#FROM python:3.9.5-alpine


#WORKDIR /app

#RUN pip3 install --upgrade pip

#COPY /preprocessors/openstreetmap/requirements.txt /app/requirements.txt


#RUN pip3 install -r requirements.txt

#COPY /schemas /app/schemas

#COPY /preprocessors/openstreetmap/ /app

#EXPOSE 8000


#CMD [ "uvicorn", "main:app", "-b", "0.0.0.0:8000", "--capture-output", "--log-level=debug" ]
