from typing import Optional
from copy import deepcopy
from fastapi import FastAPI
import haversine as hs
from app.osm_service import (
    query_osmdata,
    transform_osmdata,
    extract_nodes_list,
    extract_intersection,
    merge_street_intersection_by_name,
)
from app.osm_service import (
    create_new_intersection_sets,
    my_final_data_structure,
    merge_street_points_by_name,
    merge_street_by_name,
    compute_query_bounding_box,
)
from app.osm_service import (
    get_amenities,
    process_extracted_amenities,
    align_points_of_interest,
    retrieve_all_point_of_interest,
)
from app.osm_service import (
    keep_in_list_all_retrieved_point_of_interest,
    final_osm_data_format,
)


app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{distance_in_metres}/{lat}/{lon}")
def get_location(distance_in_metres: float, lat: float, lon: float):
    coordinates = compute_query_bounding_box(distance_in_metres, lat, lon)

    queried_osm_data, bbox = query_osmdata(coordinates)

    transformed_osm_data = transform_osmdata(queried_osm_data)
    
    merged_street = merge_street_by_name(transformed_osm_data)

    intersection, street_intersection_sets = extract_nodes_list(merged_street)

    new_intersection_list = create_new_intersection_sets(intersection)

    merged_intersection = merge_street_intersection_by_name(street_intersection_sets)

    copy_of_merged_street = deepcopy(merged_street)

    copy_of_new_intersection_list = deepcopy(new_intersection_list)

    street_records = my_final_data_structure(
        copy_of_merged_street, copy_of_new_intersection_list, merged_intersection
    )

    merged_street_data = merge_street_points_by_name(street_records)

    amenities = get_amenities(coordinates)

    processed_amenities = process_extracted_amenities(amenities)

    copy_of_merged_street_data = align_points_of_interest(
        processed_amenities, merged_street_data
    )

    retrieved_point_of_interest = retrieve_all_point_of_interest(
        copy_of_merged_street_data
    )

    (
        unique_listed_point_of_interest,
        listed_point_of_interest,
    ) = keep_in_list_all_retrieved_point_of_interest(retrieved_point_of_interest)

    response = final_osm_data_format(unique_listed_point_of_interest, merged_street)
    comment1 = "//map_area: [lat_min, lon_min, lat_max, lon_max]:"
    comment2 = "//poi_collection:"
    comment3 = "//streets:"

    return (comment1, bbox, comment2, listed_point_of_interest, comment3, response)
