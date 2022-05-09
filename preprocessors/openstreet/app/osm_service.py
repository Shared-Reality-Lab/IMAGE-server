import overpy
from copy import deepcopy
import haversine as hs
import math
from datetime import datetime


def create_bbox_coordinates(distance, lat, lon):
    assert distance > 0
    assert lat >= -90.0 and lat <= 90.0
    assert lon >= -180.0 and lon <= 180.0
    distance_in_km = distance * 0.001
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
    bbox_coordinates = [lat_min, lon_min, lat_max, lon_max]
    return bbox_coordinates


def query_OSMap(bbox_coordinates):
    """Send request to get map data from OSM"""
    lat_min = bbox_coordinates[0]
    lon_min = bbox_coordinates[1]
    lat_max = bbox_coordinates[2]
    lon_max = bbox_coordinates[3]
    """ fetch all ways and nodes """
    api = overpy.Overpass()
    OSM_data = api.query(
        f"""
    way({lat_min},{lon_min},{lat_max},{lon_max})[highway~"^(primary|tertiary|secondary|track|path|crossing|pedestrian|living_street|residential|service|footway)$"];
    (._;>;);
    out body;
    """
    )
    return (OSM_data)


def get_timestamp():
    d = datetime.now()
    timestamp = int(datetime.timestamp(d))

    return timestamp


def process_OSMap_data(OSM_data):
    """Retrieve inteterested street information from the requested OSM data"""
    assert OSM_data is not None
    processed_OSM_data = []
    for way in OSM_data.ways:
        node_list = []
        for node in way.nodes:
            node_object = {
                "id": int(node.id),
                "lat": float(node.lat),
                "lon": float(node.lon),
            }
            if node_object not in node_list:
                node_list.append(node_object)
        way_object = {
            "street_id": int(way.id),
            "street_name": way.tags.get("name", "n/a"),
            "street_type": way.tags.get("highway", "n/a"),
            "surface": way.tags.get("surface", "n/a"),
            "oneway": way.tags.get("oneway", "n/a"),
            "sidewalk": way.tags.get("sidewalk", "n/a"),
            "nodes": node_list,
            # "timestamp": way.tags.get("osm_base")
        }
        processed_OSM_data.append(way_object)
    return processed_OSM_data


def compare_street(street1, street2):  # Compare two streets
    intersecting_points = [x for x in street1 if x in street2]
    return intersecting_points


def extract_street(processed_OSM_data):  # extract two streets

    intersection_record = []

    for i in range(len(processed_OSM_data)):
        for j in range(i + 1, len(processed_OSM_data)):
            street1 = processed_OSM_data[i]["nodes"]
            street2 = processed_OSM_data[j]["nodes"]
            intersecting_points = compare_street(
                street1, street2)  # function call
            if len(intersecting_points):  # check if not empty
                street_object = {
                    "street_id": processed_OSM_data[i]["street_id"],
                    "street_name": processed_OSM_data[i]["street_name"],
                    "intersection_nodes": intersecting_points,
                }
                intersection_record.append(street_object)
                street_object = {
                    "street_id": processed_OSM_data[j]["street_id"],
                    "street_name": processed_OSM_data[j]["street_name"],
                    "intersection_nodes": intersecting_points,
                }
                intersection_record.append(street_object)

    # Group the street segment by their ids
    output = {}
    for obj in intersection_record:
        street_id = obj["street_id"]
        if street_id not in output:
            assert obj["intersection_nodes"] is not None
            record = {
                "street_id": obj["street_id"],
                "street_name": obj["street_name"],
                "intersection_nodes": obj["intersection_nodes"],
            }
            output[street_id] = record
        else:
            existing_record = output[street_id]
            existing_intersection_nodes = existing_record["intersection_nodes"]
            assert existing_intersection_nodes is not None
            new_intersection_nodes = obj["intersection_nodes"]
            q = new_intersection_nodes
            assert q is not None
            merged_intersection_nodes = existing_intersection_nodes + q
            existing_record["intersection_nodes"] = merged_intersection_nodes
            output[street_id] = existing_record
    intersection_record_updated = list(output.values())
    # Keep a unique set of intersections under each street segment (i.e.
    # street id)
    for obj in range(len(intersection_record_updated)):
        unique_set = []
        inter_sets = intersection_record_updated[obj]["intersection_nodes"]
        for item in range(len(inter_sets)):
            if inter_sets[item] not in unique_set:
                unique_set.append(inter_sets[item])
        intersection_record_updated[obj]["intersection_nodes"] = unique_set
    return (intersection_record_updated)


def allot_intersection(processed_OSM_data, inters_rec_up
                       ):  # iterate & indicate common nodes
    processed_OSM_data1 = deepcopy(processed_OSM_data)
    inters = inters_rec_up
    for obj in range(len(processed_OSM_data1)):
        name1 = processed_OSM_data1[obj]["street_name"]
        id1 = processed_OSM_data1[obj]["street_id"]
        nodes = processed_OSM_data1[obj]["nodes"]
        for i in range(len(nodes)):
            for objs in range(len(inters)):
                name2 = inters[objs]["street_name"]
                id2 = inters[objs]["street_id"]
                intersection_nodes = inters[objs]["intersection_nodes"]
                for items in range(len(intersection_nodes)):
                    if id1 != id2:  # compare unique street segment only

                        # check if a node represents an intersection
                        if nodes[i] == intersection_nodes[items]:
                            nodes[i]["cat"] = "intersection"
                            f = nodes[i]
                            f["name"] = f"{name1}{id1} intersects {name2}{id2}"

    return processed_OSM_data1


