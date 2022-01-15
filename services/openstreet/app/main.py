from typing import Optional
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{lat}/{lon}")
def get_location(lat: float,lon: float):
      # Connect to openmap street
      # Get the data
      # transform the data
      # return a response
    return {"lat": lat, "long": lon}
