from typing import List
import overpy
import json
from copy import deepcopy
import haversine as hs
import random
import math


def compute_query_bounding_box(distance_in_metres: float, lat: float, lon: float):

    assert distance_in_metres > 0
    assert lat >= -90.0 and lat <= 90.0
    assert lon >= -180.0 and lon <= 180.0
    distance_in_km = distance_in_metres * 0.001
    """ convert lat/lon from degrees to radians """
    lat = math.radians(lat)
    lon = math.radians(lon)

    radius = 6371
    """ Radius of the earth in km """
    parallel_radius = radius * math.cos(lat)
    """ Radius of the parallel at given latitude """
    lat_min = lat - distance_in_km / radius
    lat_max = lat + distance_in_km / radius
    lon_min = lon - distance_in_km / parallel_radius
    lon_max = lon + distance_in_km / parallel_radius

    """ Convert lat/lon from radians back to degrees """
    lat_min = math.degrees(lat_min)
    lon_min = math.degrees(lon_min)
    lat_max = math.degrees(lat_max)
    lon_max = math.degrees(lon_max)
    coordinates = [lat_min, lon_min, lat_max, lon_max]

    return coordinates


def query_osmdata(coordinates):
    """Send request to get map data from OSM"""
    lat_min = coordinates[0]
    lon_min = coordinates[1]
    lat_max = coordinates[2]
    lon_max = coordinates[3]

    """ fetch all ways and nodes """
    api = overpy.Overpass()
    queried_osm_data = api.query(
        f"""
    way({lat_min},{lon_min},{lat_max},{lon_max}) [highway~"^(primary|tertiary|residential|service|footway)$"];
    (._;>;);
    out body;
    """
    )
    bbox = [lat_min, lon_min, lat_max, lon_max]

    return (queried_osm_data, bbox)


def transform_osmdata(raw_osmdata: List[dict]):
    """Retrieve inteterested street information from the requested OSM data"""
    assert raw_osmdata is not None
    street_data_list = []
    for way in raw_osmdata.ways:
        nodes_list = []
        for node in way.nodes:
            node_record = {
                "id": str(node.id),
                "lat": str(node.lat),
                "lon": str(node.lon),
            }
            if node_record not in nodes_list:
                nodes_list.append(node_record)
                way_record = {
                    "street_id": str(way.id),
                    "street_name": way.tags.get("name", "n/a"),
                    "street_type": way.tags.get("highway", "n/a"),
                    "surface": way.tags.get("surface", "n/a"),
                    "oneway": way.tags.get("oneway", "n/a"),
                    "sidewalk": way.tags.get("sidewalk", "n/a"),
                    "nodes": nodes_list,
                }
                street_data_list.append(way_record)

                transformed_osm_data = []
                for obj in street_data_list:
                    """Remove duplicate objects if any"""
                    if obj not in transformed_osm_data:
                        transformed_osm_data.append(obj)
    return transformed_osm_data


def merge_street_by_name(transformed_osm_data: List[dict]):
    """Group all street information on street name to achieve street by street record"""
    output = {}
    for obj in transformed_osm_data:
        street_name = obj["street_name"]
        if street_name not in output:
            assert obj["nodes"] is not None
            record = {
                "street_id": obj["street_id"],
                "street_name": obj["street_name"],
                "nodes": obj["nodes"],
            }
            output[street_name] = record
        else:
            existing_record = output[street_name]
            existing_nodes = existing_record["nodes"]
            assert existing_nodes is not None
            new_node = obj["nodes"]
            assert new_node is not None
            merged_node = existing_nodes + new_node
            existing_record["nodes"] = merged_node
            output[street_name] = existing_record
        merged_street = list(output.values())

        for objs in range(len(merged_street)):
            """Clean nodes to remove duplicated nodes in any given street"""
            unique_nodes = []
            nodes = merged_street[objs]["nodes"]
            for node in range(len(nodes)):
                if nodes[node] not in unique_nodes:
                    unique_nodes.append(nodes[node])
                    merged_street[objs]["nodes"] = unique_nodes
    return merged_street


def extract_intersection(list1, list2):
    """Compare two streets for possible intersection"""
    computed_intersection = [x for x in list1 if x in list2]
    return computed_intersection


