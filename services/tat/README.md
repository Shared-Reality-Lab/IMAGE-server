# Tactile Authoring Tool (TAT)

![license: AGPL](https://img.shields.io/badge/license-AGPL-success) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-service-tat)

## Overview

This is the containerized version of the web app [IMAGE-TactileAuthoring](https://github.com/Shared-Reality-Lab/IMAGE-TactileAuthoring) used to publish to [IMAGE-Monarch client](https://github.com/Shared-Reality-Lab/IMAGE-Monarch) via [monarch-link-app](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/services/monarch-link-app).

While this app is included in the same docker-compose as other components of the IMAGE architecture, it is not a "service" in the specific sense the term is used within the IMAGE architecture. This web app is not used by any handlers/preprocessors within IMAGE. Instead, it is a standalone application related to IMAGE and is included in the docker-compose solely for convenience and ease of deployment.

This container runs on port 80.

## Endpoints
- GET `https://tat.unicorn.cim.mcgill.ca/` opens the web application on a web browser. It has been tested for Chrome (but could also work for recent versions of Safari and Firefox as per [the application's parent repo](https://github.com/SVG-Edit/svgedit))
