# Deploying the IMAGE Server
IMAGE is a Docker microservice-oriented stack where preprocessors, handlers, and services plug into a central orchestrator, all deployed via Docker Compose.
This describes the IMAGE team's reference server deployment, which can be used as a starting point for running your own IMAGE server.
If you aren't familiar with Docker, you will struggle to set up an IMAGE server from scratch.
High level steps for deployment:

1. Install Debian server (We use Ubuntu LTS), whether on a local machine, or in the cloud (we have used Amazon EC2)
2. Install and configure base tools including Docker and GPU driver
3. Set up your directory structure, clone the IMAGE server repository, and configure links
4. Decide how you will handle routing (we use traefik), and encryption (easy if you use traefik!)
5. Set up config files for accessing external tools like an LLM
6. Run the imageup script to bring up the entire IMAGE server stack
7. Point the IMAGE browser extension to your server via the options page
8. Know how to keep your IMAGE server updated

# Minimum System Requirements
System requirements vary depending on what components you will run, and how loaded you expect your server to be. For reference, we run a test server with a Ryzen 3800x CPU, 32GB RAM, 1GB NVMe, and a couple of older NVidia GPUs (Titan XP and 1660ti). This is fine for testing, including running a very small local LLM. Our production reference server is beefier, with a Ryzen 7950x CPU, 5090 NVidia GPU, 64GB RAM, 2TB NVMe. Anecdotal load testing indicates that the production reference server responds to most requests in roughly 5 seconds, and can support multiple users all making overlapping requests from the browser extension as fast as they can (although response time increases).

Pretty much any IMAGE server will require a GPU for running local ML models and services. However, if you use a remote API for LLM functionality, an 8GB VRAM GPU can be sufficient for running the smaller local models that provide, for example, text-to-speech. We expect that it will soon be possible to run an IMAGE server without any local GPU resources, and only use cloud endpoints, but at least a small GPU is currently required. If you run a local LLM, anticipate using approximately 20GB of GPU VRAM total for reasonable response quality.

AWS EC2 Example Configuration:
- Instance Type: g5.xlarge (GPU)
- OS: Ubuntu 22.04 LTS (not yet tested on later LTS releases)
- CPU: 4 vCPUs
- RAM: 16 GiB (15 GiB usable)
- Storage: 1000GB EBS (Elastic Block Store)
- Network: Default VPC with public IPv4
- Security Group: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS) — Required for server & web-based access


# Required Software - System Setup
Install the following packages:
```
sudo apt update && sudo apt upgrade -y    # refreshes the package index and upgrades any out-of-date base packages, which is crucial for installing Docker/NVIDIA tooling.
sudo apt install -y docker.io docker-compose git python3-pip 
sudo apt install -y nvidia-driver nvidia-container-runtime  # For GPU-based services
```
- nvidia-driver is needed so that the server can communicate with NVIDIA GPUs. Without this, GPU-accelerated preprocessors (like segmentation or local LLMs) won’t run.
- nvidia-container-runtime integrates NVIDIA GPUs into Docker. Without this, Compose won’t recognize your GPUs.

Post-install steps:
```
sudo usermod -aG docker $USER    # By default, only root can run Docker. Adding your user to the docker group allows you to run Docker commands without sudo
newgrp docker    # Refreshes, so you don’t need to log out/in before using Docker as a non-root user.
reboot  # Required after NVIDIA driver install
```

Verify:

`docker --version`

`docker-compose --version`

`nvidia-smi  # For GPU instances. This should display driver version and usage.`

# Clone the [IMAGE-server](https://github.com/Shared-Reality-Lab/IMAGE-server) repo
We strongly recommend putting all of the IMAGE server components in the directory `/var/docker/image`. Although mostly abstracted, if you use another directory, you may need to adjust scripts.

In `/var/docker/image`, clone the IMAGE server repository:
```
git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git
cd IMAGE-server
```

# Docker Compose Files
IMAGE runs entirely through Docker Compose. You’ll see several Compose files in the repo root:
- docker-compose.yml — the base stack. This is applied to any profile (test, production).
- test-docker-compose.yml — overrides for test/dev setups (for us, unicorn.cim.mcgill.ca). 
- prod-docker-compose.yml — overrides for production setups (for us, pegasus.cim.mcgill.ca).
- ec2-docker-compose.yml — overrides for our EC2 instance.
- docker-compose.override.yml — optional overrides for local development.

Docker Compose lets you layer files with -f flags, or list them in .env via COMPOSE_FILE. The next section covers how to populate the .env file.

# Environment Configuration

We place everything under `/var/docker/image` to keep a clean separation between the IMAGE-server respository and the server's working directory. By soft-linking into the repo where needed, we keep configs and overrides outside of Git, but still in the right place for Docker Compose to find them.

