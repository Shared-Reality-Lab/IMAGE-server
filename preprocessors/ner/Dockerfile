FROM python:3.8-slim-buster

WORKDIR /app
RUN adduser --disabled-password python
ENV PATH="/home/python/.local/bin:${PATH}"
COPY /preprocessors/ner/requirements.txt /app/requirements.txt

# intstalling chrome driver
RUN apt-get update && \
    apt-get install -y gnupg wget curl unzip --no-install-recommends && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
    apt-get update -y && \
    apt-get install -y google-chrome-stable && \
    CHROMEVER=$(google-chrome --product-version | grep -o "[^\.]*\.[^\.]*\.[^\.]*") && \
    DRIVERVER=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROMEVER") && \
    wget -q --continue -P /chromedriver "http://chromedriver.storage.googleapis.com/$DRIVERVER/chromedriver_linux64.zip" && \
    unzip /chromedriver/chromedriver* -d /chromedriver

# installing gcc
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv gcc wget git && rm -rf /var/lib/apt/lists/*

RUN pip3 install -r requirements.txt

COPY /schemas /app/schemas
COPY /preprocessors/ner/ /app

EXPOSE 5000
ENV FLASK_APP=ner.py

USER python
CMD [ "gunicorn", "ner:app", "-b", "0.0.0.0:5000", "--capture-output", "--log-level=debug" ]
