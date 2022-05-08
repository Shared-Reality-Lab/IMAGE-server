FROM python:3.7-alpine

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip

COPY /preprocessors/sorting/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /app/schemas

COPY /preprocessors/sorting/ /app

EXPOSE 5000


ENV FLASK_APP=sorting.py
USER python
CMD [ "gunicorn", "sorting:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
