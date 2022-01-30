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
      node_record={"id":node.id,"lat":str(node.lat),"lon":str(node.lon)}
      if node_record not in nodes_list:
        nodes_list.append(node_record)
        way_record={"street_name":way.tags.get("name","n/a"),"street_type":way.tags.get("highway","n/a"),"surface":way.tags.get("surface","n/a"),"oneway":way.tags.get("oneway","n/a"),"sidewalk":way.tags.get("sidewalk","n/a"),"nodes":nodes_list} 
        street_data_list.append(way_record)
        #remove duplicate objects if any
        cleaned_street_data_list=[]
        for obj in street_data_list:
           if obj not in cleaned_street_data_list:
             cleaned_street_data_list.append(obj)   
               
  return (cleaned_street_data_list)

def merge_street_by_name(transformed_osmdata:List[dict]):
  response=transformed_osmdata
  output={}
  for obj in response:
    str_name=obj["street_name"]
    if str_name not in output:
      assert obj["nodes"] is not None
      record={"street_name":obj["street_name"],"street_type":obj["street_type"],"surface":obj["surface"], "sidewalk":obj["sidewalk"],"oneway":obj["oneway"],"nodes": obj["nodes"]} 
      output[str_name]= record
    else:
      existing_record = output[str_name]
      existing_nodes = existing_record["nodes"]
      assert existing_nodes is not None
      new_node = obj["nodes"]
      assert new_node is not None
      merged_node = existing_nodes + new_node
      existing_record["nodes"] = merged_node
      output[str_name] = existing_record
      merged_street = list(output.values())
  return(merged_street)

def return_intersection(merged_street_data:List[dict]):
  street_intersection=[]
  for i,items in enumerate (merged_street_data):
    nodes_object=items["nodes"]
    intersection=process_intersection(nodes_object)
    total_coordinates_sets=len(intersection)
    intersection_records={"street_name":items["street_name"],"street_type":items["street_type"],"surface":items["surface"], "sidewalk":items["sidewalk"],"oneway":items["oneway"],"total_coordinates_sets":total_coordinates_sets,"intersection_coordinates":intersection}
    street_intersection.append(intersection_records)
  return(street_intersection)

def process_intersection(nodes_object):
  intersection_list=[]
  for i, items in enumerate (nodes_object):
    number_of_nodes=len(nodes_object)
    if i<number_of_nodes:
      nom=i+1
      for j in range (nom,number_of_nodes):
        if nodes_object[i]==nodes_object[j]:
          shared_nodes=nodes_object[i]
          intersection_list.append(shared_nodes)
  return(intersection_list)