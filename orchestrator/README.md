# IMAGE Orchestrator

![license: AGPL](https://img.shields.io/badge/license-AGPL-success) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-orchestrator)

## What is this?

The orchestrator is the point-of-entry into the IMAGE server components. It:
- validates an HTTP request against the schema documents,
- determines which preprocessors and handlers are available for use,
- forwards requests to preprocessors, adding the results from each to the next request sent,
- sends the original request and all preprocessor outputs to the handlers to receive renderings, and
- sends all renderings back to the client.

It also can optionally save the requests and responses for a temporary amount of time unless the user who created
the request indicates they would like it to be saved for debugging purposes. This is explained more below.

The orchestrator runs within the container on port 8080.

## Options

Three environment variables are checked
- `STORE_IMAGE_DATA`: when set to `ON` or `on`, the request and response data associated with a request will be stored in a subdirectory
of `/var/log/IMAGE` with the name of the UUID for that request *in the orchestrator container*. A volume should be
mounted to this location if this option is used. A cron job will delete subdirectories older than 1 hour every 10 minutes
unless that request has been [authorized by the user to save beyond that point](#authenticate).
If left unset or set to any other value, request and response data will never be saved.
- `PARALLEL_PREPROCESSORS`: when set to `ON` or `on`, the preprocessors in a [priority group](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#docker-compose-configuration) will be run in parallel
rather than serially. Note that this may result in higher resource usage which can cause instability if resources (e.g., GPU memory) are exhausted.
If left unset or set to any other value, preprocessors within a group will run sequentially although in an undefined order.
- `MEMCACHE_SERVERS`: this contains the server and the port of the memcache where memjs client will connect to. Server should match with the service name of docker container (as specfied in docker-compose). Multiple servers are separated by a comma. If this value is missing, memjs client will try to connect to 'localhost:11211'.  Refer https://memjs.netlify.app/ for details 

## Endpoints

### Render

Accessible at `POST /render` with a body of type `application/json`. A valid request sent to this endpoint goes through the process outlined above. That is,
the request will be validated, preprocessors will run, and handlers will generate renderings if possible.

### Preprocessors Only

Accessible at `POST /render/preprocess` with a body of type `application/json`. At first, the orchestrator responds
the same as if it was sent to `/render`, but will stop after the preprocessor section and return the data that would
otherwise be sent to the handlers. This is most useful for debugging purposes.

### Authenticate

Accessible at `GET /authenticate/:uuid/:check` where `:uuid` must be the random UUID of a request and `:check` is the [object-hash](https://www.npmjs.com/package/object-hash) SHA1 checksum
of the request JSON object. This is only available if `STORE_IMAGE_DATA` is on.
In that case, the orchestrator will check if a UUID matching `:uuid` is currently saved and, if so, if the
request associated with it has the checksum provided in this GET request. If it does, the saved request/response pair
will be marked for long-term storage and not deleted by the cron job when it is older than 1 hour.


## Configuration

Here is a snippet of the service from our sample `docker-compose.yml`:

```yaml
orchestrator:
  image: ghcr.io/shared-reality-lab/image-orchestrator:unstable
  env_file:
    - ./config/express-common.env
  environment:
    - STORE_IMAGE_DATA=ON
    - PARALLEL_PREPROCESORS=ON
  group_add:
    - ${DOCKER_GID}
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - user-logs:/var/log/IMAGE
```

The environment file loaded at `./config/express-common.env` increases the maximum body size allowed by Express.
If this is not included, larger requests (for example, those including larger graphics) will be rejected by the orchestrator
and not be handled by IMAGE. For consistency, this value should be used in all containers using Express.

The environment variable section sets the options for the orchestrator. These may be set another way, or the section can just
be omitted if the default behavior is desired.

The orchestrator runs as a non-root user. As such, the container must be run with permissions of the `docker` group on the host
in order to access the socket. The socket must also be mounted into the container (the bind mount `/var/run/docker.sock:/var/run/docker.sock:ro`).
This docker group ID changes from system to system and needs to be checked manually using a command like `cat /etc/group | grep docker | awk -F: '{ print $3 }'`

## Cache Implementation

IMAGE uses Memcached as in-memory data store. Cache is implemented using [MemJS](https://www.npmjs.com/package/memjs). Following is the confugration to enable Cache for preprocessors:

- Cache size is configured in the docker-compose in the commad attribute under memcached service `command: -m 4096` implies cache size of 4GB.

- Cache timeout is configured at the preprocessor level, with the label `ca.mcgill.a11y.image.cacheTimeout` . Label value is the timeout value in seconds. Timeout value of 0 indicates that Cache is disabled for a preprocessor. Missing `ca.mcgill.a11y.image.cacheTimeout` label on the preprocessor will default to timeout value of 0.

- Cache key is generated using the following attributes:
  - `reqData` can have the following values
    - `request["data"]` (for graphics)
    - `request["placeID"]`/`request["coordinates"]` (for maps)
    - `request["highChartsData"]` (for charts)
  - `preprocessor` - preprocessor id (as returned in the response) identifying the data returned by the preprocessor 

  cache key is the [object-hash](https://www.npmjs.com/package/object-hash) generated for the object `{reqData, preprocessor}`

