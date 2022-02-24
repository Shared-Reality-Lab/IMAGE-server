from typing import List
import overpy
import json
from copy import deepcopy
import haversine as hs
import random


#Send request to get map data from OSM
def query_osmdata(radius:float, lat:float, lon:float):
  api = overpy.Overpass()
  result = api.query (f'way(around:{radius},{lat},{lon})[highway~"^(primary|tertiary|residential|service|footway)$"];(._;>;);out body;')
  #[highway~"^(residential|service|footway)$"];(._;>;);out body;')
  #
  return (result)
#Send request to get points of interests (POIs)
def get_points_of_interest(radius:float, lat:float, lon:float):
  api = overpy.Overpass()
  result1 = api.query (f'node(around:{radius},{lat},{lon})["amenity" = ""];(._;>;);out body;')
  return (result1)

#Retrieve inteterested street information from the requested OSM data
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
        #Remove duplicate objects if any
        cleaned_street_data_list=[]
        for obj in street_data_list:
          if obj not in cleaned_street_data_list:
            cleaned_street_data_list.append(obj)              
  return (cleaned_street_data_list)


#Group all street information on street name (to achieve street by street record)
def merge_street_by_name(transformed_osmdata: List[dict]):
  response=transformed_osmdata
  output={}
  for obj in response:
    str_name=obj["street_name"]
    if str_name not in output:
      assert obj["nodes"] is not None
      record={"street_id":random.randint(10_000_000, 99_999_999),"street_name":obj["street_name"],"nodes": obj["nodes"]} 
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
    # Clean nodes to remove duplicated nodes in any given street
    for objs in range (len(merged_street)):
      unique_nodes = []
      nodes = merged_street[objs]["nodes"]
      for node in range (len(nodes)):
        if nodes[node] not in unique_nodes:
          unique_nodes.append(nodes[node])
          merged_street[objs]["nodes"] = unique_nodes
  return(merged_street)


#Compare two streets for possible intersection
def extract_intersection(list1, list2):
  computed_intersection = [x for x in list1 if x in list2]  
  return(computed_intersection)


#The function uses loop to extract sets of points (nodes) for any two streets and send out for possible intersection and so on
def extract_nodes_list(result):
  intersection_sets = []
  #List str_link contains the same intersection sets as "intersection_sets" except that it 
  #contains more additional information such as street_name, etc
  str_link = []
  for i in range(len(result)):
    for j in range(i + 1, len(result)):
      list1 = (result[i]["nodes"])
      list2 = (result[j]["nodes"])
      intersection = extract_intersection(list1,list2)
      if len(intersection):
        str_record={"street_name":result[i]["street_name"],"intersection_sets":intersection} 
        str_link.append(str_record)
        #intersection_sets.append(str_record)
        #str_record={"street_name":result[j]["street_name"],"street_type":result[j]["street_type"],"surface":result[j]["surface"], "sidewalk":result[j]["sidewalk"],"oneway":result[j]["oneway"],"intersection_sets":intersection} 
        str_record={"street_name":result[j]["street_name"],"intersection_sets":intersection} 
        str_link.append(str_record)
        intersection_sets.append(intersection)
  return(intersection_sets, str_link)

#Creata a function to group street intersections by their respective street names
def merge_street_intersection_by_name(str_link):
  response=str_link
  output={}
  for obj in response:
    str_name=obj["street_name"]
    if str_name not in output:
      assert obj["intersection_sets"] is not None
      record={"street_name":obj["street_name"],"intersection_sets": obj["intersection_sets"]} 
      output[str_name]= record
    else:
      existing_record = output[str_name]
      existing_intersection = existing_record["intersection_sets"]
      assert existing_intersection is not None
      new_intersection = obj["intersection_sets"]
      assert new_intersection is not None
      merged_intersection = existing_intersection + new_intersection
      existing_record["intersection_sets"] = merged_intersection
      output[str_name] = existing_record
  merged_intersection = list(output.values())
  #.....
  #remove duplicate objects if any
  #cleaned_intersection_data_list=[]
  #for obj in merged_intersection:
  #if obj not in cleaned_intersection_data_list:
  #cleaned_intersection_data_list.append(obj)
  #return(cleaned_intersection_data_list)

  return (merged_intersection)

  