def extract_nodes_list(merged_street):
    """The function uses loop to extract sets of points (nodes) for any two streets and send out for possible intersection and so on
    street_intersection_sets contains the same information as intersection_sets except that the former contains more tags"""
    intersection_sets = []
    street_intersection_sets = []
    for i in range(len(merged_street)):
        for j in range(i + 1, len(merged_street)):
            list1 = merged_street[i]["nodes"]
            list2 = merged_street[j]["nodes"]
            intersection = extract_intersection(list1, list2)
            if len(intersection):
                street_record = {
                    "street_name": merged_street[i]["street_name"],
                    "intersection_sets": intersection,
                }
                street_intersection_sets.append(street_record)

                street_record = {
                    "street_name": merged_street[j]["street_name"],
                    "intersection_sets": intersection,
                }
                street_intersection_sets.append(street_record)
                intersection_sets.append(intersection)
    return (intersection_sets, street_intersection_sets)


def merge_street_intersection_by_name(street_intersection_sets):
    """Creata a function to group street intersections by their respective street names"""
    output = {}
    for obj in street_intersection_sets:
        street_name = obj["street_name"]
        if street_name not in output:
            assert obj["intersection_sets"] is not None
            record = {
                "street_name": obj["street_name"],
                "intersection_sets": obj["intersection_sets"],
            }
            output[street_name] = record
        else:
            existing_record = output[street_name]
            existing_intersection = existing_record["intersection_sets"]
            assert existing_intersection is not None
            new_intersection = obj["intersection_sets"]
            assert new_intersection is not None
            merged_intersection = existing_intersection + new_intersection
            existing_record["intersection_sets"] = merged_intersection
            output[street_name] = existing_record
    merged_intersection = list(output.values())
    return merged_intersection


def create_new_intersection_sets(result):
    """Create a new single list of intersection objects [{},{},{}...]"""
    modified_intersection_sets = []
    for intersect_list in result:
        for obj in intersect_list:
            modified_intersection_sets.append(obj)
    return modified_intersection_sets


def my_final_data_structure(
    copy_of_merged_street, modified_intersection_set, merged_intersection
):
    """# Loop through all the nodes across the ways and indicate if a node is an intersection or not. It
    also indicates what street is intersecting with what street.
    This is to fit in to the desired structure in mind"""
    street_records = []
    for obj in range(len(copy_of_merged_street)):
        nodes = copy_of_merged_street[obj]["nodes"]
        for i in range(len(nodes)):
            if nodes[i] not in modified_intersection_set:
                alist = []
                node = nodes[i]
                alist.append(node)
                street_info = {
                    "street_name": copy_of_merged_street[obj]["street_name"],
                    "nodes": alist,
                }
                street_records.append(street_info)
            else:
                for ob_items in range(len(merged_intersection)):
                    merged_street_name = copy_of_merged_street[obj]["street_name"]
                    intersected_street_name = merged_intersection[ob_items][
                        "street_name"
                    ]
                    if merged_street_name != intersected_street_name:
                        nod = merged_intersection[ob_items]["intersection_sets"]
                        for n_items in range(len(nod)):
                            if nodes[i] == nod[n_items]:
                                alist = []
                                blist = []
                                node = nodes[i]
                                node["cat"] = "intersection"
                                alist.append(node)
                                node["name"] = (
                                    "intersection "
                                    + merged_street_name
                                    + " and "
                                    + intersected_street_name
                                )
                                blist.append(node)
                                street_info = {
                                    "street_name": copy_of_merged_street[obj][
                                        "street_name"
                                    ],
                                    "nodes": alist,
                                }
                                street_records.append(street_info)
    return street_records


def merge_street_points_by_name(street_records):
    """Sort out the final data structure and group by name"""
    output = {}
    for obj in street_records:
        street_name = obj["street_name"]
        if street_name not in output:
            assert obj["nodes"] is not None
            record = {
                "street_name": obj["street_name"],
                "nodes": obj["nodes"],
            }
            output[street_name] = record

        else:
            existing_record = output[street_name]
            existing_node = existing_record["nodes"]
            assert existing_node is not None
            new_node = obj["nodes"]
            assert new_node is not None
            merged_node = existing_node + new_node
            existing_record["nodes"] = merged_node
            output[street_name] = existing_record
    merged_street_data = list(output.values())
    return merged_street_data


