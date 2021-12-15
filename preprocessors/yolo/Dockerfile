FROM schemas:latest AS schemas

FROM ultralytics/yolov5:v6.0


WORKDIR /usr/src/app
RUN adduser --disabled-password python
ENV PATH="/usr/src/app/.local/bin:${PATH}"

RUN wget bach.cim.mcgill.ca/atp/models/objectDetectionWeights/yolov5x.pt

RUN pip3 install --upgrade pip
RUN pip3 install gunicorn==20.1.0
RUN pip3 install jsonschema==3.2.0

COPY --from=schemas /schemas /usr/src/app/schemas
COPY . /usr/src/app


EXPOSE 5000

ENV FLASK_APP=detect.py
USER python
CMD [ "gunicorn", "detect:app", "-b", "0.0.0.0:5000" ]
