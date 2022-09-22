#!/bin/bash

#first check if no one's using the override
cd /var/docker/atp
docker-compose stop ocr-clouds-preprocessor
rm docker-compose.override.yml