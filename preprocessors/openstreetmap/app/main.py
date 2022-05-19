from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
import logging
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


class Coordinate(BaseModel):
    latitude: float
    longitude: float

# Validate incoming request


class incoming_request(BaseModel):
    request_uuid: str
    timestamp: int
    coordinates: Coordinate
    context: str
    language: str
    url: str
    capabilities: list[str] = []
    renderers: list[str]


# Validate preprocessor's response

class outgoing_request(BaseModel):
    request_uuid: str
    timestamp: int
    name: str
    data: object


@app.get("/")
def health():
    return {"Hello": "World"}

# Generate validation error if JSON request format is invalid


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)


@app.post("/preprocessor/", response_model=outgoing_request)
async def get_map_data(request: incoming_request):

    request = jsonable_encoder(request)
    latitude = request["coordinates"]["latitude"]
    longitude = request["coordinates"]["longitude"]
    request_uuid = request["request_uuid"]
    distance: float = 100
    bbox_coordinates = create_bbox_coordinates(distance, latitude, longitude)
    OSM_data = query_OSMap(bbox_coordinates)
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
    response = {

        "request_uuid": request_uuid,
        "timestamp": int(get_timestamp()),
        "name": "ca.mcgill.a11y.image.preprocessor.openstreetmap",
        "data": response,

    }

    logging.debug("Sending response")
    return response
