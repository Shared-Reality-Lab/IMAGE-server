Beta quality: Useful enough for testing by end-users.

# Usage

The autour preprocessor is used to analyze an embedded google map and return locations of interest around the maps locations. 

This uses the same back-end server as the Autour app (https://autour.mcgill.ca).

## Environment setup
The environment file (maps.env) should contain the API key used to call Google Places API. [Here](https://developers.google.com/maps/documentation/places/web-service/get-api-key) is the documentation for how to obtain a valid API key.: 

Following is the sample format of maps.env file:
```
GOOGLE_PLACES_KEY = [INSERT KEY STRING]
```

## Example Website:
https://developers.google.com/maps/documentation/embed/embedding-map

