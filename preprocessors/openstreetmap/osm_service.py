import overpy
from copy import deepcopy
import haversine as hs
from math import radians, degrees, cos
from datetime import datetime
from flask import jsonify
import jsonschema
import logging
from overpy.exception import (
    OverpassTooManyRequests,
    OverpassGatewayTimeout,
    OverpassRuntimeError,
)


def create_bbox_coordinates(distance, lat, lon):
    assert distance > 0
    assert lat >= -90.0 and lat <= 90.0
    assert lon >= -180.0 and lon <= 180.0
    distance_in_km = distance * 0.001
    """ convert lat/lon from degrees to radians """
    lat, lon = radians(lat), radians(lon)
    radius = 6371
    """ Radius of the earth in km """
    parallel_radius = radius * cos(lat)
    """ Radius of the parallel at given latitude """
    lat_min = lat - distance_in_km / radius
    lat_max = lat + distance_in_km / radius
    lon_min = lon - distance_in_km / parallel_radius
    lon_max = lon + distance_in_km / parallel_radius
    """ Convert lat/lon from radians back to degrees """
    lat_min, lon_min = degrees(lat_min), degrees(lon_min)
    lat_max, lon_max = degrees(lat_max), degrees(lon_max)
    bbox_coordinates = [lat_min, lon_min, lat_max, lon_max]
    return bbox_coordinates


def get_streets(bbox_coord):
    lat_min, lon_min = bbox_coord[0], bbox_coord[1]
    lat_max, lon_max = bbox_coord[2], bbox_coord[3]
    """ fetch all ways and nodes """
    try:
        api = overpy.Overpass(
            url="https://pegasus.cim.mcgill.ca/overpass/api/interpreter?")
        OSM_data = api.query(
            f"""
        way({lat_min},{lon_min},{lat_max},{lon_max})[highway~"^(primary|tertiary|secondary|track|path|living_street|service|crossing|pedestrian|residential|footway)$"];
        (._;>;);
        out body;
        """
        )
    except OverpassGatewayTimeout:
        error = 'Overpass GatewayTimeout: High server load. Retry again'
        logging.error(error)
    except OverpassTooManyRequests:
        error = 'Overpass Too many requests. Retry again'
        logging.error(error)
    except OverpassRuntimeError:
        error = 'Overpass Runtime error. Retry again'
        logging.error(error)
    except Exception:
        error = 'Overpass Attibute error. Retry again'
        logging.error(error)
    else:
        return (OSM_data)


def get_timestamp():
    d = datetime.now()
    timestamp = int(datetime.timestamp(d))
    return timestamp


