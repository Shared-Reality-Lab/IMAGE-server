from typing import Optional
from fastapi import FastAPI
from app.osm_service import query_osmdata, transform_osmdata,merge_street_by_name,extract_nodes_list,extract_intersection,merge_street_intersection_by_name

app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{radius}/{lat}/{lon}")
def get_location(radius:float,lat:float, lon:float):
  raw_osmdata=query_osmdata(radius, lat, lon)
  transformed= transform_osmdata(raw_osmdata)
  merged=merge_street_by_name(transformed)
  result=extract_nodes_list(merged)
  response=merge_street_intersection_by_name(result)
  
  return (response)
