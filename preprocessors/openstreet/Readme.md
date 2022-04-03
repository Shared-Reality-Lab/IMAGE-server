# Description

This service basically involves automatic communication with the openstreetmap (OSM), based on the user's orientation and location, to extract critical map information within an optimum user's radius. The extracted data would be transformed to a suitable data framework, for effective audio and haptic rendering.



## Instruction (Docker Setup) - Recommended

1. Ensure you're in the directory `preprocessors/openstreet`

```
$ cd  /project-path/preprocessors/openstreet

```
2. Build the service (Only reguired for the first time)

```
$ docker-compose build
```

3. Run the service

```
$ docker-compose up
```

4. With your browser or Postman, navigate to http://localhost:8000


## Instructions (Without Docker Setup)
Follow the instructions to run this service locally.

1. Ensure you're in the directory `preprocessors/openstreet`

```
$ cd  /project-path/preprocessors/openstreet

```
2. Create a python virtual environment with the command. This is require if you're starting the project for the first time.

 ```
$ python -m venv .venv

```

3. Activate the python virtual environment

```
source .venv/bin/activate

```
or 

```
.venv\Scripts\activate

```

4. Install project libraries and dependencies

```
$ pip install -r requirements.txt
 
```
5. Start the project with the command below:

```
$ uvicorn app.main:app --reload
```


### Instructions for testing

1. Pull the image from the server 

```
$ docker run osm-preprocessors:latest 

```
2. Use the command to do local build 

```
$ docker-compose build openstreet
$ docker-compose up -d orchestrator openstreet

NB: You can stop or start the container by running the following command respectively

$ docker stop image-server_openstreet_1
or

$ docker start image-server_openstreet_1

```

3. To publish the output of the container. 

```
$ curl -X 'GET' \
  'http://localhost:8000/location/100/49.8974309/-97.2033944' \
  -H 'accept: application/json'

```

In this case, 100 is the radius in metres while 49.8974309 and -97.2033944 are
latitude and longitude respectively of a point on the OpenStreet Map. You may play around the three values to see different results yourself.

or download and install insomnia rest. Please see https://insomnia.rest/  to download   
After installing insomnia, type http://localhost:8000/location/100/49.8974309/-97.2033944 on the "GET" field.
and click the Send Button. 

