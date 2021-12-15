FROM schemas:latest AS schemas

FROM python:3.9.5

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY ./requirements.txt /app/requirements.txt


RUN pip3 install -r requirements.txt

COPY --from=schemas /schemas /app/schemas

COPY . /app

EXPOSE 5000

ENV FLASK_APP=autour.py
USER python
CMD [ "flask", "run", "--host=0.0.0.0" ]
