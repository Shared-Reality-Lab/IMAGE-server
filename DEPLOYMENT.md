# Deploying the IMAGE Server

The following information is meant to aid people in getting IMAGE running
on their own so components can be used. It is based on what we've done for
our testing and production environments, but by no means is this the only
way to deploy. The general principles and concerns will likely be relevant.

## Dependencies and Environment

The following is written with the assumption you are running a Debian-based
Linux environment. This should work elsewhere, but this is not something
we have practical experience with. You should have installed:

- [Docker Engine](https://docs.docker.com/engine/) and [Docker Compose](https://docs.docker.com/compose/)
    - Note: For version 20.10.13 and later, the `docker-compose-plugin` package provides the `docker compose` subcommand which operates the same was as `docker-compose`.
- NVIDIA drivers and [nvidia-container-runtime](https://docs.docker.com/config/containers/resource_constraints/#gpu)
    - Many of these containers do not use or do not need to use a GPU, but performance will be greatly reduced.
- [Git](https://git-scm.com/)

## Unstable vs Latest

Our Docker images our tagged in four possible ways:

1. A timestamp: this indicates the time the image was built.
2. `latest`: the newest *production-ready* version of an image.
3. `unstable`: the newest version of an image based on what is on the main branch. This *may* be suitable for production, but has received less vetting.
4. A version: this indicates a particular production-ready version of an image. It may not be the newest.

Typically, we use *unstable* for testing and development and *latest* for production.
We recommend you follow this if you are unsure which to use.

## For Testing/Local Use

Clone the repository by running:
```
git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git
```

The default compose file within there (`docker-compose.yml`) is a useful base for testing. Each image will be downloaded from the Github Container Registry
using the "unstable" tag.

This can be brought up using `docker-compose up -d`.

## For Production

For production, it is recommended to use "latest" and limit the number of running services for additional stability.
We also recommend running two instances of supercollider to allow for multiple audio files to be generated at once. This can be done with the following keys:
```yaml
deploy:
    replicas: 2
```

## Configuration

Certain files need to be set to run the server.

### Orchestrator

In order to access the docker socket, the orchestrator must run as part of the docker group.
Otherwise, it will not be able to find any preprocessors and handlers.

Determine the GID for docker. One way to do this is to run
`grep docker /etc/group | awk -F: '{ print $3 }'`.
This number is the group ID.
This must be set as the `DOCKER_GID` environment variable that gets used
in `docker-compose.yml`.
To do this, append the line
```
DOCKER_GID=NUM
```
to `.env` in the directory containing `docker-compose.yml` where `NUM` is replaced with the GID.

### Autour Preprocessor

For the autour preprocessor to work, it must have the environment variable
`GOOGLE_PLACES_KEY` set to a valid API key. This can be done in many ways,
but we include it at `./config/maps.env` and load this using the `env_file` key in `docker-compose.yml`.
If you do not want to use this preprocessor, either remove these lines
or create an empty file of this name as otherwise service creation may fail, even if you aren't starting this preprocessor.

### OCR, Graphic Tagger, and Azure Object Detection Preprocessors

For these to work, a valid Microsoft Azure API key must be available in the
environment variable `AZURE_API_KEY`. You can set this in a variety of ways,
but we read from the file `'./config/azure.env` using the `env_file` key
in `docker-compose.yml`.
If you do not want to use this preprocessor, either remove these lines where they appear or create an empty file of this name. Otherwise, service creation may fail even if you
aren't starting these preprocessors.

## Networking

While you can run only the containers in the `docker-compose.yml` and
have full functionality, this probably isn't convenient for production.
We use two reverse proxies in our testing and production configurations.

The first is a [Traefik](https://traefik.io) instance in docker that runs in front of the entire
server. It is either configured to redirect a specific domain or
a specific route to a particular Docker container. It also is set up to
handle TLS certificate management and HTTPS redirection.

Traefik forwards requests (e.g., anything to `image.a11y.mcgill.ca`) to
a second web server. This one is a docker instance of [nginx](https://nginx.org)
that normally hosts the [IMAGE website](https://image.a11y.mcgill.ca).
It forwards requests to orchestrator endpoints (e.g., `/render`) to the
orchestrator docker service.

Note that if these are not in the same `docker-compose.yml`, they will not
share networks by default. For this reason, we typically include
the nginx instance in the IMAGE `docker-compose.yml` and then include
the traefik network externally using the following configuration:
```yaml
networks:
  traefik:
    external: true
    name: traefik
  default:
    name: image
```
This connects to a preexisting network named "traefik" while also explicitly naming the default network created by this compose "image".
Remember that non-default networks must be explicitly added to services.
