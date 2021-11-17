FROM schemas:latest AS schemas

FROM ultralytics/yolov5:v5.0

RUN wget bach.cim.mcgill.ca/atp/models/objectDetectionWeights/yolov5s.pt

RUN pip3 install --upgrade pip
RUN pip install gunicorn
RUN pip install jsonschema==3.2.0

COPY --from=schemas /schemas /usr/src/app/schemas
WORKDIR /usr/src/app
COPY . /usr/src/app

EXPOSE 5000

ENV FLASK_APP=detect.py
CMD [ "gunicorn", "detect:app", "-b", "0.0.0.0:5000" ]