def get_amenities(bbox_coordinates):
    # Send request OSM to get amenities which are part of point of interest
    # (POIs)
    api = overpy.Overpass()
    lat_min = bbox_coordinates[0]
    lon_min = bbox_coordinates[1]
    lat_max = bbox_coordinates[2]
    lon_max = bbox_coordinates[3]
    amenities = api.query(
        f"""
    node({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
    (._;>;);
    out body;
    """
    )
    # Filter the amenity data from OSM to have only the basic tag info
    amenity = []
    for node in amenities.nodes:
        if node.tags.get("amenity") is not None:
            amenity_record = {
                "id": int(node.id),
                "lat": float(node.lat),
                "lon": float(node.lon),
                "name": node.tags.get("name"),
                "cat": node.tags.get("amenity"),
            }
            amenity.append(amenity_record)
    return amenity


def enlist_POIs(processed_OSM_data1, amenity):
    # Keep all identified points of interest in a single list
    POIs = []
    for obj in range(len(processed_OSM_data1)):
        nodes = processed_OSM_data1[obj]["nodes"]
        for node in range(len(nodes)):
            key_to_check = "cat"
            # check if "cat" key is in the node
            if key_to_check in nodes[node]:
                if nodes[node]["cat"]:  # ensure the "cat" key has a value
                    POIs.append(nodes[node])
    for objs in range(len(amenity)):
        POIs.append(amenity[objs])
    return POIs  # POIs is a list of all point of interest


def OSM_preprocessor(processed_OSM_data, POIs):
    id_list = []
    node_list = []
    POI_id_list = []
    processed_OSM_data2 = deepcopy(processed_OSM_data)
    assert POIs is not None
    # Iterate through the amenities
    for i in range(len(
            POIs)):
        key_to_check = POIs[i]["cat"]
        # check if true, then the point of interests are amenity,
        # e.g. restaurants, bars, rentals, etc
        if key_to_check != "intersection":
            minimum_distance = []
            for obj in range(len(processed_OSM_data)):
                nodes = processed_OSM_data[obj]["nodes"]
                for j in range(len(nodes)):
                    lat1 = nodes[j]["lat"]
                    lon1 = nodes[j]["lon"]
                    lat2 = POIs[i]["lat"]
                    lon2 = POIs[i]["lon"]
                    location1 = (float(lat1), float(lon1))
                    location2 = (float(lat2), float(lon2))
                    # Compute the distance between a node and POI
                    distance = hs.haversine(location1, location2)
                    if (len(minimum_distance)) == 0:
                        minimum_distance.append(distance)
                        k = processed_OSM_data2[obj]["nodes"]
                        reference_id = {
                            "node_id": k[j]["id"], }
                    else:
                        if distance < minimum_distance[0]:
                            minimum_distance[0] = distance
                            k = processed_OSM_data2[obj]["nodes"]
                            reference_id = {
                                "node_id": k[j]["id"], }

            # iterate through the OSM data
            # to reference the node that should
            # hold the point of interest

            for objs in range(len(processed_OSM_data2)):
                nodes = processed_OSM_data2[objs]["nodes"]
                for node in range(len(nodes)):  # if true,
                    # the node will hold the point of interest

                    if nodes[node]["id"] == reference_id["node_id"]:
                        if nodes[node]["id"] not in id_list:  # id_list stores
                            # all the node ids using the POIs

                            id_list.append(nodes[node]["id"])

                            nodes[node]["POI_id"] = [
                                POIs[i]["id"]]  # create a key-pair in the node

                            # node_list keeps all the nodes using POIs
                            node_list.append(nodes[node])

                            # POI_list keeps all the POI ids
                            POI_id_list.append(POIs[i]["id"])
                        else:
                            for n in range(len(node_list)):
                                # identify the node in the list by using its id
                                if nodes[node]["id"] == node_list[n]["id"]:

                                    # Existing amenity/POI's id(s)
                                    existing_id = node_list[n]["POI_id"]

                                    # An id for new POI
                                    new_id = POIs[i]["id"]

                                    # Ensure new id is not in the existing id
                                    if new_id not in POI_id_list:

                                        POI_id_list.append(new_id)

                                        # Two id's merged into a single list
                                        merged_id = existing_id + [new_id]
                                        nodes[node]["POI_id"] = merged_id
                                    else:
                                        nodes[node]["POI_id"] = existing_id

        else:  # POIs here are intersections
            for objs in range(len(processed_OSM_data2)):
                nodes = processed_OSM_data2[objs]["nodes"]
                for node in range(len(nodes)):

                    # check if node is among the point of interest list
                    if nodes[node]["id"] == POIs[i]["id"]:

                        # check if this node has not been used by POIs
                        if nodes[node]["id"] not in id_list:

                            # id_list stores all the node ids using the POIs
                            id_list.append(nodes[node]["id"])

                            # create a new key-pair in the node
                            nodes[node]["POI_id"] = [nodes[node]["id"]]

                            # node_list keeps all the nodes using POIs
                            node_list.append(nodes[node])

                            # POI_list keeps all the POI ids
                            POI_id_list.append(nodes[node]["id"])
                        else:
                            for n in range(len(node_list)):

                                if nodes[node]["id"] == node_list[n]["id"]:
                                    existing_id = node_list[n]["POI_id"]

                                    # node id for intersection (POI)
                                    new_id = nodes[node]["id"]

                                    # Ensure new id is not in the existing id
                                    if new_id not in POI_id_list:
                                        POI_id_list.append(new_id)

                                        # Two id's merged into a single list
                                        merged_id = existing_id + [new_id]
                                        nodes[node]["POI_id"] = merged_id
                                    else:
                                        nodes[node]["POI_id"] = existing_id
    return processed_OSM_data2
