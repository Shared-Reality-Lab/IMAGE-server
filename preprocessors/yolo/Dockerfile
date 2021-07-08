FROM schemas:latest AS schemas

FROM ultralytics/yolov5:latest

RUN wget bach.cim.mcgill.ca/atp/models/objectDetectionWeights

RUN pip3 install --upgrade pip

RUN pip install jsonschema==3.2.0

COPY --from=schemas /schemas /app/schemas

WORKDIR /app

COPY . /app

EXPOSE 5000

ENV FLASK_APP=detect.py
CMD [ "flask", "run", "--host=0.0.0.0" ]
