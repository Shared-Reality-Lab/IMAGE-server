FROM python:3.8

RUN adduser --disabled-password python
WORKDIR /usr/src/app
ENV PATH="/home/python/.local/bin:${PATH}"

COPY /handlers/people-handler/ /usr/src/app

RUN pip install --upgrade pip

RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm
#RUN pip show language-tool-python
RUN chmod -R 777 /usr/src/app
ENV LTP_PATH = ./

EXPOSE 80
USER python
CMD ["gunicorn", "people_handler:app", "-b", "0.0.0.0:80", "--capture-output", "--log-level=debug" ]
