import overpy
from copy import deepcopy
import haversine as hs
from math import radians, degrees, cos
from datetime import datetime
from flask import jsonify
import jsonschema
import logging
import math
import os
import requests
from osm_config import defaultServer, secondaryServer1, secondaryServer2
from geographiclib.geodesic import Geodesic
import traceback


# Configure logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%y-%m-%d %H:%M %Z",
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def create_bbox_coordinates(distance, lat, lon):
    assert distance > 0
    assert lat >= -90.0 and lat <= 90.0
    assert lon >= -180.0 and lon <= 180.0
    distance_in_km = distance * 0.001
    """ convert lat/lon from degrees to radians """
    lat, lon = radians(lat), radians(lon)
    """ Radius of the earth in km """
    radius = 6371
    """ Radius of the parallel at given latitude """
    parallel_radius = radius * cos(lat)
    """ Compute lat/lon """
    lat_min = lat - distance_in_km / radius
    lat_max = lat + distance_in_km / radius
    lon_min = lon - distance_in_km / parallel_radius
    lon_max = lon + distance_in_km / parallel_radius
    """ Convert lat/lon from radians back to degrees """
    lat_min, lon_min = degrees(lat_min), degrees(lon_min)
    lat_max, lon_max = degrees(lat_max), degrees(lon_max)
    bbox_coordinates = [lat_min, lon_min, lat_max, lon_max]
    return bbox_coordinates


def server_config1(url, bbox_coord):
    # Get street data from the
    # specified url.

    lat_min, lon_min = bbox_coord[0], bbox_coord[1]
    lat_max, lon_max = bbox_coord[2], bbox_coord[3]
    """ fetch all ways and nodes """

    api = overpy.Overpass(url=url)
    street_data = api.query(
        f"""
    way({lat_min},{lon_min},{lat_max},{lon_max})[highway];
    (._;>;);
    out body;
    """
    )
    return street_data


def server_config2(url, bbox_coord):
    # Get amenities from
    # the specified url.

    lat_min, lon_min = bbox_coord[0], bbox_coord[1]
    lat_max, lon_max = bbox_coord[2], bbox_coord[3]
    api = overpy.Overpass(url=url)
    street_amenities = api.query(
        f"""
    (node({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
    way({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
    rel({lat_min},{lon_min},{lat_max},{lon_max}) ["amenity"];
    way({lat_min},{lon_min},{lat_max},{lon_max}) ["building"];
    );
    out center;
    """
    )
    return street_amenities


def get_streets(bbox_coord):
    """ fetch all ways and nodes """
    try:
        OSM_data = server_config1(defaultServer, bbox_coord)
    except Exception:
        try:
            error = error = (f"{defaultServer} not responding, so connecting "
                             f"{secondaryServer1}")
            LOGGER.debug(error)
            OSM_data = server_config1(secondaryServer1, bbox_coord)
        except Exception:
            try:
                error = error = (
                    f"{secondaryServer1} not responding, so connecting "
                    f"{secondaryServer2}")
                LOGGER.debug(error)
                OSM_data = server_config1(secondaryServer2, bbox_coord)
            except Exception:
                error = 'Unable to get data. All servers down!'
                LOGGER.debug(error)
                OSM_data = None
    return (OSM_data)


def get_timestamp():
    d = datetime.now()
    timestamp = int(datetime.timestamp(d))
    return timestamp


