FROM schemas:latest AS schemas

FROM ultralytics/yolov5:v6.0

RUN wget bach.cim.mcgill.ca/atp/models/objectDetectionWeights/yolov5x.pt

RUN pip3 install --upgrade pip
RUN pip install gunicorn==20.1.0
RUN pip install jsonschema==3.2.0

COPY --from=schemas /schemas /usr/src/app/schemas
WORKDIR /usr/src/app
COPY . /usr/src/app
#RUN sed -i "s|releases/latest|releases/tag/v5.0|g" /usr/src/app/utils/google_utils.py

EXPOSE 5000

ENV FLASK_APP=detect.py
CMD [ "gunicorn", "detect:app", "-b", "0.0.0.0:5000" ]
