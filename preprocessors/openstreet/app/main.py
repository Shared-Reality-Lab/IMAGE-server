from typing import Optional
from fastapi import FastAPI
from app.osm_service import query_osmdata, transform_osmdata,merge_street_by_name,return_intersection

app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{radius}/{lat}/{lon}")
def get_location(radius:float,lat:float, lon:float):
  raw_osmdata=query_osmdata(radius, lat, lon)
  transformed= transform_osmdata(raw_osmdata)
  merged=merge_street_by_name(transformed)
  response=return_intersection(merged)
  return (response)