def process_streets_data(OSM_data, bbox_coordinates):
    """Retrieve inteterested street information from the requested OSM data"""
    try:
        processed_OSM_data = []
        lat_min = bbox_coordinates[0]
        lat_max = bbox_coordinates[2]
        lon_min = bbox_coordinates[1]
        lon_max = bbox_coordinates[3]
        for way in OSM_data.ways:
            # List contains only nodes of a street within the bounding box.
            bounded_nodes = []
            # List contains all the nodes of a street (i.e., no boundary
            # restriction).
            unbounded_nodes = []
            for node in way.nodes:
                # Extract all nodes of a street.
                node_object = {
                    "id": int(node.id),
                    "lat": float(node.lat),
                    "lon": float(node.lon),
                }
                # Include tags for a street node if available
                node_object.update(node.tags)
                if node_object not in unbounded_nodes:
                    unbounded_nodes.append(node_object)
                # Apply the boundary conditions to extract only nodes
                # of a street that are within the bounding box.
                if node.lat >= lat_min and node.lat <= lat_max:
                    if node.lon >= lon_min and node.lon <= lon_max:
                        if node_object not in bounded_nodes:
                            bounded_nodes.append(node_object)
            # After the boundary restrictions are applied, it is
            # possible that the list containing the bounded_nodes of
            # a street may no longer have enough points
            # (nodes) to represent the street shape.
            # This is addressed by the function "get_new_nodes",
            # which creates more possible points for the path
            # within the boundary conditions.
            node_list = get_new_nodes(
                bounded_nodes, unbounded_nodes, bbox_coordinates)
            # Check if the "bounded_nodes" for a street/way is not empty.
            # Otherwise all its nodes might have fallen outside the boundary.
            if node_list:
                # Convert lanes to integer if its value is not None
                lanes = way.tags.get("lanes")
                if lanes is not None:
                    lanes = int(lanes)
                # Convert oneway tag to boolean if its value is not None
                oneway = way.tags.get("oneway")
                if oneway is not None:
                    oneway = bool(oneway)
                way_object = {
                    "street_id": int(way.id),
                    "street_name": way.tags.get("name"),
                    "street_type": way.tags.get("highway"),
                    "oneway": oneway,
                    "lanes": lanes
                }
                # Delete key if value is empty
                way_object = dict(x for x in way_object.items() if all(x))
                processed_OSM_data.append(way_object)

                # Remove name, highway, lane, and oneway tags from the tag list
                way.tags.pop("name", None)
                way.tags.pop("highway", None)
                way.tags.pop("lane", None)
                way.tags.pop("oneway", None)

                # Add other tags
                way_object.update(way.tags)
                # Add nodes to the street
                way_object["nodes"] = node_list
                # Delete key if value is empty
                way_object = dict(x for x in way_object.items() if all(x))
                if way_object not in processed_OSM_data:
                    processed_OSM_data.append(way_object)
    except AttributeError:
        error = 'Overpass Attibute error. Retry again'
        LOGGER.debug(error)
        LOGGER.debug(traceback.format_exc())
    else:
        return processed_OSM_data


