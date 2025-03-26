# Deploying the IMAGE Server

The following information is meant to aid people in getting IMAGE running
on their own so components can be used. It is based on what we've done for
our testing and production environments, but by no means is this the only
way to deploy. The general principles and concerns will likely be relevant.

## System Requirements & Dependencies

The following is written with the assumption you are running a Debian-based Linux distribution (e.g., Ubuntu 24.04, Debian 12).
Other distributions may work but are not officially tested.

Minimum System Requirements
- OS: Debian-based Linux (Ubuntu 24.04+ recommended) -- Pegasus runs on Ubuntu 24.04 LTS, so we recommend using the latest LTS.
- CPU: At least 4 cores recommended -- more cores improve parallel processing.
- RAM: 16GB or more recommended -- Some services may require more RAM, especially if running multiple preprocessors concurrently.
- Storage: 50GB free, 100GB+ recommended if using a GPU
- GPU: NVIDIA GPU required for certain services (some services will not run on CPU-only configurations)
      - While AMD GPUs may work, we have not tested compatibility with AMD ROCm or other alternatives


IMAGE Server was also successfully deployed on AWS EC2 using the below configuration:
- Instance Type:	[Preferred] g4dn.xlarge (GPU) or t3.large (CPU-only)
- OS:	Ubuntu 22.04 LTS
- CPU: 4 vCPUs
- RAM: 16GB
- Storage: 1000GB EBS (Elastic Block Store)
- Network: Default VPC with public IPv4
- Security Group: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS) -- Required for server & web-based access

Note: If using a CPU-only instance (t3.large), some preprocessors/services will not be available.


## Required Software
You will need the following installed:

