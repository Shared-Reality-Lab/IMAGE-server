FROM schemas:latest AS schemas
FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime

RUN adduser --disabled-password python
WORKDIR /app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY ./requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY --from=schemas /schemas /app/schemas
WORKDIR /app
COPY . /app


EXPOSE 5000
ENV FLASK_APP=azure_api.py
USER python
CMD [ "gunicorn", "azure_api:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