def get_amenities(coordinates):
    """Send request OSM to get amenities which are part of point of interest (POIs)"""

    api = overpy.Overpass()
    lat_min = coordinates[0]
    lon_min = coordinates[1]
    lat_max = coordinates[2]
    lon_max = coordinates[3]

    amenities = api.query(
        f"""
    node({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
    (._;>;);
    out body;
    """
    )

    return amenities


def process_extracted_amenities(amenities):
    """Process to retrieve POIs tags of interest such as restaurants, etc. but excluding intersections"""
    processed_amenities = []
    for node in amenities.nodes:
        if node.tags.get("amenity") is not None:
            amenity_record = {
                "id": str(node.id),
                "lat": str(node.lat),
                "lon": str(node.lon),
                "name": node.tags.get("name"),
                "cat": node.tags.get("amenity"),
            }
            processed_amenities.append(amenity_record)
    return processed_amenities


def align_points_of_interest(processed_amenities, merged_street_data):
    """Match/connect POIs which include all amenities in "processed_amenities"
    and all intersections in "merged_street_data" to the streets"""

    copy_of_merged_street_data = deepcopy(merged_street_data)
    for amenity in range(len(processed_amenities)):
        distance_list = []
        street_data = merged_street_data
        for obj in range(len(street_data)):
            nodes = street_data[obj]["nodes"]
            for node_items in range(len(nodes)):
                lat1 = nodes[node_items]["lat"]
                lon1 = nodes[node_items]["lon"]
                lat2 = processed_amenities[amenity]["lat"]
                lon2 = processed_amenities[amenity]["lon"]
                location1 = (float(lat1), float(lon1))
                location2 = (float(lat2), float(lon2))
                distance = hs.haversine(location1, location2)
                if (len(distance_list)) == 0:
                    distance_list.append(distance)

                    street_record = {
                        "street_name": street_data[obj]["street_name"],
                        "poi": processed_amenities[amenity],
                        "node_index": node_items + 1,
                    }
                else:
                    if distance < distance_list[0]:
                        distance_list[0] = distance

                        street_record = {
                            "street_name": street_data[obj]["street_name"],
                            "poi": processed_amenities[amenity],
                            "node_index": node_items + 1,
                        }

        for str_obj in range(len(copy_of_merged_street_data)):
            if (
                copy_of_merged_street_data[str_obj]["street_name"]
                == street_record["street_name"]
            ):
                nodes = copy_of_merged_street_data[str_obj]["nodes"]
                nodes.insert(street_record["node_index"], street_record["poi"])
    return copy_of_merged_street_data


def retrieve_all_point_of_interest(copy_of_merged_street_data):
    """retrieve only all points of interest (pois) including intersections, restaurants, etc. from all the streets"""
    retrieved_point_of_interest = deepcopy(copy_of_merged_street_data)
    for obj in range(len(retrieved_point_of_interest)):
        nodes = retrieved_point_of_interest[obj]["nodes"]
        poi_collection = []
        for node in range(len(nodes)):
            key_to_check = "cat"
            if key_to_check in nodes[node]:
                if nodes[node]["cat"]:
                    poi_collection.append(nodes[node])
        retrieved_point_of_interest[obj]["nodes"] = poi_collection
        retrieved_point_of_interest[obj]["pois"] = retrieved_point_of_interest[obj].pop(
            "nodes"
        )
    return retrieved_point_of_interest


def keep_in_list_all_retrieved_point_of_interest(retrieved_point_of_interest):
    """Keep all points of interest from all the streets together in a single list"""
    listed_point_of_interest = []
    id_record = []
    unique_listed_point_of_interest = []
    for obj in range(len(retrieved_point_of_interest)):
        pois = retrieved_point_of_interest[obj]["pois"]
        for poi in range(len(pois)):
            listed_point_of_interest.append(pois[poi])

    for unique_obj in range(len(listed_point_of_interest)):
        """Remove duplicated point of interest"""
        key_to_check = "nodes"

        if key_to_check in listed_point_of_interest[unique_obj]:
            if listed_point_of_interest[unique_obj]["nodes"]["id"] not in id_record:
                unique_listed_point_of_interest.append(
                    listed_point_of_interest[unique_obj]
                )
                id_record.append(listed_point_of_interest[unique_obj]["nodes"]["id"])

        else:

            if listed_point_of_interest[unique_obj]["id"] not in id_record:
                unique_listed_point_of_interest.append(
                    listed_point_of_interest[unique_obj]
                )
                id_record.append(listed_point_of_interest[unique_obj]["id"])

    return (unique_listed_point_of_interest, listed_point_of_interest)


