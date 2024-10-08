FROM python:3.10

RUN apt-get install libcairo2

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

RUN pip install --upgrade pip
COPY /services/monarch-link-app/requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

COPY /services/monarch-link-app/ /usr/src/app

RUN chown -R python:python /usr/src/app

EXPOSE 80
USER python
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug" ]