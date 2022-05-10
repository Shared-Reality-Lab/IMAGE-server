FROM python:3.9.5-alpine

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

#COPY /preprocessors/openstreetmap/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
#COPY /schemas /code/schemas
#COPY /preprocessors/openstreetmap/ /code

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
#CMD [ "uvicorn", "app.main:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]