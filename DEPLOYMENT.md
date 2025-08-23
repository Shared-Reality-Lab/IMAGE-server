# Deploying the IMAGE Server
IMAGE is a microservice-oriented stack where preprocessors, handlers, and services plug into a central orchestrator. Everything runs in Docker containers, wired together via Docker Compose.
The following information is meant to aid people in getting IMAGE running on their own so components can be used. It is based on what we've done for our testing and production environments, but by no means is this the only way to deploy. The general principles and concerns will likely be relevant.

# System Requirements & Dependencies
The following is written with the assumption you are running a Debian-based Linux distribution (e.g., Ubuntu 24.04, Debian 12). Other distributions may work but are not officially tested.

# Minimum System Requirements
- OS: Debian-based Linux (Ubuntu 24.04+ recommended) — Pegasus runs on Ubuntu 24.04 LTS, so we recommend using the latest LTS.
- CPU: At least 4 cores recommended - more cores improve parallel processing.
- RAM: 16GB or more recommended — Some services may require more RAM, especially if running multiple preprocessors concurrently.
- Storage: 50GB free, 100GB+ recommended if using a GPU.
- GPU: NVIDIA GPU required for certain services (some services will not run on CPU-only configurations).
** While AMD GPUs may work, we have not tested compatibility with AMD ROCm or other alternatives.

AWS EC2 Example Configuration
IMAGE Server was also successfully deployed on AWS EC2 using the configuration below:

- Instance Type: [Preferred] g5.xlarge (GPU) or t3.large (CPU-only)
- OS: Ubuntu 22.04 LTS
- CPU: 4 vCPUs
- RAM: 16 GiB (15 GiB usable)
- Storage: 1000GB EBS (Elastic Block Store)
- Network: Default VPC with public IPv4
- Security Group: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS) — Required for server & web-based access

Note: If using a CPU-only instance (t3.large), some preprocessors/services will not be available.

# Required Software
Install the following packages:
```
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git python3-pip
sudo apt install -y nvidia-driver nvidia-container-runtime  # For GPU-based services
```

Post-install steps:
```
sudo usermod -aG docker $USER
newgrp docker
reboot  # Required after NVIDIA driver install
```

Verify:
```
docker --version
docker-compose --version
nvidia-smi  # For GPU instances
```

# Clone the [IMAGE-server](https://github.com/Shared-Reality-Lab/IMAGE-server) repo
```
git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git
cd IMAGE-server
```

# Docker Compose Files
IMAGE runs entirely through Docker Compose. You’ll see several Compose files in the repo root:
- docker-compose.yml — the base stack. This is applied to any profile (test, production).
- test-docker-compose.yml — overrides for test/dev setups (we use Unicorn). 
- prod-docker-compose.yml — overrides for production setups (we use Pegasus).
- ec2-docker-compose.yml — overrides for our EC2 instance.
- docker-compose.override.yml — local overrides.

Docker Compose lets you layer files with -f flags, or list them in .env via COMPOSE_FILE. The next section covers how to populate the .env file.

# Environment Configuration
Docker Compose uses environment files to configure how services run. In IMAGE, you’ll usually work with two types of env files:

1. System-level .env (in repo root) — tells Compose which profiles and files to load.
    Let’s look at the root .env. 
    This is our unicorn .env file, which is our test server:
  ```
  # Do not add any secrets in this file
  COMPOSE_PROFILES=test  # or COMPOSE_PROFILES=production
  COMPOSE_FILE=docker-compose.yml:test-docker-compose.yml:docker-compose.override.yml  # a colon-separated list of compose files to apply in order (base -> test overrides -> local overrides)
  REGISTRY_TAG=unstable   # Docker image tag to use (unstable for development, latest for production).
  DOCKER_GID=134 # find your Docker group ID by doing `grep docker /etc/group | awk -F: '{ print $3 }'`
  PII_LOGGING_ENABLED=true  # Flag to control whether Personally Identifiable Information logging is active (true/false)
  ```
