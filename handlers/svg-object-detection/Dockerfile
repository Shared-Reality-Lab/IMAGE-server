FROM python:3.10

RUN apt-get install libcairo2

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /handlers/svg-object-detection/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /schemas /usr/src/app/schemas
COPY /handlers/svg-object-detection/ /usr/src/app

EXPOSE 80
USER python
CMD ["gunicorn", "od_svg:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug" ]