def get_new_nodes(bounded_nodes, unbounded_nodes, bbox_coordinates):
    # Bounded_nodes is a list of only nodes of a street that fall within
    # the bounding box.
    # Unbounded_nodes is a list of all the nodes of a street.
    number_of_nodes_in_bounded_nodes = len(bounded_nodes)
    number_of_nodes_in_unbounded_nodes = len(unbounded_nodes)
    if bounded_nodes:
        if (number_of_nodes_in_bounded_nodes > 0 and
                number_of_nodes_in_unbounded_nodes >
                number_of_nodes_in_bounded_nodes):
            # Set "there_is_a_succeding_node" flag variable to True.
            there_is_a_succeeding_node = True
            if number_of_nodes_in_bounded_nodes == 1:
                # The condition above is true when the
                # "bounded" list has just a node element.

                # Variable index gives the position of this node in
                # the unbounded_nodes.
                index = unbounded_nodes.index(bounded_nodes[0])
                if (index < number_of_nodes_in_unbounded_nodes - 1 and
                        index > 0):
                    # The above condition is true for
                    # a node element that has both the succeeding
                    # and preceding nodes.
                    # So, estimate a value for the succeeding node.
                    bounded_nodes = add_new_node(
                        there_is_a_succeeding_node, index, bounded_nodes,
                        unbounded_nodes, bbox_coordinates)
                    # Set "there_is_a_succeeding_node" flag to False
                    # to estimate a value for the preceding node.
                    there_is_a_succeeding_node = False
                    bounded_nodes = add_new_node(
                        there_is_a_succeeding_node, index, bounded_nodes,
                        unbounded_nodes, bbox_coordinates)
                elif index < number_of_nodes_in_unbounded_nodes - 1:
                    # This above condition holds if
                    # a node element has just the succeeding node.
                    # Estimate a value for the succeeding node.
                    bounded_nodes = add_new_node(
                        there_is_a_succeeding_node, index, bounded_nodes,
                        unbounded_nodes, bbox_coordinates)
                else:
                    # This holds if the node has only a
                    # preceding node. So, set "there_is_a_succeeding_node"
                    # flag variable to False to get the preceding node.
                    there_is_a_succeeding_node = False
                    # So, estimate value for the preceding node.
                    bounded_nodes = add_new_node(
                        there_is_a_succeeding_node, index, bounded_nodes,
                        unbounded_nodes, bbox_coordinates)

            elif number_of_nodes_in_bounded_nodes > 1:
                # This is the case when the " bounded" list has
                # more than one node element.
                # Here we will only consider only the
                # last and the first node element of
                # the list.
                # Variable index gives the position of the last node element of
                # the "bounded" in the "unbounded" list.
                index = unbounded_nodes.index(
                    bounded_nodes[number_of_nodes_in_bounded_nodes - 1])
                if index < number_of_nodes_in_unbounded_nodes - \
                        1:
                    # If true, there is a succeeding node.
                    # Estimate a value for a succeeding node.
                    bounded_nodes = add_new_node(
                        there_is_a_succeeding_node, index, bounded_nodes,
                        unbounded_nodes, bbox_coordinates)
                # Variable index gives the position of the first node element
                # of the "bounded" in the "unbounded" list.
                index = unbounded_nodes.index(bounded_nodes[0])
                if index > 0:
                    # If the above condition holds true,
                    # then the node has a preceding node. So, estimate a value
                    # for the preceding node.
                    there_is_a_succeeding_node = False
                    bounded_nodes = add_new_node(
                        there_is_a_succeeding_node, index, bounded_nodes,
                        unbounded_nodes, bbox_coordinates)
    return bounded_nodes


def add_new_node(
        there_is_a_succeeding_node, index, bounded_nodes,
        unbounded_nodes, bbox_coordinates):
    # Latitude of the node element.
    lat1 = unbounded_nodes[index]["lat"]
    # Longitude of the node element.
    lon1 = unbounded_nodes[index]["lon"]
    a = (lat1, lon1)
    if there_is_a_succeeding_node:  # Do for a succeeding node
        index = index + 1  # Get the position of the succeeding node
        # The original/initial latitude of the succeeding node
        lat2 = unbounded_nodes[index]["lat"]
        # The original/initial longitude of the succeeding node
        lon2 = unbounded_nodes[index]["lon"]
        b = (lat2, lon2)
        result = Geodesic.WGS84.Inverse(*a, *b)
        # street_boundingbox_angle of the succeeding node from the node element
        # in degrees.
        street_boundingbox_angle = result["azi1"]
        node_parameters = {
            "id": unbounded_nodes[index]["id"],
            "lat1": lat1,
            "lon1": lon1,
            "lat2": lat2,
            "lon2": lon2
        }
        succeeding_node = compute_new_node(
            node_parameters, street_boundingbox_angle, bbox_coordinates)
        bounded_nodes.append(succeeding_node)

    else:  # Do for a preceeding node
        index = index - 1  # Get the position of the preceeding node
        # The real latitude of the preceeding node
        lat2 = unbounded_nodes[index]["lat"]
        # The real longitude of the preceeding node
        lon2 = unbounded_nodes[index]["lon"]
        b = (lat2, lon2)
        result = Geodesic.WGS84.Inverse(*a, *b)
        # Angular difference between a street and the intersecting side
        # of the bounding box in degrees.
        street_boundingbox_angle = result["azi1"]
        node_parameters = {
            "id": unbounded_nodes[index]["id"],
            "lat1": lat1,
            "lon1": lon1,
            "lat2": lat2,
            "lon2": lon2
        }
        preceding_node = compute_new_node(
            node_parameters, street_boundingbox_angle, bbox_coordinates)
        bounded_nodes.insert(0, preceding_node)
    return bounded_nodes


