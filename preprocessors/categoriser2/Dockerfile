FROM schemas:latest AS schemas
FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime

COPY ./requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY --from=schemas /schemas /app/schemas
WORKDIR /app
COPY . /app


EXPOSE 5000
ENV FLASK_APP=azure_api.py
CMD [ "flask", "run", "--host=0.0.0.0" ]