# Deploying the IMAGE Server
There are many ways to configure and deploy an IMAGE server.
We describe how our own IMAGE server is configured, as a reference for you to do your own deployment.
IMAGE server heavily relies on Docker, and is deployed via a docker-compose file, so if you aren't familiar with Docker, you will struggle to set up a server from scratch.
We generally do not provide step-by-step instructions itemizing each command, as these change with versions, etc.
High level steps for deployment:

1. Install Debian server (We use Ubuntu LTS), whether on a local machine, or in the cloud (we have used Amazon EC2)
2. Install and configure base tools including Docker and GPU driver
3. Set up your directory structure, clone the IMAGE server repository, and configure links
3. Decide how you will handle routing (we use traefik), and encryption (easy if you use traefik!)
4. Set up config files for accessing external tools like an LLM
5. Run the imageup script to bring up the entire IMAGE server stack
6. Point the IMAGE browser extension to your server via the options page
6. Know how to keep your IMAGE server updated


# System Requirements
System requirements vary depending on what components you will run, and how loaded you expect your server to be.
For reference, we run a test server with a Ryzen 3800x CPU, 32GB RAM, 1GB NVMe, and a couple of older NVidia GPUs (Titan XP and 1660ti).
This is fine for testing, including running a very small local LLM.
Our production reference server is beefier, with a Ryzen 7950x CPU, 5090 NVidia GPU, 64GB RAM, 2TB NVMe.
Anecdotal load testing indicates that the production reference server responds to most requests in roughly 5 seconds, and can support multiple users all making overlapping requests from the browser extension as fast as they can (although response time increases).

Pretty much any IMAGE server will require a GPU for running local ML models and services.
However, if you use a remote API for LLM functionality, an 8GB VRAM GPU can be sufficient for running the smaller local models that provide, for example, text-to-speech.
We expect that it will soon be possible to run an IMAGE server without any local GPU resources, and only use cloud endpoints, but at least a small GPU is currently required.
If you run a local LLM, anticipate using approximately 20GB of GPU VRAM for reasonable response quality.

We have also run IMAGE on AWS EC2. Note that the major cost is the dedicated GPU:
- Instance Type: g5.xlarge (GPU)
- OS: Ubuntu 22.04 LTS
- CPU: 4 vCPUs
- RAM: 16 GiB (15 GiB usable)
- Storage: 1000GB EBS (Elastic Block Store)
- Network: Default VPC with public IPv4
- Security Group: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS) — Required for server & web-based access

# System setup
- Install Debian or Ubuntu LTS Server
- Install and configure Docker (make sure `docker --version` & `docker compose --version` both work)
- Install GPU drivers (make sure `nvidia-smi` sees your GPU

# Cloning and configuring
We strongly recommend putting all of the IMAGE server components in the directory `/var/docker/image`.
Although mostly abstracted, if you use another directory, you may need to adjust scripts.

In `/var/docker/image`, clone the IMAGE server repository:

```
git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git
```

In the same directory, make the following soft links, to get access to scripts and configuration, and copy the prod-docker-compose.yml file so you can modify it to reflect your server configuration:

```
ln -s /var/docker/image/IMAGE-server/scripts ./bin
ln -s IMAGE-server/config ./config
ln -s  IMAGE-server/docker-compose.yml ./docker-compose.yml
cp IMAGE-server/prod-docker-compose.yml ./prod-docker-compose.yml
```

Create a `.env` file that tells Docker, for example, what profile you want to use (production, test, etc.), and what versions of containers you want to use, e.g.:

```
COMPOSE_PROFILES=production
COMPOSE_FILE=docker-compose.yml:prod-docker-compose.yml
REGISTRY_TAG=latest
DOCKER_GID=999
PII_LOGGING_ENABLED=false
```

COMPOSE_PROFILES sets the docker compose profile to be used. If you look at docker-compose.yml, you will note some microservices are run only in the `test` profile. You can also make your own profile in a docker-compose file, and set it here.

DOCKER_GID can be obtained by running `grep docker /etc/group | awk -F: '{ print $3 }'`

`REGISTRY_TAG=latest` will use the most current stable IMAGE server components. Set to `unstable` to run pre-production (beta) versions.

`PII_LOGGING_ENABLED=false` will avoid logging any personally identifiable information (PII).
Make sure this aligns with your terms of service if you set it to `true` (useful for debugging on a test server).

The prod-docker-compose.yml file assumes you are doing routing via traefik, and uses the McGill server names.
You can override this in the prod-docker-compose.yml file to reflect your own server names and configuration.
If you don't want to pick up future changes to the base docker-compose.yml file, copy it instead of linking it.


The IMAGE microservices use cloud and other endpoints, for which you typically need credentials.
These should not be checked into git, of course!
Ensure the following files exist in `/var/docker/image/config/` and are populated with appropriate credentials:

```
apis-and-selection.env
azure-api.env
llm.env
maps.env
```

If a service is not in use, create an empty file to avoid startup errors.

Note that for the LLM used by multiple server components, we use a local instance of vLLM fronted by open-webui.
An easier alternative is to point to a cloud-based openai API compatible service for the LLM you wish to use.
We currently use qwen [GET DETAILED INFO FROM MIKE]


# JEFF EDITED TO HERE...

# Starting Services
Create the Traefik Network
If this is your first time:
docker network create traefik

Start Services
From the IMAGE-server root directory:
docker-compose up -d

Optional cleanup:
docker system prune

Verify running containers:
docker ps


# Why We Use Traefik
We use Traefik as the external reverse proxy for the IMAGE server stack. It allows us to:

- Automatically manage HTTPS with Let's Encrypt
- Route traffic to the correct service by hostname or path (e.g., /render → Orchestrator)
- Cleanly separate internal and external traffic

It works in combination with an internal nginx instance that forwards specific requests to services like the Orchestrator.

Example networking block in docker-compose.yml:

networks:
  traefik:
    external: true
    name: traefik
  default:
    name: image
Services must explicitly declare the network they connect to.

# Why We Use Ollama
Ollama is used to serve local LLMs for use with the text-followup preprocessor and others. It allows offline or low-latency processing and integrates with Open WebUI.
Key features:
- Accepts image and text input for multimodal tasks
- Loads large models locally
- Paired with Open WebUI

Configuration:
Store credentials and settings in config/ollama.env.


GPU Notes
Containers that require GPU include espnet-tts, text-followup, semantic-segmentation,object-detection, action-recognition, and so on.

If you see this error:

Cannot start service ...: could not select device driver "nvidia"

Make sure:
- nvidia-smi works
- The container is configured to use the NVIDIA runtime


# Docker Image Tagging
Docker images are tagged in four ways:
- latest: Stable, production-ready image
- unstable: Built from the main branch, less tested
- <timestamp>: Exact build time
- <version>: Explicit version number

We recommend:
- Use unstable for development
- Use latest for production


# Local vs Production Use
Local Testing
Use the default docker-compose.yml:
docker-compose up -d

Disable services not needed on your machine (especially GPU-based ones) to save resources.

Production Tips
Use latest tags
Use Traefik + Nginx for public access
Add replicas for audio services:


deploy:
  replicas: 2
  
Final Notes
This guide is intended to help you deploy IMAGE Server in a robust and flexible way, whether on a local machine or cloud host like AWS EC2. For more advanced deployments, monitoring, logging, and load balancing, consult the maintainers or reference our internal production setup (e.g., Pegasus).