#Create a new single list of intersection objects [{},{},{}...]
def create_new_intersection_sets(result):
  modified_intersection_sets=[]
  for intersect_list in result:
    for obj in intersect_list:
      modified_intersection_sets.append(obj)
  return(modified_intersection_sets)


#Loop through all the nodes across the ways and indicate if a node is an intersection or not. It
#also indicates what street is intersecting with what street.
#This is to fit in to the desired structure in mind
def my_final_data_structure(merged_street, modified_intersection_set, merged_intersection):
  str_records = []
  for obj in range (len(merged_street)):
    nodes= merged_street[obj]["nodes"]
    for i in range (len(nodes)):
      if nodes[i] not in modified_intersection_set:
        alist=[]
        node = nodes[i]
        #node["inter_link"] = "nil"
        alist.append(node)
        str_info={"street_name":merged_street[obj]["street_name"],"nodes":alist} 
        str_records.append(str_info)
      else:
        for ob_items in range (len(merged_intersection)):
          merged_street_name = merged_street[obj]["street_name"]
          intersected_street_name = merged_intersection[ob_items]["street_name"]
          if merged_street_name != intersected_street_name:
            nod=merged_intersection[ob_items]["intersection_sets"]
            for n_items in range (len(nod)):
              if nodes[i]==nod[n_items]:
                alist=[]
                blist=[]
                node = nodes[i]
                node["cat"] = "intersection"
                alist.append(node)
                node["name"]= "intersection "+ merged_street_name +" and "+ intersected_street_name
                blist.append(node)
                str_info={"street_name":merged_street[obj]["street_name"],"nodes":alist}
                str_records.append(str_info)
  return(str_records)


#Sort out the final data structure and group by name
def merge_street_points_by_name(my_str_data):
  output = {}
  for obj in my_str_data:
    str_name = obj["street_name"]
    if str_name not in output:
      assert obj["nodes"] is not None
      record={"street_id":random.randint(10_000_000, 99_999_999),"street_name":obj["street_name"],"nodes": obj["nodes"]} 
      output[str_name]= record

    else:
      existing_record = output[str_name]
      existing_node = existing_record["nodes"]
      assert existing_node is not None
      new_node = obj["nodes"]
      assert new_node is not None
      merged_node = existing_node + new_node
      existing_record["nodes"] = merged_node
      output[str_name] = existing_record
  merged_street_data = list(output.values())

      #remove duplicate objects if any
      #cleaned_node_data_list=[]
      #for obj in merged_node:
      #if obj not in cleaned_node_data_list:
      #cleaned_node_data_list.append(obj)
      #merged_data_structure=cleaned_node_data_list

  return(merged_street_data)
  # Seive out the desired features of POIs
def process_points_of_interest(amenities):
  point_of_interest=[]
  for node in amenities.nodes:
    if node.tags.get("amenity") is not None:
      #print("Name: %s" % node.tags.get("name", "n/a"))
      #print("Amenity: %s" % node.tags.get("amenity", "n/a"))
      #print("Nodes:")
      #print("    node: %d, Lat: %f, Lon: %f" % (node.id, node.lat, node.lon))
      node_record={"id":str(node.id),"lat":str(node.lat),"lon":str(node.lon)}

      amenity_record ={ "name":node.tags.get("name"),"cat":node.tags.get("amenity"),"nodes":node_record}
      point_of_interest.append(amenity_record)
  return(point_of_interest)