def compute_new_node(
        node_parameters,
        street_boundingbox_angle,
        bbox_coordinates):
    lat_min = bbox_coordinates[0]
    lat_max = bbox_coordinates[2]
    lon_min = bbox_coordinates[1]
    lon_max = bbox_coordinates[3]
    if street_boundingbox_angle < 0:
        street_boundingbox_angle = street_boundingbox_angle + 360
    # Latitude of the node element
    lat1 = node_parameters["lat1"]
    # Longitude of the node element
    lon1 = node_parameters["lon1"]
    # Latitude of either the preceding or the succeeding node.
    lat2 = node_parameters["lat2"]
    # Longitude of either the preceding or the succeeding node.
    lon2 = node_parameters["lon2"]
    top_side_intersection = True
    bottom_side_intersection = True
    # The street_boundingbox_angle indicates the side of the bounding
    # box that intercepts the street.
    if (street_boundingbox_angle >= 0 and
            street_boundingbox_angle < 90):
        # If a street makes an angular intersection of
        # between 0 and 90 with the
        # bounding box, it is likely such a street passes through either the
        # top side or the right side of the bounding box.
        # Validation is used to determine which of the two
        # gives the true result.
        # We first assume the street passes via the top side and validate.
        # If validation fails, then it is the right side.
        lat2 = lat_max
        # Get longitude for the new node
        lon2 = get_new_node_coordinates(
            top_side_intersection,
            lat1,
            lon1,
            lat2,
            street_boundingbox_angle)
        # Validate the latitude/longitude pair. # If validation fails,
        # then intersection will be at the right side.
        validated = validate_new_node_coordinates(lat2, lon2, bbox_coordinates)
        if not validated:  # If validation fails,
            # Set the top_side intersection to False.
            top_side_intersection = False
            lon2 = lon_max
            lat2 = get_new_node_coordinates(
                top_side_intersection, lat1, lon1,
                lon2, street_boundingbox_angle)
    elif (street_boundingbox_angle >= 90 and
          street_boundingbox_angle < 180):
        # If a street makes an angular intersection of
        # between 90 and 180 with the
        # bounding box, it is likely such a street passes through either the
        # bottom side or the right side of the bounding box.
        # Validation is used to determine which of the two
        # gives the true result.
        # We first assume the street passes via the bottom side and validate.
        # If validation fails, then it is the right side.
        lat2 = lat_min
        # Get longitude for the new node
        lon2 = get_new_node_coordinates(
            bottom_side_intersection,
            lat1,
            lon1,
            lat2,
            street_boundingbox_angle)
        # Validate the latitude/longitude pair. # If validation fails,
        # then intersection will be at the right side.
        validated = validate_new_node_coordinates(lat2, lon2, bbox_coordinates)
        if not validated:  # If validation fails,
            # Set the bottom_side intersection to False.
            bottom_side_intersection = False
            lon2 = lon_max
            lat2 = get_new_node_coordinates(
                bottom_side_intersection, lat1, lon1,
                lon2, street_boundingbox_angle)
    elif (street_boundingbox_angle >= 180 and
          street_boundingbox_angle < 270):
        # If a street makes an angular intersection of
        # between 180 and 270
        # with the bounding box, it is likely such a street passes
        # through either the bottom side or the left side of the bounding box.
        # Validation is used to determine which of the
        # two gives the true result.
        # We first assume the street passes via the bottom side and validate.
        # If validation fails, then it is the left side.
        lat2 = lat_min
        # Get longitude for the new node
        lon2 = get_new_node_coordinates(
            bottom_side_intersection,
            lat1,
            lon1,
            lat2,
            street_boundingbox_angle)
        # Validate the latitude/longitude pair. # If validation fails,
        # then intersection will be at the left side.
        validated = validate_new_node_coordinates(lat2, lon2, bbox_coordinates)
        if not validated:  # If validation fails,
            # Set the bottom_side intersection to False.
            bottom_side_intersection = False
            lon2 = lon_min
            lat2 = get_new_node_coordinates(
                bottom_side_intersection, lat1, lon1,
                lon2, street_boundingbox_angle)
    elif (street_boundingbox_angle >= 270 and
          street_boundingbox_angle <= 360):
        # If a street makes an angular intersection of
        # between 270 and 360 with the
        # bounding box, it is likely such a street
        # passes through either the
        # top side or the left side of the bounding box.
        # Validation is used to determine which of the
        # two gives the true result.
        # We first assume the street passes via the
        # top side and validate. If validation fails, then it is the left side.
        lat2 = lat_max
        # Get longitude for the new node
        lon2 = get_new_node_coordinates(
            top_side_intersection,
            lat1,
            lon1,
            lat2,
            street_boundingbox_angle)
        # Validate the latitude/longitude pair. # If validation fails,
        # then intersection will be at the left side.
        validated = validate_new_node_coordinates(lat2, lon2, bbox_coordinates)
        if not validated:  # If  validation fails,
            # the intercept takes place at the left side.
            # Set the top_side intersection to False.
            top_side_intersection = False
            lon2 = lon_min
            lat2 = get_new_node_coordinates(
                top_side_intersection, lat1, lon1,
                lon2, street_boundingbox_angle)
    new_node = {
        "id": node_parameters["id"],
        "node_type": "displaced",
        "lat": float(lat2),
        "lon": float(lon2)
    }
    return new_node