In the same directory (`/var/docker/image` or equivalent), make the following soft links, to get access to scripts and configuration, and copy the [prod-docker-compose.yml](https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/prod-docker-compose.yml) file so you can modify it to reflect your server configuration:
```
ln -s /var/docker/image/IMAGE-server/scripts ./bin
ln -s IMAGE-server/config ./config
ln -s  IMAGE-server/docker-compose.yml ./docker-compose.yml
cp IMAGE-server/prod-docker-compose.yml ./prod-docker-compose.yml
```
Docker Compose uses environment files to configure how services run. In IMAGE, you’ll usually work with two types of env files:

1. System-level .env (in repo root) — tells Compose which profiles and configs to load.
    For example, this is our production reference server pegasus.cim.mcgill.ca .env file:
  ```
    # Do not add any secrets in this file
    COMPOSE_PROFILES=production    # or test
    COMPOSE_FILE=docker-compose.yml:prod-docker-compose.yml    # colon-separated ordered list of compose files to apply
    REGISTRY_TAG=latest    # Docker image tag (unstable for development, latest for production). More info below.
    DOCKER_GID=999    # find your Docker group ID with `grep docker /etc/group | awk -F: '{ print $3 }'`
    PII_LOGGING_ENABLED=false    # Flag to control whether Personally Identifiable Information logging is active (true/false)
  ```
    Note: PII_LOGGING_ENABLED=false will avoid logging any personally identifiable information (PII). Make sure this aligns with your terms of service if you set it to true (useful for debugging on a test server).

2. Env files in `/var/docker/image/config/` :
    
    a) Infrastructure / script envs: These helper scripts control our own tooling (deployment, logging, scripts). We abstracted repo URLs, directory lists, Slack API keys, and log locations, and store them in a .env file eponymous with the name of the script (in the `/var/docker/image/IMAGE-server/scripts/` dir). You may find it beneficial to use our healthcheck script for instance, which polls each microservice and reports if it can hit the /health endpoint. For reporting, our `healthcheck.env` stores the API key for our team's Slack, and the log location. 
    
    b) Component-specific envs: These configure runtime services (preprocessors, handlers, or standalone services) which are loaded by containers at runtime. They often hold API keys, model names, or URLs that you don't want to check into git. Filenames are specified in docker-compose.
    For example, ensure the following files exist in the config/ folder and are populated with appropriate credentials:

    `apis-and-selection.env, azure-api.env, llm.env, maps.env`
    
    If a service is not in use, simply create an empty file with the same name to avoid startup errors.
    Here is a command to create them all:
    `touch config/{maps.env,express-common.env,llm.env,azure-api.env}`

    TIP: once completed, these files include credentials that should not be committed in Git!

# Starting Services
To start the services, cd to `/var/docker/image`.

First, create the Traefik Network if this is your first time. Any external network in Docker Compose isn't automatically created. If a docker-compose.yml defines a network as [`external: true` (like we do with traefik)](https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/docker-compose.yml#L617), Compose expects that network to already exist - it wont create it for you, because "external" implies 'managed outside this Compose stack':

`docker network create traefik`

Then, you can start the services. We ship a helper script called [`imageup`](https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/scripts/imageup) (in `scripts/`) to bring up all the services. It’s the same script we use on our own production and test servers.
Make sure you're in the `/var/docker/image` directory, and run `./bin/imageup`. It pulls the latest code and Docker images from GitHub/registry, ensures the Git repo is clean and up to date, brings services up with the correct env files, removes stale containers and network, and abstracts away the docker-compose incantations (so you don’t forget to include prod-docker-compose.yml or the right .env). 

You can also start services using `docker-compose up -d`. This will just launch containers using your current .env and COMPOSE_FILE. It does not:
Pull the latest images, reset Git or overrides, remove stale containers, or warm up models.

TIP: Clean up old Docker containers, images, etc. that are clogging your drive: `docker system prune`

TIP: Verify running containers with `docker ps`


# Traefik, or another reverse proxy
We use Traefik as the reverse proxy to:

- Automatically manage HTTPS with Let's Encrypt
- Route traffic to the correct service by hostname or path (e.g., /render → Orchestrator)
- Cleanly separate internal and external network traffic

It works in combination with an internal nginx instance that forwards specific requests to services like the Orchestrator. Traefik only needs to reach the services you want public; the rest stay on the internal image network. For example, we connect the orchestrator, plus `monarch-link-app` and `tat` to Traefik since they need to be exposed publicly.

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

Traefik itself lives in a separate compose (it’s just another container) and exposes ports 80/443 on the host. Following our setup on `/var/docker/image` above, we place this docker compose in `/var/docker/traefik`.

