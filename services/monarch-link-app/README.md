This is the app used to connect IMAGE-TactileAuthoring to IMAGE-Monarch. 

# Monarch Link App

![license: AGPL](https://img.shields.io/badge/license-AGPL-success) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-service-monarch-link-app)

## Overview

This is the containerized version of a web app used to publish content from [IMAGE-TactileAuthoring](https://github.com/Shared-Reality-Lab/IMAGE-TactileAuthoring) which can then be fetched by [IMAGE-Monarch client](https://github.com/Shared-Reality-Lab/IMAGE-Monarch). It stores the data in a json file data.json which is recreated each time the container is restarted. 

This container runs on port 80.

## Endpoints
- POST `https://unicorn.cim.mcgill.ca/image/monarch/create/` where the body is a JSON object with the key `data` set to the SVG in base64 format,  `title` set to a familiar name to refer to the channel, and `layer` set to the layer to be shown or None if no default layer is selected. An automatically generated `id`, a unique channel identifier (referred to as the "subscribed_code"), and `secret`, which is a secret key required to make further edits to the data, are returned. 
- POST `https://unicorn.cim.mcgill.ca/image/monarch/update/<subscribed_code>` where the body is a JSON object with the key `data` set to the SVG in base64 format, `secret` set to the secret key, `title` set to a familiar name to refer to the channel, and `layer` set to the layer to be shown or None if no default layer is selected. 
This can be used to create a new channel `<subscribed_code>` if one doesn't already exist. The data is stored in data.json. If `<subscribed_code>` already exists the `data` field corresponding it is changed only if the `secret` field matches the secret key when the channel was created. 
- GET `https://unicorn.cim.mcgill.ca/image/monarch/display/<subscribed_code>` returns a JSON object with the [tactile svg schema](https://github.com/Shared-Reality-Lab/IMAGE-server/blob/24a41b4f36a8c89b1a94d7c31388703ece8c81c7/renderers/tactilesvg.schema.json).