# Get the latitude and the longitude of the new (immediate) node


def get_new_node_coordinates(
        coordinates_indicator,
        lat1,
        lon1,
        node_coordinates,
        street_boundingbox_angle):
    if coordinates_indicator:  # if true, solve for longitude
        lat2 = node_coordinates
        # Compute longitude
        lon2 = ((math.tan(radians(street_boundingbox_angle)) *
                (lat2 - lat1)) / math.cos(radians(lat1))) + lon1
        return lon2
    else:  # solve for latitude
        lon2 = node_coordinates
        # Compute latitude
        lat2 = ((lon2 - lon1) * math.cos(radians(lat1)) /
                math.tan(radians(street_boundingbox_angle))) + lat1
        return lat2


def validate_new_node_coordinates(lat2, lon2, bbox_coordinates):
    lat_min = bbox_coordinates[0]
    lat_max = bbox_coordinates[2]
    lon_min = bbox_coordinates[1]
    lon_max = bbox_coordinates[3]
    if ((lat2 >= lat_min and lat2 <= lat_max) and
            (lon2 >= lon_min and lon2 <= lon_max)):
        return True


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
                            if "highway" in nodes[i]:
                                nodes[i]["cat"] = nodes[i]["highway"]
                            nodes[i]["intersection"] = [id1, id2]
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
    lat_min = bbox_coord[0]
    lat_max = bbox_coord[2]
    lon_min = bbox_coord[1]
    lon_max = bbox_coord[3]
    try:
        amenities = server_config2(defaultServer, bbox_coord)
    except Exception:
        try:
            error = (f"{defaultServer} not responding, so connecting "
                     f"{secondaryServer1}")
            LOGGER.debug(error)
            amenities = server_config2(secondaryServer1, bbox_coord)
        except Exception:
            try:
                error = (f"{secondaryServer1} not responding, so connecting "
                         f"{secondaryServer2}")
                LOGGER.debug(error)
                amenities = server_config2(secondaryServer2, bbox_coord)
            except Exception:
                error = 'Unable to get data. All servers down!'
                LOGGER.debug(error)
                amenities = None

    # Fetch the basic amenity tags
    amenity = []
    if amenities is not None:
        if amenities.nodes:
            for node in amenities.nodes:
                # Extract only amenities(under nodes) within the boundary
                if ((node.lat >= lat_min and node.lat <= lat_max) and (
                        node.lon >= lon_min and node.lon <= lon_max)):
                    amenity_record = {
                        "id": int(node.id),
                        "lat": float(node.lat),
                        "lon": float(node.lon),
                        "name": node.tags.get("name"),
                    }
                    # Fetch as many tags possible beyond the basic
                    # Remove name tag
                    node.tags.pop("name", None)
                    if "amenity" in node.tags:
                        amenity_record["cat"] = node.tags.get("amenity")
                        node.tags.pop("amenity", None)
                        # Add other tags
                        amenity_record.update(node.tags)
                        # Delete keys with no value
                        amenity_record = dict(
                            x for x in amenity_record.items() if all(x))
                        if amenity_record not in amenity:
                            amenity.append(amenity_record)
                    if "highway" in node.tags:
                        amenity_record["cat"] = node.tags.get("highway")
                        node.tags.pop("highway", None)
                        # Add other tags
                        amenity_record.update(node.tags)
                        # Delete keys with no value
                        amenity_record = dict(
                            x for x in amenity_record.items() if all(x))
                        if amenity_record not in amenity:
                            amenity.append(amenity_record)

        if amenities.ways:
            for way in amenities.ways:
                # Extract only amenities(under ways) within the boundary
                if (way.center_lat >= lat_min and way.center_lat <= lat_max
                    and way.center_lon >= lon_min
                        and way.center_lon <= lon_max):
                    amenity_record = {
                        "id": int(way.id),
                        "lat": float(way.center_lat),
                        "lon": float(way.center_lon),
                        "name": way.tags.get("name"),
                    }
                    # Remove name tag
                    way.tags.pop("name", None)
                    if "amenity" in way.tags:
                        amenity_record["cat"] = way.tags.get("amenity")
                        # Remove name tag and fetch other tags available
                        way.tags.pop("amenity", None)
                        # Add other tags
                        amenity_record.update(way.tags)
                        # Delete keys with no value
                        amenity_record = dict(
                            x for x in amenity_record.items() if all(x))
                        if amenity_record not in amenity:
                            amenity.append(amenity_record)
                    if "building" in way.tags:
                        amenity_record["cat"] = way.tags.get("building")
                        if amenity_record["cat"] == "yes":
                            amenity_record["cat"] = "building"
                        # Remove building tag and fetch other tags available
                        way.tags.pop("building", None)
                        # Add other tags
                        amenity_record.update(way.tags)
                        # Delete keys with no value
                        amenity_record = dict(
                            x for x in amenity_record.items() if all(x))
                        if amenity_record not in amenity:
                            amenity.append(amenity_record)

        if amenities.relations:
            for rel in amenities.relations:
                # Extract only amenities(under relations) within the boundary
                if (rel.center_lat >= lat_min and rel.center_lat <= lat_max
                    and rel.center_lon >= lon_min
                        and rel.center_lon <= lon_max):
                    amenity_record = {
                        "id": int(rel.id),
                        "lat": float(rel.center_lat),
                        "lon": float(rel.center_lon),
                        "name": rel.tags.get("name")
                    }
                    # Remove name tag
                    rel.tags.pop("name", None)
                    if "amenity" in rel.tags:
                        amenity_record["cat"] = rel.tags.get("amenity")
                        # Remove amenity tag and fetch other tags available
                        rel.tags.pop("amenity", None)
                        # Add other tags
                        amenity_record.update(way.tags)
                        # Delete keys with no value
                        amenity_record = dict(
                            x for x in amenity_record.items() if all(x))
                        if amenity_record not in amenity:
                            amenity.append(amenity_record)
    return amenity


