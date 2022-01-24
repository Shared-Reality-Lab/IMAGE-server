from typing import Optional
from fastapi import FastAPI
from app.osm_service import query_osmdata, transform_osmdata


app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{radius}/{lat}/{lon}")
def get_location(radius:float,lat:float, lon:float):
  raw_osmdata=query_osmdata(radius, lat, lon)
  response= transform_osmdata(raw_osmdata)
  return (response)
