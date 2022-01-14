from typing import Optional
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"Hello": "Africa"}


@app.get("/location/{lat}/{lon}")
def get_location(lat: float,lon: float):
      # Connect to openmap street
      # Get the data
      # transform the data
      # return a response
    return {"lat": lat, "long": lon}


@app.get("/profile/{name}")
def get_profile(name: str):
      return {"name": name}