def process_streets_data(OSM_data):
    """Retrieve inteterested street information from the requested OSM data"""
    try:
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
            # Convert lanes to integer if its value is not None
            lanes = way.tags.get("lanes")
            if lanes is not None:
                lanes = int(lanes)
            else:
                lanes = lanes
            # Convert oneway tag to boolean if its value is not None
            oneway = way.tags.get("oneway")
            if oneway is not None:
                oneway = bool(oneway)
            else:
                oneway = oneway
                way_object = {
                    "street_id": int(way.id),
                    "street_name": way.tags.get("name"),
                    "street_type": way.tags.get("highway"),
                    "addr:street": way.tags.get("addr:street"),
                    "surface": way.tags.get("surface"),
                    "oneway": oneway,
                    "sidewalk": way.tags.get("sidewalk"),
                    "maxspeed": way.tags.get("maxspeed"),
                    "lanes": lanes,
                    "nodes": node_list,
                }
                # Delete key if value is empty
                way_object = dict(x for x in way_object.items() if all(x))
                processed_OSM_data.append(way_object)
    except AttributeError:
        error = 'Overpass Attibute error. Retry again'
        logging.error(error)
    else:
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
                if "street_name" in processed_OSM_data[i]:
                    street_object = {
                        "street_id": processed_OSM_data[i]["street_id"],
                        "street_name": processed_OSM_data[i]["street_name"],
                        "intersection_nodes": intersecting_points,
                    }
                elif "street_type" in processed_OSM_data[i]:
                    street_object = {
                        "street_id": processed_OSM_data[i]["street_id"],
                        "street_type": processed_OSM_data[i]["street_type"],
                        "intersection_nodes": intersecting_points,
                    }
                else:
                    street_object = {
                        "street_id": processed_OSM_data[i]["street_id"],
                        "intersection_nodes": intersecting_points,
                    }
                intersection_record.append(street_object)
                if "street_name" in processed_OSM_data[j]:
                    street_object = {
                        "street_id": processed_OSM_data[j]["street_id"],
                        "street_name": processed_OSM_data[j]["street_name"],
                        "intersection_nodes": intersecting_points,
                    }
                elif "street_type" in processed_OSM_data[i]:
                    street_object = {
                        "street_id": processed_OSM_data[i]["street_id"],
                        "street_type": processed_OSM_data[i]["street_type"],
                        "intersection_nodes": intersecting_points,
                    }
                else:
                    street_object = {
                        "street_id": processed_OSM_data[j]["street_id"],
                        "intersection_nodes": intersecting_points,
                    }
                intersection_record.append(street_object)
    # Group the streets by their ids
    output = {}
    for obj in intersection_record:
        street_id = obj["street_id"]
        if street_id not in output:
            assert obj["intersection_nodes"] is not None
            if "street_name" in obj:
                record = {
                    "street_id": obj["street_id"],
                    "street_name": obj["street_name"],
                    "intersection_nodes": obj["intersection_nodes"],
                }
            elif "street_type" in obj:
                record = {
                    "street_id": obj["street_id"],
                    "street_type": obj["street_type"],
                    "intersection_nodes": obj["intersection_nodes"],
                }
            else:
                record = {
                    "street_id": obj["street_id"],
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
    # Keep a unique set of intersections under each street segment
    for obj in range(len(intersection_record_updated)):
        unique_set = []
        inter_sets = intersection_record_updated[obj]["intersection_nodes"]
        unique_set = [item for item in inter_sets if item not in unique_set]
        # for item in range(len(inter_sets)):
        # if inter_sets[item] not in unique_set:
        # unique_set.append(inter_sets[item])
        intersection_record_updated[obj]["intersection_nodes"] = unique_set
    return (intersection_record_updated)


def allot_intersection(processed_OSM_data, inters_rec_up
                       ):  # iterate & indicate common nodes
    processed_OSM_data1 = deepcopy(processed_OSM_data)
    inters = inters_rec_up
    for obj in range(len(processed_OSM_data1)):
        id1 = processed_OSM_data1[obj]["street_id"]
        nodes = processed_OSM_data1[obj]["nodes"]
        for i in range(len(nodes)):
            for objs in range(len(inters)):
                id2 = inters[objs]["street_id"]
                intersection_nodes = inters[objs]["intersection_nodes"]
                for items in range(len(intersection_nodes)):
                    if id1 != id2:  # compare unique street only
                        # check if a node represents an intersection
                        if nodes[i] == intersection_nodes[items]:
                            nodes[i]["cat"] = "intersection"
                            f = nodes[i]
                            key1 = "street_name"
                            key2 = "street_type"
                            X = processed_OSM_data1[obj]
                            Y = inters[objs]
                            # Check if street_name key is empty or not to
                            # format the output
                            if key1 in X and key1 in Y:
                                nm1 = X["street_name"]
                                nm2 = Y["street_name"]
                                f["name"] = f"{nm1} intersecting {nm2}"
                            elif key1 not in X and key1 in Y:
                                nm2 = Y["street_name"]
                                if key2 in X:  # Use street type if noname
                                    stp = X["street_type"]
                                    f["name"] = f"{stp} intersecting {nm2}"
                                else:
                                    f["name"] = f"{id1} intersecting {nm2}"
                            elif key1 in X and key1 not in Y:
                                nm1 = X["street_name"]
                                if key2 in Y:  # Use street type if noname
                                    stp = Y["street_type"]
                                    f["name"] = f"{nm1} intersecting {stp}"
                                else:
                                    f["name"] = f"{nm1} intersecting {id2}"
                            else:
                                if key2 in X and key2 in Y:
                                    stp1 = X["street_type"]
                                    stp2 = Y["street_type"]
                                    f["name"] = f"{stp1} intersecting {stp2}"
                                else:
                                    f["name"] = f"{id1} intersecting {id2}"
    return processed_OSM_data1


def get_amenities(bbox_coord):
    # Send request to OSM to get amenities which are part of
    # points of interest (POIs)
    api = overpy.Overpass(
        url="https://pegasus.cim.mcgill.ca/overpass/api/interpreter?")
    lat_min, lon_min = bbox_coord[0], bbox_coord[1]
    lat_max, lon_max = bbox_coord[2], bbox_coord[3]
    try:
        amenities = api.query(
            f"""
        (node({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
        way({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
        rel({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
        );
        out center;
        """
        )
    except OverpassGatewayTimeout:
        error = 'Overpas GatewayTimeout: High server load. Retry again'
        logging.error(error)
    except OverpassTooManyRequests:
        error = 'Overpass Too many requests. Retry again'
        logging.error(error)
    except OverpassRuntimeError:
        error = 'Overpass Runtime error. Retry again'
        logging.error(error)
    except Exception:
        error = 'Overpass Attibute error. Retry again'
        logging.error(error)
    else:
        # Filter the amenity tags to the basic useful ones
        amenity = []
        if amenities.nodes:
            for node in amenities.nodes:
                if node.tags.get("amenity") is not None:
                    amenity_record = {
                        "id": int(node.id),
                        "lat": float(node.lat),
                        "lon": float(node.lon),
                        "name": node.tags.get("name"),
                        "cat": node.tags.get("amenity"),
                    }
                    # Fetch as many tags possible

                    for key, value in node.tags.items():
                        if value != node.tags.get(
                                "name") and value != node.tags.get("amenity"):
                            if key not in amenity_record:
                                amenity_record[key] = value

                # Delete keys with no value
                amenity_record = dict(
                    x for x in amenity_record.items() if all(x))
                amenity.append(amenity_record)

        if amenities.ways:
            for way in amenities.ways:
                if way.tags.get("amenity") is not None:
                    amenity_record = {
                        "id": int(way.id),
                        "lat": float(way.center_lat),
                        "lon": float(way.center_lon),
                        "name": way.tags.get("name"),
                        "cat": way.tags.get("amenity"),
                    }
                    # Fetch as many tags possible
                    for key, value in way.tags.items():
                        if value != way.tags.get(
                                "name") and value != way.tags.get("amenity"):
                            if key not in amenity_record:
                                amenity_record[key] = value
                # Delete keys with no value
                amenity_record = dict(
                    x for x in amenity_record.items() if all(x))
                amenity.append(amenity_record)
        if amenities.relations:
            for rel in amenities.relations:
                if rel.tags.get("amenity") is not None:
                    amenity_record = {
                        "id": int(rel.id),
                        "lat": float(rel.center_lat),
                        "lon": float(rel.center_lon),
                        "name": rel.tags.get("name"),
                        "cat": rel.tags.get("amenity"),
                    }
                    # Fetch as many tags possible
                    for key, value in rel.tags.items():
                        if value != rel.tags.get(
                                "name") and value != rel.tags.get("amenity"):
                            if key not in amenity_record:
                                amenity_record[key] = value
                # Delete keys with no value
                amenity_record = dict(
                    x for x in amenity_record.items() if all(x))
                amenity.append(amenity_record)
        return amenity


def enlist_POIs(processed_OSM_data1, amenity):
    # Keep all identified points of interest in a single list
    POIs = []
    if len(processed_OSM_data1):
        for obj in range(len(processed_OSM_data1)):
            nodes = processed_OSM_data1[obj]["nodes"]
            for node in range(len(nodes)):
                key_to_check = "cat"
                # check if "cat" key is in the node
                if key_to_check in nodes[node]:
                    if nodes[node]["cat"]:  # ensure the "cat" key has a value
                        POIs.append(nodes[node])
    if amenity is not None and len(amenity) != 0:
        # POIs = [objs for objs in amenity]
        for objs in range(len(amenity)):
            POIs.append(amenity[objs])
    return POIs  # POIs is a list of all points of interest


def OSM_preprocessor(processed_OSM_data, POIs, amenity):
    id_list, node_list, POI_id_list = [], [], []
    processed_OSM_data2 = deepcopy(processed_OSM_data)
    if len(POIs):
        # Iterate through the amenities
        for i in range(len(
                POIs)):
            key_to_check = POIs[i]["cat"]
            # check if true, then the points of interest are amenity,
            # e.g. restaurants, bars, rentals, etc
            if key_to_check != "intersection" and amenity is not None:
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
                            if nodes[node]["id"] not in id_list:  # id_list
                                # stores all the node ids using the POIs
                                id_list.append(nodes[node]["id"])
                                nodes[node]["POIs_ID"] = [
                                    POIs[i]["id"]]  # New key-pair in the node
                                # node_list keeps all the nodes using POIs
                                node_list.append(nodes[node])
                                # POI_list keeps all the POI ids
                                POI_id_list.append(POIs[i]["id"])
                            else:
                                for n in range(len(node_list)):
                                    # identify the node in the list by using
                                    # its id
                                    if nodes[node]["id"] == node_list[n]["id"]:
                                        # Existing amenity/POI's id(s)
                                        existingid = node_list[n]["POIs_ID"]
                                        # An id for new POI
                                        new_id = POIs[i]["id"]
                                        # Ensure new id is not in the existing
                                        # id
                                        if new_id not in POI_id_list:
                                            POI_id_list.append(new_id)
                                            # Two id's merged into a single
                                            # list
                                            merged_id = existingid + [new_id]
                                            nodes[node]["POIs_ID"] = merged_id
                                        else:
                                            nodes[node]["POIs_ID"] = existingid
            else:  # POIs here are intersections
                for objs in range(len(processed_OSM_data2)):
                    nodes = processed_OSM_data2[objs]["nodes"]
                    for node in range(len(nodes)):
                        # check if node is among the points of interest list
                        if nodes[node]["id"] == POIs[i]["id"]:
                            # check if this node has not been used by any POIs
                            if nodes[node]["id"] not in id_list:
                                # id_list stores all the node ids using the
                                # POIs
                                id_list.append(nodes[node]["id"])
                                # create a new key-pair in the node
                                nodes[node]["POIs_ID"] = [nodes[node]["id"]]
                                # node_list keeps all the nodes using POIs
                                node_list.append(nodes[node])
                                # POI_list keeps all the POIs ids
                                POI_id_list.append(nodes[node]["id"])
                            else:
                                for n in range(len(node_list)):
                                    if nodes[node]["id"] == node_list[n]["id"]:
                                        existingid = node_list[n]["POIs_ID"]
                                        # node id for intersection (POI)
                                        new_id = nodes[node]["id"]
                                        # Ensure new id is not in the existing
                                        # id
                                        if new_id not in POI_id_list:
                                            POI_id_list.append(new_id)
                                            # Two id's merged into a single
                                            # list
                                            merged_id = existingid + [new_id]
                                            nodes[node]["POIs_iD"] = merged_id
                                        else:
                                            nodes[node]["POIs_ID"] = existingid

    # Arrange street segments in order of lengths (descending order)
    for i in range(len(processed_OSM_data2)):
        j = i + 1
        for j in range(len(processed_OSM_data2)):
            # Use the size of their nodes to rank them
            nodes1 = len(processed_OSM_data2[i]["nodes"])
            nodes2 = len(processed_OSM_data2[j]["nodes"])
            if nodes1 > nodes2:
                street = processed_OSM_data2[i]
                processed_OSM_data2[i] = processed_OSM_data2[j]
                processed_OSM_data2[j] = street
    return processed_OSM_data2


def validate(schema, data, resolver, json_message, error_code):
    """
    Validate a piece of data against a schema
    Args:
        schema: a JSON schema to check against
        data: the data to check
        resolver: a JSON schema resolver
        json_messaage: the error to jsonify and return
        error_code: the error code to return
    Returns:
        None or Tuple[flask.Response, int]
    """
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as error:
        logging.error(error)
        return jsonify(json_message), error_code
    return None


def get_coordinates(content):
    """
    Retrieve the coordinates of a map from the
    content of the request
    """
    if 'coordinates' in content.keys():
        return content['coordinates']