def enlist_POIs(processed_OSM_data1, amenity):
    # Keep all identified points of interest in a single list
    POIs = []
    nodes_ids = []
    if len(processed_OSM_data1):
        for obj in range(len(processed_OSM_data1)):
            nodes = processed_OSM_data1[obj]["nodes"]
            for node in range(len(nodes)):
                key_to_check = "cat"
                # check if "cat" key is in the node
                if (key_to_check in nodes[node]
                        or "intersection" in nodes[node]):
                    # Check to remove duplicate intersections
                    if nodes[node] not in POIs:
                        if nodes[node]["id"] not in nodes_ids:
                            nodes_ids.append(nodes[node]["id"])
                            nodes_ids.append(nodes[node]["id"])
                            POIs.append(nodes[node])
    if amenity is not None and len(amenity) != 0:
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
            # check if true, then the points of interest are amenity,
            # e.g. restaurants, bars, rentals, etc
            if "intersection" not in POIs[i] and amenity is not None:
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
    # Use Python Sort function
    processed_OSM_data2 = compute_street_length(processed_OSM_data2)
    processed_OSM_data2 = (
        sorted(
            processed_OSM_data2,
            key=lambda x:
                x['distance'],
            reverse=True))

    for obj in range(len(processed_OSM_data2)):
        # Delete the distance key
        processed_OSM_data2[obj].pop('distance', None)
        # Remove node tags from the streets list
        # since they are now included in the points of interest
        # list.
        nodes = processed_OSM_data2[obj]["nodes"]
        for node in range(len(nodes)):
            node_object = {
                "id": nodes[node]["id"],
                "lat": nodes[node]["lat"],
                "lon": nodes[node]["lon"]
            }
            if "node_type" in nodes[node]:
                node_object["node_type"] = nodes[node]["node_type"]
            if "POIs_ID" in nodes[node]:
                node_object["POIs_ID"] = nodes[node]["POIs_ID"]
            nodes[node] = node_object
    return processed_OSM_data2