def final_osm_data_format(all_pois_merged_list, merged_street):
    """FORMAT:........First collect all points of all categories (inter_section, restaurant, fast_food, etc) in an array
    and align them to the respective adjacent nodes"""

    point_of_interest = all_pois_merged_list

    id_list = []
    new_node_tied_to_poi_list = []
    first_copy_of_street_data = deepcopy(merged_street)

    for poi in range(len(all_pois_merged_list)):
        distance_list = []
        poi_list = []

        street_data = merged_street

        for obj in range(len(street_data)):
            nodes = street_data[obj]["nodes"]

            for node_items in range(len(nodes)):
                lat1 = nodes[node_items]["lat"]
                lon1 = nodes[node_items]["lon"]
                lat2 = point_of_interest[poi]["lat"]
                lon2 = point_of_interest[poi]["lon"]
                location1 = (float(lat1), float(lon1))
                location2 = (float(lat2), float(lon2))
                distance = hs.haversine(location1, location2)

                if (len(distance_list)) == 0:
                    distance_list.append(distance)
                    poi_list.append(point_of_interest[poi])

                    street_record = {
                        "street_name": street_data[obj]["street_name"],
                        "poi": all_pois_merged_list[poi],
                        "node_index": node_items,
                        "poi_list": poi_list,
                    }
                else:

                    if distance < distance_list[0]:
                        distance_list[0] = distance

                        street_record = {
                            "street_name": street_data[obj]["street_name"],
                            "poi": all_pois_merged_list[poi],
                            "node_index": node_items,
                            "poi_list": poi_list,
                        }

        second_copy_of_street_data = deepcopy(first_copy_of_street_data)

        for street_object in range(len(second_copy_of_street_data)):
            """Merge pois when we have multiple pois competeting for a node and assign it to key called s_link"""

            if (
                second_copy_of_street_data[street_object]["street_name"]
                == street_record["street_name"]
            ):

                index = street_record["node_index"]
                node_tied_to_poi = second_copy_of_street_data[street_object]["nodes"][
                    index
                ]
                key_id = node_tied_to_poi["id"]

                if key_id not in id_list:
                    id_list.append(key_id)
                    poi_id = str(all_pois_merged_list[poi]["id"])
                    poi_items_list = poi_id
                    node_tied_to_poi["s_link"] = [poi_items_list]

                    new_node_tied_to_poi = {
                        "key_id": key_id,
                        "tied_node": node_tied_to_poi,
                    }
                    new_node_tied_to_poi_list.append(new_node_tied_to_poi)

                else:

                    for item_s in range(len(new_node_tied_to_poi_list)):

                        if new_node_tied_to_poi_list[item_s]["key_id"] == key_id:

                            poi_id = str(all_pois_merged_list[poi]["id"])
                            poi_items_list = poi_id
                            existing_poi = new_node_tied_to_poi_list[item_s][
                                "tied_node"
                            ]["s_link"]
                            new_poi = [poi_items_list]
                            merged_poi = existing_poi + new_poi
                            node_tied_to_poi["s_link"] = merged_poi

                            if new_node_tied_to_poi_list[item_s]["key_id"] == key_id:
                                new_node_tied_to_poi_list[item_s]["tied_node"][
                                    "s_link"
                                ] = node_tied_to_poi["s_link"]

    for obj in range(len(new_node_tied_to_poi_list)):
        """Match the pois in new_node_tied_to_poi_list to the concerned node in each street"""
        key_idd = new_node_tied_to_poi_list[obj]["key_id"]

        for objs in range(len(second_copy_of_street_data)):
            nodes = second_copy_of_street_data[objs]["nodes"]

            for node in range(len(nodes)):

                if nodes[node]["id"] == key_idd:
                    nodes[node] = new_node_tied_to_poi_list[obj]["tied_node"]

    return second_copy_of_street_data