Below is our traefik docker-compose.yml on our production server:
```
services:
    traefik:
        image: "traefik:3.1"
        container_name: "pegasus-traefik"
        restart: unless-stopped
        command:
            # Basic config
            - "--providers.docker=true"
            - "--providers.docker.exposedbydefault=false"
            # Set up HTTP(S) and redirects
            - "--entrypoints.web.address=:80"
            - "--entrypoints.websecure.address=:443"
            - "--entrypoints.web.http.redirections.entryPoint.to=websecure"
            - "--entrypoints.web.http.redirections.entryPoint.scheme=https"
            # Set up TLS with LetsEncrypt
            #- "--certificatesresolvers.myresolver.acme.tlsChallenge=true"
            - "--certificatesresolvers.myresolver.acme.httpchallenge.entrypoint=web"
            - "--certificatesresolvers.myresolver.acme.email=juliette@cim.mcgill.ca"
            - "--certificatesresolvers.myresolver.acme.storage=/var/letsencrypt/acme.json"
            # Logging & Debugging
            - "--log.level=DEBUG"    # Can be ERROR (default), DEBUG, PANIC, FATAL, WARN, and INFO
            #- "--api.insecure=true"
        ports:
            - "80:80"
            - "443:443"
        volumes:
            - "/var/run/docker.sock:/var/run/docker.sock:ro"
            - "letsencrypt:/var/letsencrypt"

    test:
        image: "nginx"
        container_name: "test-nginx"
        labels:
            - "traefik.enable=true"
            - "traefik.http.routers.test-nginx.rule=Host(`pegasus.cim.mcgill.ca`) && Path(`/test`)"
            - "traefik.http.routers.test-nginx.tls.certresolver=myresolver"

volumes:
    letsencrypt:

networks:
    default:
        name: traefik
```

# Connecting to, or running your own, visual LLM
Since multiple IMAGE preprocessors us a visual LLM (currently qwen), you need to either specify a cloud endpoint, or run your own LLM locally on your server.
Our production reference server uses vLLM as the runtime for LLM models.
Like Traefik, it runs with its own docker-compose in its own directory on our server (e.g., `/var/docker/ollama`).
It’s not a preprocessor itself; instead, several preprocessors in IMAGE-server call out to whatever LLM endpoint you configure (Ollama/vLLM locally, or a remote API if you set one). For example, the following preprocessors connect to the LLM via env_file `/var/docker/image/config/llm.env`: content-categoriser, graphic-caption, text-followup, and multistage-diagram-segmentation.
Key features:
- Accepts multimodal graphic and text prompots
- Loads models within GPU memory constraints
- Optional: Can use Open WebUI as a front-end for manual testing

Configuration:
Store credentials and settings in `/var/docker/image/config/[vllm,ollama].env. [Example of how to set this up](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors/text-followup).

Similar to Traefik, Ollama (or vLLM) is not baked into IMAGE-server, but runs in its own stack and IMAGE preprocessors talk to it via HTTP. For example, using a separate docker-compose file in `/var/docker/ollama`.
You must specifiy services such as:
- ollama: pulls `ollama/ollama:latest`, exposes port 11434.
- vllm: runs `vllm/vllm-openai:latest`, reserves a GPU, serves an OpenAI-style API at port 8000.
- open-webui: optional WebUI that connects to Ollama or vLLM and is exposed via Traefik with a hostname like `ollama.unicorn.cim.mcgill.ca`.


GPU Notes:
Some containers that require GPU (and don't use a cloud endpoint or the LLM) include espnet-tts, text-followup, semantic-segmentation,object-detection, action-recognition, and so on. You can see which ones need GPU directly in docker-compose.yml since they include a `deploy.resources.reservations.devices` stanza with `driver: nvidia`. 

TIP: if you run into `Cannot start service ...: could not select device driver "nvidia"`, you can use this checklist to guide you:

- Host GPUs present: `nvidia-smi` works on the host.
- Toolkit configured: `nvidia-container-toolkit` installed and Docker restarted.
- Compose GPU config present: service has either `deploy.resources.reservations.devices` with `driver: nvidia` (or similar).


TIP: In `/var/docker/image/IMAGE-server/scripts/`, we provide a [warmup script](https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/scripts/warmup) that hits model-loading endpoints to cold-start model load and reduce first-request latency.
On a slow server, the first request can even cause failures due to timeouts, which the warmup helps avoid.
Note that the warmups are automatically called if you use the `imageup` script.


# Docker Image Tags & Keeping IMAGE-Server Up-to-Date
Docker images are tagged:
- latest: Stable, production-ready image
- unstable: Built from the main branch, less tested
- `<timestamp>`: Exact build time
- `<version>`: Explicit version number

We recommend `unstable` for development and `latest` for production

As described earlier, you can set the default tag in `/var/docker/image/.env`.
```
REGISTRY_TAG=latest   # use 'unstable' for test
```

The `imageup` script already runs `docker compose pull` and `docker compose up -d` for you, along with cleanup and warmup. Re-run `./bin/imageup` to ensure you’re running the latest images for your selected tag.

Alternatively, you could run:
```
docker-compose pull    # fetch latest images for the current tag
docker-compose up -d    # restart containers with those images
```

Note: if you’ve made local changes to Dockerfiles or compose files, imageup may overwrite them when pulling from Git.


# Tips & Tricks
- 
