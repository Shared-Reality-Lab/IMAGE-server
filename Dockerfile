FROM python:3.7

RUN pip3 install --upgrade pip

#RUN pip install --upgrade pip setuptools wheel

#RUN apt-get update -y && \
#   apt-get install -y python-pip python-dev

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

#ENTRYPOINT [ "python" ]

#CMD ["flask", "run", "-h", "0.0.0.0", "-p", "5000"]

CMD [ "python", "./final.py" ]