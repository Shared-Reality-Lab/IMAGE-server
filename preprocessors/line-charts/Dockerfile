FROM python:3.10

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip3 install --upgrade pip

COPY /preprocessors/line-charts/requirements.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas

COPY /preprocessors/line-charts/ /app

EXPOSE 5000

ENV FLASK_APP=charts.py
USER python
CMD [ "gunicorn", "charts:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
