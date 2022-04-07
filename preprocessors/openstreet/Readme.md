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

1. Clone this repository. Note that the schemas are a submodule, so you need to either get them in the initial clone, e.g.,
```
git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git
```

or else get them after you've done the initial clone (while in the root of the cloned repo on your local machine):
```
git submodule init
git submodule update

```

2. Run 

```
git checkout openStreetM

```
3. Set DOCKER_GID variable to 134

```
export DOCKER_GID=134

```

4. Run

```
docker build schemas -t schemas
docker-compose build openstreet
docker-compose up -d orchestrator openstreet
docker run -d osm-preprocessors

```

5. Test with the request below to get sample result
```
curl -X 'GET' \
  'http://localhost:8000/location/100/49.8974309/-97.2033944' \
  -H 'accept: application/json'

```
In this case, 100 is the distance in metres while 49.8974309 and -97.2033944 are
latitude and longitude respectively of a point on the OpenStreet Map. You may play around the three values to see different results yourself.



You may also do the testing on your local machine by following all the above instructions. 
On your local machine, you may also like to download and install insomnia rest. Please see https://insomnia.rest/    

After the installation, type http://localhost:8000/location/100/49.8974309/-97.2033944 on the "GET" field.
and click the Send Button. You may also like to use postman if you so wish. The displayed results should be the same as that of (5) above, but in a more user-friendly format.

