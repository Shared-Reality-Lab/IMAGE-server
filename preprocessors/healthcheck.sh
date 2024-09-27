#!/bin/bash

if [ -z "$1" ]; then
  echo "<container_name> Health Check"
  exit 1
fi

CONTAINER_NAME=$1

SLACK_WEBHOOK_URL="https://hooks.slack.com/services/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"

# check the health status of the container
health_status=$(docker inspect --format='{{json .State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null)

# If the container doesn't have health check defined, report failure
if [ -z "$health_status" ]; then
  health_status="unavailable"
fi

# Notify via Slack if the container is not healthy (Will remove the healthy once tested)
if [ "$health_status" != "\"healthy\"" ]; then
    response=$(curl -X POST --data-urlencode "payload={\"channel\": \"#preprocessors\", \"username\": \"docker-health-check\", \"text\": \"Container *$CONTAINER_NAME* is healthy.\"}" $SLACK_WEBHOOK_URL 2>/dev/null)

    if [ "$response" == "ok" ]; then
        echo "Message successfully posted to Slack."
    else
        echo "Failed to post message to Slack: $response"
    fi
    
else
  curl -X POST --data-urlencode "payload={\"channel\": \"#preprocessors\", \"username\": \"docker-health-check\", \"text\": \"Container *$CONTAINER_NAME* is healthy.\"}" $SLACK_WEBHOOK_URL
fi


## how could tjos fial?