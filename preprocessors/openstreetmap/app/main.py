from fastapi import FastAPI
import uuid
from app.osm_service import (
    query_OSMap,
    get_timestamp,
    create_bbox_coordinates,
    process_OSMap_data,
    extract_street,
    allot_intersection,
    get_amenities,
    enlist_POIs,
    OSM_preprocessor,
)
app = FastAPI()


@app.get("/")
def health():
    return {"Hello": "World"}


@app.get("/location/{distance_in_metres}/{lat}/{lon}")
def get_location(distance: float, lat: float, lon: float):
    bbox_coordinates = create_bbox_coordinates(distance, lat, lon)
    OSM_data = query_OSMap(bbox_coordinates)
    timestamp = get_timestamp()
    processed_OSM_data = process_OSMap_data(OSM_data)
    intersection_record_updated = extract_street(processed_OSM_data)
    POD1 = allot_intersection(processed_OSM_data, intersection_record_updated)
    amenity = get_amenities(bbox_coordinates)
    POIs = enlist_POIs(POD1, amenity)
    response = OSM_preprocessor(processed_OSM_data, POIs)
    response = {
        "point_of_interest": POIs,
        "streets": response,
    }
    OSM_Preproc = {
        "request_uuid": uuid.uuid4(),
        "timestamp": timestamp,
        "coordinates": {
            "latitude": lat,
            "longitude": lon},
        "context": "",
        "language": "en",
        "url": "",
        "capabilities": [],
        "renderers": "",
        "preprocessor": {
            "OSM_preprocessor": {
                "latitude": lat,
                "longitude": lon,
                "radius": distance,
                "bounding_box": bbox_coordinates,
                "OSM_data": response, }}}
    return (OSM_Preproc)
