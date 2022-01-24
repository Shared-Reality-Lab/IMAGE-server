from typing import List
import overpy
import json

def query_osmdata(radius:float, lat:float, lon:float):
  api = overpy.Overpass()
  result=api.query (f'way(around:{radius},{lat},{lon})["highway"=""];(._;>;);out body;')
  return (result)


def transform_osmdata(raw_osmdata: List[dict]):
  street_data_list=[]
  for way in raw_osmdata.ways:
    nodes_list=[] 
    for node in way.nodes:
      node_record={"node":node.id,"lat":str(node.lat),"lon":str(node.lon)}
      if node_record not in nodes_list:
        nodes_list.append(node_record)
        way_record={"street_name":way.tags.get("name","n/a"),"street_type":way.tags.get("highway"),"nodes":nodes_list} 
        street_data_list.append(way_record)
        
  return (street_data_list)


