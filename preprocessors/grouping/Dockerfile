FROM schemas:latest AS schemas

FROM python:3.7

RUN apt-get update && apt-get install -y python3-opencv && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY --from=schemas /schemas /app/schemas

COPY . /app

EXPOSE 5000


ENV FLASK_APP=grouping.py
USER python
CMD [ "gunicorn", "grouping:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
