FROM python:3.9.5

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY /preprocessors/ocr/requirements.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas

COPY /preprocessors/ocr/ /app

EXPOSE 5000

ENV FLASK_APP=ocr.py
USER python
CMD [ "gunicorn", "ocr:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]