2. Env files in config/ — either Infrastructure / script envs, or component-specific envs.
    
    a) Infrastructure / script envs: These control our own tooling (deployment, logging, scripts). We abstracted repo URLs, directory lists, Slack API keys, and log locations, and store them in a .env file eponymous with the name of the script (in the `scripts/` dir) for convenience. You may find it beneficial to use our healthcheck script for instance, which polls through each microservice and reports if they can hit the /health endpoint defined in each component. Therefore, a `healthcheck.env` would store the API key for Slack (where we have hourly reporting), and the log location. 
    
    b) Component-specific envs: These configure runtime services (preprocessors, handlers, or standalone services) which are consumed by containers at runtime. They often hold API keys, model names, or URLs.
    In the docker-compose, each service that requires an env file has an env_file block like so:
    ```
    env_file:
      - config/ollama.env
    ```
    Ensure the following files exist in the config/ folder and are populated with appropriate credentials:

    apis-and-selection.env, azure-api.env, llm.env, maps.env
    
    If a service is not in use, simply create an empty file with the same name to avoid startup errors.
    Here is a command to create them all:
    `touch config/{maps.env,express-common.env,llm.env,azure-api.env}`


# Starting Services
To start the services, you need to be in the directory where your docker compose is located.

First, ceate the Traefik Network if this is your first time: 
`docker network create traefik`

Then, you can start services:

From the IMAGE-server root directory:
`docker-compose up -d`

Tips:

Optional cleanup:
`docker system prune`

Verify running containers:
`docker ps`


# Why We Use Traefik
We use Traefik as the external reverse proxy for the IMAGE server stack. It allows us to:

- Automatically manage HTTPS with Let's Encrypt
- Route traffic to the correct service by hostname or path (e.g., /render → Orchestrator)
- Cleanly separate internal and external traffic

It works in combination with an internal nginx instance that forwards specific requests to services like the Orchestrator. Traefik only needs to reach the services you want public; the rest stay on the internal image network. In our docker-compose, we connect `monarch-link-app` and `tat` to Traefik for this reason.

Example networking block in docker-compose.yml:
```
networks:
  traefik:
    external: true
    name: traefik
  default:
    name: image
```
Services must explicitly declare the network they connect to.

Traefik itself lives in a separate compose (it’s just another container) and exposes ports 80/443 on the host.

# Why We Use Ollama
Ollama is the local LLM runtime. It’s not a preprocessor itself; instead, several preprocessors in IMAGE-server call out to whatever LLM endpoint you configure (Ollama locally, or a remote API if you set one). Currently the following preprocessors connect to the LLM via env_file `./config/llm.env`: content-categoriser, graphic-caption, text-followup, and multistage-diagram-segmentation. It allows offline or low-latency processing and integrates with Open WebUI.
Key features:
- Accepts image and text input for multimodal tasks
- Loads large models locally
- Paired with Open WebUI

Configuration:
Store credentials and settings in config/ollama.env. [Guidelines on how to set this up wcan be found here](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/text-followup).

Similar to Traefik, Ollama (or vLLM) works the same way: it’s not baked into IMAGE-server, but runs in its own stack and IMAGE preprocessors talk to it via HTTP.
Within the ollama `docker-compose.yml`, you'll find services like:
- ollama: pulls `ollama/ollama:latest`, exposes port 11434.
- vllm: runs `vllm/vllm-openai:latest`, reserves a GPU, serves an OpenAI-style API at port 8000.
- open-webui: optional WebUI that connects to Ollama or vLLM and is exposed via Traefik with a hostname like `ollama.unicorn.cim.mcgill.ca`.


GPU Notes
Some containers that require GPU include espnet-tts, text-followup, semantic-segmentation,object-detection, action-recognition, and so on. You can see which ones need GPU directly in docker-compose.yml—they either include a `deploy.resources.reservations.devices` stanza with `driver: nvidia`. 

If you see this error:
Cannot start service ...: could not select device driver "nvidia"
Common error & fixes

Error:

Cannot start service <name>: could not select device driver "nvidia"

Fix checklist:

- Host GPUs present: `nvidia-smi` works on the host.
- Toolkit configured: `nvidia-container-toolkit` installed and Docker restarted.
- Compose GPU config present: service has either `deploy.resources.reservations.devices` with `driver: nvidia` (or similar).

Performance tips:
Within our `scripts/` directory, we provide a [warmup script](https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/scripts/warmup) that hits model-loading endpoints to cold-start model load and reduce first-request latency.

# Docker Image Tagging
Docker images are tagged in four ways:
- latest: Stable, production-ready image
- unstable: Built from the main branch, less tested
- `<timestamp>`: Exact build time
- `<version>`: Explicit version number

We recommend:
- Use unstable for development
- Use latest for production

As described earlier in the `.env` file in root, you can set the default tag there. To update containers to a new tag, you can:
```
docker-compose pull
docker-compose up -d
```

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
