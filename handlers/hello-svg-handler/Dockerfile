FROM python:3.10-alpine

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /handlers/hello-svg-handler/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /usr/src/app/schemas
COPY /handlers/hello-svg-handler/ /usr/src/app

EXPOSE 5000
USER python
CMD ["gunicorn", "hello_svg:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