#Match/connect POIs to the streets
def align_points_of_interest(point_of_interest, merged_street_data):
  street_data_cpy = deepcopy(merged_street_data)
  for poi in range (len(point_of_interest)):
    distance_list = []
    street_data = merged_street_data
    for obj in range (len(street_data)):
      nodes = street_data[obj]["nodes"]
      for node_items in range (len(nodes)):
        lat1 = nodes[node_items]["lat"]
        lon1 = nodes[node_items]["lon"]
        lat2 = point_of_interest[poi]["nodes"]["lat"]
        lon2 = point_of_interest[poi]["nodes"]["lon"]
        location1 = (float(lat1), float(lon1))
        location2 = (float(lat2), float(lon2))
        distance = hs.haversine(location1, location2)
        if (len(distance_list))==0:
          distance_list.append(distance)
          #print("distance:",distance)
          street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items + 1}
        else:
          if distance < distance_list[0]:
            distance_list[0] = distance
            #print("distance:",distance)
            street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items + 1} 
      
    for str_obj in range (len(street_data_cpy)):
      if street_data_cpy[str_obj]["street_name"] == street_record["street_name"]:
        nodes = street_data_cpy[str_obj]["nodes"]
        nodes.insert(street_record["node_index"], street_record["poi"])
  return (street_data_cpy)



# Collect only all points of interest (pois) including intersections, restaurants, etc. street by street
def collect_all_pois(align_pois):
  collected_pois = deepcopy(align_pois)
  for obj in range (len(collected_pois)):
    nodes = collected_pois[obj]["nodes"]
    poi_collection = []
    for node in range (len(nodes)):
      key_to_check = "cat"
      if key_to_check in nodes[node]:
        if nodes[node]["cat"]:
          poi_collection.append(nodes[node])
    collected_pois[obj]["nodes"] = poi_collection 
    collected_pois[obj]["pois"] = collected_pois[obj].pop("nodes")
  return(collected_pois)

# Merge all points of interest from all the streets together in a single list
def merge_all_collected_pois(all_pois):
  pois_list = []
  id_record = []
  all_pois_merged_list = []
  for obj in range (len(all_pois)):
    pois = all_pois[obj]["pois"]
    for poi in range (len(pois)):
      pois_list.append(pois[poi])

  #Remove duplicated pois
  for unique_obj in range (len(pois_list)):
    key_to_check = "nodes"

    if key_to_check in pois_list[unique_obj]:
      if pois_list[unique_obj]["nodes"]["id"] not in id_record:
        all_pois_merged_list.append(pois_list[unique_obj])
        id_record.append(pois_list[unique_obj]["nodes"]["id"])

    else:
      
      if pois_list[unique_obj]["id"] not in id_record:
        all_pois_merged_list.append(pois_list[unique_obj])
        id_record.append(pois_list[unique_obj]["id"])


  return(all_pois_merged_list, pois_list)

