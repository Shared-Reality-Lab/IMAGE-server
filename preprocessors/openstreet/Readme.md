# Description

This service basically involves automatic communication with the openstreetmap (OSM), based on the user's orientation and location, to extract critical map information within an optimum user's radius. The extracted data would be transformed to a suitable data framework, for effective audio and haptic rendering.



## Instruction (Docker Setup) - Recommended

1. Ensure you're in the directory `services/openstreet`

```
$ cd  /project-path/services/openstreet

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

1. Ensure you're in the directory `services/openstreet`

```
$ cd  /project-path/services/openstreet

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