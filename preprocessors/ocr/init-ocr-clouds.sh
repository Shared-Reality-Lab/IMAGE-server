#!/bin/bash

#first check there isn't already an override
cd /home/danpecor/repo/IMAGE-server
docker build -t ocr-clouds-preprocessor:test -f preprocessors/ocr/Dockerfile .
cp docker-compose.override.yml ../../../../var/docker/atp
cd /var/docker/atp
docker-compose up -d ocr-clouds-preprocessor
docker inspect atp-orchestrator | grep IPAddress