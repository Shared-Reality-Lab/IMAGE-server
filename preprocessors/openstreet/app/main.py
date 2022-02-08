from typing import Optional
from copy import deepcopy
from fastapi import FastAPI
from app.osm_service import query_osmdata, transform_osmdata,extract_nodes_list,extract_intersection
from app.osm_service import create_new_intersection_sets, my_final_data_structure, merge_street_points_by_name,merge_street_by_name

app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{radius}/{lat}/{lon}")
def get_location(radius:float, lat:float, lon:float):
  raw_osmdata = query_osmdata(radius, lat, lon)
  transformed = transform_osmdata(raw_osmdata)
  merged = merge_street_by_name(transformed)
  result = extract_nodes_list(merged)
  new_intersection_list = create_new_intersection_sets(result)

  merged_d = deepcopy(merged)
  modified_new_intersection_list = deepcopy(new_intersection_list)
  
  my_str_data = my_final_data_structure(merged_d,modified_new_intersection_list)
  my_response = merge_street_points_by_name(my_str_data)
  #response = merge_street_intersection_by_name(result)
  
  return (my_response)