def compute_street_length(processed_OSM_data):
    # Compute the overall path length
    for obj in range(len(processed_OSM_data)):
        nodes = processed_OSM_data[obj]["nodes"]
        for node in range(len(nodes)):
            if node <= 0:
                i = 0
                sum = 0
                for j in range(i + 1, len(nodes)):
                    lat1 = nodes[i]["lat"]
                    lon1 = nodes[i]["lon"]
                    lat2 = nodes[j]["lat"]
                    lon2 = nodes[j]["lon"]
                    location1 = (float(lat1), float(lon1))
                    location2 = (float(lat2), float(lon2))
                    # Compute the distance between two adjacent nodes of a way
                    # (in metres)
                    distance = (hs.haversine(location1, location2) * 1000)
                    # Sum up the distance
                    sum = sum + distance
                    i = i + 1
        processed_OSM_data[obj]["distance"] = sum
    return processed_OSM_data


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
        LOGGER.error(error)
        return jsonify(json_message), error_code
    return None

# This supports input request from google embedded map.


def get_coordinates(content):
    """
    Retrieve the coordinates of a map from the
    content of the request
    """
    if 'coordinates' in content.keys():
        return content['coordinates']

    if "placeID" not in content:
        error = 'Unable to find placeID'
        LOGGER.error(error)
        return jsonify(""), 400

    if "GOOGLE_PLACES_KEY" not in os.environ:
        LOGGER.debug("Unable to find path to API key directory")
        return jsonify(""), 500
    google_api_key = os.environ["GOOGLE_PLACES_KEY"]

    # Query google places API to find latitude longitude
    request = f"https://maps.googleapis.com/maps/api/place/textsearch/json?\
            query={content['placeID']}&\
            key={google_api_key}"
    request = request.replace(" ", "")
    place_response = requests.get(request).json()

    if not check_google_response(place_response):
        LOGGER.debug("Zero or Incomplete results returned for place ID")
        return jsonify(""), 500

    location = place_response['results'][0]['geometry']['location']
    coordinates = {
        'latitude': location['lat'],
        'longitude': location['lng']
    }

    return coordinates


def check_google_response(place_response):
    """
    Helper method to check whether the response from
    the Google Places API is valid

    Args:
        place_response: the response from the Google Places API

    Returns:
        bool: True if valid, False otherwise
    """
    if 'results' not in place_response or len(place_response['results']) == 0:
        LOGGER.error("No results found for placeID")
        LOGGER.error(place_response)
        return False

    result = place_response['results'][0]

    if 'geometry' not in result:
        LOGGER.error("No geometry found for placeID")
        return False

    if 'location' not in result['geometry']:
        LOGGER.error("No location found for placeID")
        return False

    if 'lat' not in result['geometry']['location']:
        LOGGER.error("No latitude found for placeID")
        return False

    if 'lng' not in result['geometry']['location']:
        LOGGER.error("No longitude found for placeID")
        return False

    return True
