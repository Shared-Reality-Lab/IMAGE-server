from typing import Optional
from copy import deepcopy
from fastapi import FastAPI
import haversine as hs
from app.osm_service import query_osmdata, transform_osmdata,extract_nodes_list,extract_intersection,merge_street_intersection_by_name
from app.osm_service import create_new_intersection_sets, my_final_data_structure, merge_street_points_by_name,merge_street_by_name
from app.osm_service import get_points_of_interest, process_points_of_interest, align_points_of_interest, collect_all_pois
from app.osm_service import merge_all_collected_pois, new_poi_alignment_format


app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{radius}/{lat}/{lon}")
def get_location(radius:float, lat:float, lon:float):
  raw_osmdata = query_osmdata(radius, lat, lon)

  amenities = get_points_of_interest(radius, lat, lon)

  transformed = transform_osmdata(raw_osmdata)

  merged = merge_street_by_name(transformed)

  intersection, link = extract_nodes_list(merged)

  new_intersection_list = create_new_intersection_sets(intersection)

  merged_intersection = merge_street_intersection_by_name(link)

  merged_street = deepcopy(merged)

  modified_new_intersection_list = deepcopy(new_intersection_list)

  my_str_data = my_final_data_structure(merged_street, modified_new_intersection_list, merged_intersection)

  merged_street_data = merge_street_points_by_name(my_str_data)

  point_of_interest = process_points_of_interest(amenities)

  align_pois = align_points_of_interest(point_of_interest, merged_street_data)

  all_pois = collect_all_pois(align_pois)

  all_pois_merged = merge_all_collected_pois(all_pois)

  new_poi_format = new_poi_alignment_format(point_of_interest, merged_street_data)

  
  
  return (new_poi_format)
