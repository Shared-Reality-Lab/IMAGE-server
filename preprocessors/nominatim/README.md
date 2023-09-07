# Nominatim Preprocessor

This preprocessor looks for geospatial coordinates in the request (i.e., a latitude and longitude) and uses [Nominatim](https://nominatim.org) to find a common name for the location, if possible.
This name is either a civic address or the proper name of a business, landmark, organization, etc.
The public Nominatim server is used by default, but can be overridden with the `NOMINATIM_SERVER` environment variable.
