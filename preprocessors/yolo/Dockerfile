FROM schemas:latest AS schemas

FROM ultralytics/yolov5:latest

RUN wget bach.cim.mcgill.ca/atp/models/objectDetectionWeights

RUN pip3 install --upgrade pip

COPY ./requirements.txt /app/requirements.txt

COPY --from=schemas /schemas /app/schemas

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

EXPOSE 5000

ENV FLASK_APP=detect.py
CMD [ "flask", "run", "--host=0.0.0.0" ]