#FORMAT ONE:.......this is the collection of all streets, nodes in streets that are adjacent to a POI
#have an inter_link. The interlink is an array so it can hold more than one POI if needed.
#each street has its unique ID, so we could look it up
def new_poi_alignment_format (point_of_interest, merged_street_data):

  id_list = []
  new_node_tied_to_poi_list = []
  street_data_cpy = deepcopy(merged_street_data)

  for poi in range (len(point_of_interest)):
    distance_list = []
    poi_list = []
    street_data = merged_street_data

    for obj in range (len(street_data)):
      nodes = street_data[obj]["nodes"]

      for node_items in range (len(nodes)):
        lat1 = nodes[node_items]["lat"]
        lon1 = nodes[node_items]["lon"]
        lat2 = point_of_interest[poi]["nodes"]["lat"]
        lon2 = point_of_interest[poi]["nodes"]["lon"]
        location1 = (float(lat1), float(lon1))
        location2 = (float(lat2), float(lon2))
        distance = hs.haversine(location1, location2)
        
        if (len(distance_list))==0:
          distance_list.append(distance)
          poi_list.append(point_of_interest[poi])
          #print("distance:",distance)
          street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items,"poi_list":poi_list}
        else:
          
          if distance < distance_list[0]:
            distance_list[0] = distance
            #print("distance:",distance)
            street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items,"poi_list":poi_list} 
      

    street_data_cpyy = deepcopy(street_data_cpy) 
    #merge pois when we have multiple pois competeting for a node and assign it to key called slink
    for str_obj in range (len(street_data_cpyy)):
      
      if street_data_cpyy[str_obj]["street_name"] == street_record["street_name"]:
        index = street_record["node_index"]
        node_tied_to_poi = street_data_cpyy[str_obj]["nodes"][index]
        id = node_tied_to_poi["id"] # key

        if id not in id_list:
          id_list.append(id)
          node_tied_to_poi["s_link"] =  street_record["poi_list"]  
          new_node_tied_to_poi = {"key_id":id, "tied_node":node_tied_to_poi}
          new_node_tied_to_poi_list.append(new_node_tied_to_poi)
         
        else:
          
          for item_s in range (len(new_node_tied_to_poi_list)):
            
            if new_node_tied_to_poi_list[item_s]["key_id"] == id:
              existing_poi = new_node_tied_to_poi_list[item_s]["tied_node"]["s_link"]
              new_poi = street_record["poi_list"]
              merged_poi = existing_poi + new_poi
              node_tied_to_poi["s_link"] = merged_poi
              
              if new_node_tied_to_poi_list[item_s]["key_id"] == id:
                new_node_tied_to_poi_list[item_s]["tied_node"]["s_link"] = node_tied_to_poi["s_link"]


  #match the pois in new_node_tied_to_poi_list to the concerned node in each street
  for obj in range(len(new_node_tied_to_poi_list)):
    key_id = new_node_tied_to_poi_list[obj]["key_id"]
    
    for objs in range (len(street_data_cpyy)):
      nodes = street_data_cpyy[objs]["nodes"]
      
      for node in range (len(nodes)):
        
        if nodes[node]["id"] == key_id:
          nodes[node] = new_node_tied_to_poi_list[obj]["tied_node"]
    
  return (street_data_cpyy)