- [Docker Engine](https://docs.docker.com/engine/) and [Docker Compose](https://docs.docker.com/compose/)
    - Note: docker-compose-plugin is required (old versions used docker-compose)
- NVIDIA drivers and [nvidia-container-runtime](https://docs.docker.com/config/containers/resource_constraints/#gpu)
    - Many of these containers do not use or do not need to use a GPU, but performance will be greatly reduced.
- [Git](https://git-scm.com/)
- Python & Pip

Note that running every GPU-ready container on a GPU will use multiple GB of memory
on the device. On many GPUs, an out-of-memory error will occur. For most GPU-ready
containers, switching it to CPU is a matter of removing the deployment lines
specifying it should have access to a GPU. Otherwise, there will be an environment
variable specifying which to use (e.g., "cuda", "cpu").

## Unstable vs Latest

Our Docker images our tagged in four possible ways:

1. A timestamp: this indicates the time the image was built.
2. `latest`: the newest *production-ready* version of an image.
3. `unstable`: the newest version of an image based on what is on the main branch. This *may* be suitable for production, but has received less vetting.
4. A version: this indicates a particular production-ready version of an image. It may not be the newest.

Typically, we use *unstable* for testing and development and *latest* for production.
We recommend you follow this if you are unsure which to use.

## Installing Dependencies

Update system packages: 
`sudo apt update && sudo apt upgrade -y`

Required software:
`sudo apt install -y docker.io download docker`

Verify: `docker --version`

Install Docker Compose: `sudo apt install -y docker-compose`
Verify: `docker-compose --version`

Add user to docker group: (so you don't have to keep running with sudo):
`sudo usermod -aG docker $USER`

`newgrp docker`
(Verify with `docker run hello-world`)

Install NVIDIA drivers: `sudo apt install -y nvidia-driver nvidia-container-runtime`
`sudo reboot`
Verify: `nvidia-smi`



Clone the repository. Please note that if you see permission errors, you might not have an SSH key. [Check the documentation here.](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/4.-SSH-for-connecting-to-servers-and-to-github) 

`git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git`

Cloning into 'IMAGE-server'...
remote: Enumerating objects: 17977, done.
remote: Counting objects: 100% (2127/2127), done.
remote: Compressing objects: 100% (564/564), done.
remote: Total 17977 (delta 1846), reused 1608 (delta 1561), pack-reused 15850 (from 1)
Receiving objects: 100% (17977/17977), 62.84 MiB | 28.97 MiB/s, done.
Resolving deltas: 100% (11361/11361), done.
Submodule 'docker/schemas' (git@github.com:Shared-Reality-Lab/IMAGE-server.git) registered for path 'schemas'
Cloning into '/home/ubuntu/IMAGE-server/schemas'...
remote: Enumerating objects: 17977, done.        
remote: Counting objects: 100% (2127/2127), done.        
remote: Compressing objects: 100% (564/564), done.        
remote: Total 17977 (delta 1846), reused 1608 (delta 1561), pack-reused 15850 (from 1)        
Receiving objects: 100% (17977/17977), 62.84 MiB | 35.61 MiB/s, done.
Resolving deltas: 100% (11361/11361), done.
Submodule path 'schemas': checked out 'b36c5d5fd2a7f223f996a54d01c84aeffe1b2610'


Configure environment:

ubuntu@ip-172-31-29-145:~$ `grep docker /etc/group | awk -F: '{ print $3 }'`
122

`touch .env`
`nano .env` --> DOCKER_GID=122

ubuntu@ip-172-31-29-145:~$ cat .env
DOCKER_GID=122


Navigate to IMAGE Server project directory:

ubuntu@ip-172-31-29-145:~/IMAGE-server$ `pwd`

/home/ubuntu/IMAGE-server



Before running ~/IMAGE-server$ `docker-compose up -d`,

Ensure the necessary .env files are configured with the necessary API keys:

/home/ubuntu/IMAGE-server/config/apis-and-selection.env

/home/ubuntu/IMAGE-server/config/azure-api.env

/home/ubuntu/IMAGE-server/config/ollama.env

/home/ubuntu/IMAGE-server/config/maps.env




If you see: ubuntu@ip-172-31-29-145:~/IMAGE-server$ docker-compose up -d
ERROR: Network traefik declared as external, but could not be found. Please create the network manually using `docker network create traefik` and try again.

Create the traefik betwork:
ubuntu@ip-172-31-29-145:~/IMAGE-server/config$ `docker network create traefik`
a850e29554fdb1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Then re-try:
ubuntu@ip-172-31-29-145:~/IMAGE-server$ `docker-compose up -d`
Creating volume "image-server_sc-store" with default driver
Creating volume "image-server_user-logs" with default driver
Creating volume "image-server_website-logs" with default driver
Pulling orchestrator (ghcr.io/shared-reality-lab/image-orchestrator:unstable)...
unstable: Pulling from shared-reality-lab/image-orchestrator
....


Please note that GPU-based services (espnet-tts, semantic-segmentation, object-detection, etc.) will require GPU, or else you might run into
ERROR: for action-recognition  Cannot start service action-recognition: could not select device driver "nvidia" with capabilities: [[gpu utility compute]]


Verify the containers are running :-
`docker ps`



## For Testing/Local Use

The default compose file within there (docker-compose.yml) is a useful base for testing. Each image will be downloaded from the Github Container Registry using the "unstable" tag.

This can be brought up using docker-compose up -d. We recommend limiting the number of running services to fit the resource constraints of your particular system (i.e., available CPU, GPU, memory).



## For Production

For production, it is recommended to use "latest" and limit the number of running services for additional stability.
We also recommend running two instances of supercollider to allow for multiple audio files to be generated at once. This can be done with the following keys:
```yaml
deploy:
    replicas: 2
```

### API Keys

For services that rely on third-party servers to run, access to an API key is often
necessary. For obvious reasons, these are not committed to the repository.
The way we typically have handled loading an API key is as follows:

1. Reference an environment variable in the program that should contain the API key;
2. Set the environment variable *only for services that need it* using the `docker-compose.yml`.

Examples for a few preprocessors are described below.

#### Autour Preprocessor

For the autour preprocessor to work, it must have the environment variable
`GOOGLE_PLACES_KEY` set to a valid API key. This can be done in many ways,
but we include it at `./config/maps.env` and load this using the `env_file` key in `docker-compose.yml`.
If you do not want to use this preprocessor, either remove these lines
or create an empty file of this name as otherwise service creation may fail, even if you aren't starting this preprocessor.

#### OCR, Graphic Tagger, and Azure Object Detection Preprocessors

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


