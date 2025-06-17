# Description

Alpha quality: Insufficiently refined to be tested by end-users.

This service basically involves automatic communication with the openstreetmap (OSM), based on the user's orientation and location, to extract critical map information within an optimum user's radius. The extracted data would be transformed to a suitable data framework, for effective audio and haptic rendering.

## Environment setup
The environment file (maps.env) should contain the API key used to call Google Places API. [Here](https://developers.google.com/maps/documentation/places/web-service/get-api-key) is the documentation for how to obtain a valid API key.: 

Following is the sample format of maps.env file:
```
GOOGLE_PLACES_KEY = [INSERT KEY STRING]
```

This also requires a Docker env variable, SERVERS, whose value is set to the comma-separated urls of Overpass API instances:
```
SERVERS="https://url1,https://url2"
```

## Instruction (Docker Setup) - Recommended

1. Ensure you're in the directory `preprocessors/openstreetmap`

```
$ cd  /project-path/preprocessors/openstreetmap

```
2. Build the service (Only reguired for the first time)

```
$ docker-compose build
```

3. Run the service

```
$ docker-compose up
```

4. With your browser or Postman, navigate to http://localhost:5000


## Instructions (Without Docker Setup)
Follow the instructions to run this service locally.

1. Ensure you're in the directory `preprocessors/openstreetmap`

```
$ cd  /project-path/preprocessors/openstreetmap

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

2. Run 

```
git checkout OpenStreetMap

```
3. Set your DOCKER_GID variable 


4. Run

```
docker-compose build openstreetmap
docker-compose up -d orchestrator openstreetmap
docker run --rm -p 5000:5000 osm-preprocessors

```

5. Test with the requests below, using the sample below:
```
curl -X 'POST' \
  'http://localhost:5000/preprocessor/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "request_uuid": "a3d7b6be-8f3b-47ba-8b17-4b0557e7a8ce",
  "timestamp": 1637789517,
  "coordinates": {
      "latitude": 49.8974309,
      "longitude": -97.2033944
  },
  "context": "",
  "language": "en",
  "url": "https://fake.site.com/some-url",
  "capabilities": [],
  "renderers": [
    "ca.mcgill.a11y.image.renderer.Text",
    "ca.mcgill.a11y.image.renderer.SimpleAudio",
    "ca.mcgill.a11y.image.renderer.SegmentAudio"
  ]
}'

```

In this case, 49.8974309 and -97.2033944 are latitude and longitude on the OpenStreetMap. 



You may also do the testing on your local machine by following all the above instructions. 
On your local machine, you may also like to download and install insomnia rest. Please see https://insomnia.rest/    

After the installation, copy and paste this URL http://localhost:5000/preprocessor/ on the "POST" field and then test with a POST request such as

'''
{
  "request_uuid": "a3d7b6be-8f3b-47ba-8b17-4b0557e7a8ce",
  "timestamp": 1637789517,
  "coordinates": {
      "latitude": 49.8974309,
      "longitude": -97.2033944
  },
  "context": "",
  "language": "en",
  "url": "https://fake.site.com/some-url",
  "capabilities": [],
  "renderers": [
    "ca.mcgill.a11y.image.renderer.Text",
    "ca.mcgill.a11y.image.renderer.SimpleAudio",
    "ca.mcgill.a11y.image.renderer.SegmentAudio"
  ]
}
'''

 You may also like to use postman if you so wish. The displayed results should be the same as that of (5) above, but in a more user-friendly format.

####
For additional info:
a. Computing bounding_box-

1. https://docs.google.com/document/d/1RN9tQKsTodWhX7qpr40jLGHbjzhyM4RrG0JYlSvcMrw/edit?usp=sharing

2. https://wiki.openstreetmap.org/wiki/Bounding_Box

3. https://www.katemarshallmaths.com/uploads/1/8/8/2/18821302/theory_on_latitude_and_longitude.pdf

4. https://sciencing.com/what-parallels-maps-4689046.html

5. https://stackoverflow.com/questions/238260/how-to-calculate-the-bounding-box-for-a-given-lat-lng-location

6. https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL

7. https://wiki.openstreetmap.org/wiki/Overpass_API