#FORMAT:TWO.......First collect all points of all categories (inter_section, restaurant, fast_food, etc) in an array 
#and align them to the respective adjacent nodes
def second_new_poi_alignment_format(all_pois_merged, merged_str_data):
  #Remove duplicated POIs
  
  point_of_interest = all_pois_merged
  merged_street_data = merged_str_data

  id_list = []
  new_node_tied_to_poi_list = []
  street_data_cpy = deepcopy(merged_street_data)

  for poi in range (len(point_of_interest)):
    distance_list = []
    poi_list = []
    street_data = merged_street_data

    for obj in range (len(street_data)):
      nodes = street_data[obj]["nodes"]

      for node_items in range (len(nodes)):
        lat1 = nodes[node_items]["lat"]
        lon1 = nodes[node_items]["lon"]
        key_to_check = "nodes"
        if key_to_check in point_of_interest[poi]:
          lat2 = point_of_interest[poi]["nodes"]["lat"]
          lon2 = point_of_interest[poi]["nodes"]["lon"]
          location1 = (float(lat1), float(lon1))
          location2 = (float(lat2), float(lon2))
          distance = hs.haversine(location1, location2)
        else:
          lat2 = point_of_interest[poi]["lat"]
          lon2 = point_of_interest[poi]["lon"]
          location1 = (float(lat1), float(lon1))
          location2 = (float(lat2), float(lon2))
          distance = hs.haversine(location1, location2)
  
        if (len(distance_list))==0:
          distance_list.append(distance)
          poi_list.append(point_of_interest[poi])
          #print("distance:",distance)
          street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items,"poi_list":poi_list}
        else:
          
          if distance < distance_list[0]:
            distance_list[0] = distance
            #print("distance:",distance)
            street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items,"poi_list":poi_list} 
      

    street_data_cpyy = deepcopy(street_data_cpy) 
    #merge pois when we have multiple pois competeting for a node and assign it to key called slink
    for str_obj in range (len(street_data_cpyy)):
      
      if street_data_cpyy[str_obj]["street_name"] == street_record["street_name"]:
        index = street_record["node_index"]
        node_tied_to_poi = street_data_cpyy[str_obj]["nodes"][index]
        id = node_tied_to_poi["id"] # key

        if id not in id_list:
          id_list.append(id)
          node_tied_to_poi["pois_link"] =  street_record["poi_list"]  
          new_node_tied_to_poi = {"key_id":id, "tied_node":node_tied_to_poi}
          new_node_tied_to_poi_list.append(new_node_tied_to_poi)
         
        else:
          
          for item_s in range (len(new_node_tied_to_poi_list)):
            
            if new_node_tied_to_poi_list[item_s]["key_id"] == id:
              existing_poi = new_node_tied_to_poi_list[item_s]["tied_node"]["pois_link"]
              new_poi = street_record["poi_list"]
              merged_poi = existing_poi + new_poi
              node_tied_to_poi["pois_link"] = merged_poi
              
              if new_node_tied_to_poi_list[item_s]["key_id"] == id:
                new_node_tied_to_poi_list[item_s]["tied_node"]["pois_link"] = node_tied_to_poi["pois_link"]


  #match the pois in new_node_tied_to_poi_list to the concerned node in each street
  for obj in range(len(new_node_tied_to_poi_list)):
    key_id = new_node_tied_to_poi_list[obj]["key_id"]
    
    for objs in range (len(street_data_cpyy)):
      nodes = street_data_cpyy[objs]["nodes"]
      
      for node in range (len(nodes)):
        
        if nodes[node]["id"] == key_id:
          nodes[node] = new_node_tied_to_poi_list[obj]["tied_node"]
    
  return (street_data_cpyy)



#FORMAT THREE:........First collect all points of all categories (inter_section, restaurant, fast_food, etc) in an array 
#and align them to the respective adjacent nodes

def third_new_poi_alignment_format(secon_poi_format):
  second_poi_format = deepcopy(secon_poi_format)

  for obj in range (len(second_poi_format)):
    nodes = second_poi_format[obj]["nodes"]

    for node in range (len(nodes)):
      key_to_check = "pois_link"

      if key_to_check in nodes[node]:
        pois_link = nodes[node]["pois_link"]
        
        for items in range (len(pois_link)):
          cat = pois_link[items]["cat"]

          if "nodes" in pois_link[items]:
            key_id = pois_link[items]["nodes"]["id"]
            lat = pois_link[items]["nodes"]["lat"]
            lon = pois_link[items]["nodes"]["lon"]
            
            pois_link[items] = {"id":key_id, "cat":cat, "lat":lat, "lon":lon}
          else:
            key_id = pois_link[items]["id"]
            lat = pois_link[items]["lat"]
            lon = pois_link[items]["lon"]
            
            pois_link[items] = {"id":key_id, "cat":cat, "lat":lat, "lon":lon}

  third_poi_format = second_poi_format

  return(third_poi_format)



