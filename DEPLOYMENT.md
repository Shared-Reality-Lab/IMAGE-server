# Deploying the IMAGE Server
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
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git python3-pip
sudo apt install -y nvidia-driver nvidia-container-runtime  # For GPU-based services

Post-install steps:
sudo usermod -aG docker $USER
newgrp docker
reboot  # Required after NVIDIA driver install

Verify:
docker --version
docker-compose --version
nvidia-smi  # For GPU instances

# Cloning the Repository
git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git
cd IMAGE-server

# Environment Configuration
Docker Group ID
Find your Docker group ID:

grep docker /etc/group | awk -F: '{ print $3 }'
Add this value to your .env file:
DOCKER_GID=122  # Replace with your actual Docker group ID


# API Key Setup
Ensure the following files exist in the config/ folder and are populated with appropriate credentials:
apis-and-selection.env
azure-api.env
ollama.env
maps.env

If a service is not in use, simply create an empty file with the same name to avoid startup errors.

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