#FORMAT FOUR:........First collect all points of all categories (inter_section, restaurant, fast_food, etc) in an array 
#and align them to the respective adjacent nodes
def fourth_poi_alignment_format (all_pois_merged, merged):

  point_of_interest = all_pois_merged

  id_list = []
  new_node_tied_to_poi_list = []
  street_data_cpy = deepcopy(merged)

  for poi in range (len(point_of_interest)):
    distance_list = []
    poi_list = []
    
    street_data = merged

    for obj in range (len(street_data)):
      nodes = street_data[obj]["nodes"]

      for node_items in range (len(nodes)):
        lat1 = nodes[node_items]["lat"]
        lon1 = nodes[node_items]["lon"]
        
        key_to_check = "nodes"
        if key_to_check in point_of_interest[poi]:
          lat2 = point_of_interest[poi]["nodes"]["lat"]
          lon2 = point_of_interest[poi]["nodes"]["lon"]
          location1 = (float(lat1), float(lon1))
          location2 = (float(lat2), float(lon2))
          distance = hs.haversine(location1, location2)
        else:
          lat2 = point_of_interest[poi]["lat"]
          lon2 = point_of_interest[poi]["lon"]
          location1 = (float(lat1), float(lon1))
          location2 = (float(lat2), float(lon2))
          distance = hs.haversine(location1, location2)
  
        
        if (len(distance_list))==0:
          distance_list.append(distance)
          poi_list.append(point_of_interest[poi])
          #print("distance:",distance)
          street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items,"poi_list":poi_list}
        else:
          
          if distance < distance_list[0]:
            distance_list[0] = distance
            #print("distance:",distance)
            street_record = {"street_name":street_data[obj]["street_name"],"poi":point_of_interest[poi],"node_index":node_items,"poi_list":poi_list} 
      

    street_data_cpyy = deepcopy(street_data_cpy) 
    #merge pois when we have multiple pois competeting for a node and assign it to key called slink
    for str_obj in range (len(street_data_cpyy)):
      
      if street_data_cpyy[str_obj]["street_name"] == street_record["street_name"]:
        index = street_record["node_index"]
        node_tied_to_poi = street_data_cpyy[str_obj]["nodes"][index]
        key_id = node_tied_to_poi["id"] # key

      
        if key_id not in id_list:
          id_list.append(key_id)

          if "nodes" in point_of_interest[poi]:

            poi_id = str(point_of_interest[poi]["nodes"]["id"])
            cat = str(point_of_interest[poi]["cat"])
            poi_items_list = poi_id +"("+ cat +")"
            node_tied_to_poi["s_link"] =  [poi_items_list]

          else:

            poi_id = str(point_of_interest[poi]["id"])
            cat = str(point_of_interest[poi]["cat"])
            poi_items_list = poi_id +"("+ cat +")"
            node_tied_to_poi["s_link"] =  [poi_items_list]

          new_node_tied_to_poi = {"key_id":key_id, "tied_node":node_tied_to_poi}
          new_node_tied_to_poi_list.append(new_node_tied_to_poi)
         
        else:
          
          for item_s in range (len(new_node_tied_to_poi_list)):
            
            if new_node_tied_to_poi_list[item_s]["key_id"] == key_id:
              
              if "nodes" in point_of_interest[poi]:

                poi_id = str(point_of_interest[poi]["nodes"]["id"])
                cat = str(point_of_interest[poi]["cat"])
                poi_items_list = poi_id +"("+ cat +")"
                
              else:
                poi_id = str(point_of_interest[poi]["id"])
                cat = str(point_of_interest[poi]["cat"])
                poi_items_list = poi_id +"("+ cat +")"
            
              existing_poi = new_node_tied_to_poi_list[item_s]["tied_node"]["s_link"]
              new_poi = [poi_items_list]
              merged_poi = existing_poi + new_poi
              node_tied_to_poi["s_link"] = merged_poi
              
              if new_node_tied_to_poi_list[item_s]["key_id"] == key_id:
                new_node_tied_to_poi_list[item_s]["tied_node"]["s_link"] = node_tied_to_poi["s_link"]


  #match the pois in new_node_tied_to_poi_list to the concerned node in each street
  for obj in range(len(new_node_tied_to_poi_list)):
    key_idd = new_node_tied_to_poi_list[obj]["key_id"]
    
    for objs in range (len(street_data_cpyy)):
      nodes = street_data_cpyy[objs]["nodes"]
      
      for node in range (len(nodes)):
        
        if nodes[node]["id"] == key_idd:
          nodes[node] = new_node_tied_to_poi_list[obj]["tied_node"]
    
  return (street_data_cpyy)


