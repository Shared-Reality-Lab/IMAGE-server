#!/bin/sh

if [ -z "$1" ]; then
  echo "<container_name> Health Check"
  exit 1
fi

CONTAINER_NAME=$1

#loading the slack webhook
. ./config/preprocessors-slack-webhook.env

SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
echo "Using Slack Webhook: $SLACK_WEBHOOK_URL"

if [ -z "$SLACK_WEBHOOK_URL" ]; then
  echo "Slack webhook URL is not configured correctly. Exiting."
  exit 1
fi

# check the health status of the container
health_status=$(docker inspect --format='{{json .State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null)

# If the container doesn't have health check defined, report failure
if [ -z "$health_status" ]; then
  health_status="unavailable"
fi

# Notify via Slack if the container is not healthy (Will remove the healthy once tested)
if [ "$health_status" != "\"healthy\"" ]; then
    message="Container *$CONTAINER_NAME* health check failed with status: *$health_status*"
else
    message="Container *$CONTAINER_NAME* is healthy."
fi

response=$(curl -X POST --data-urlencode "payload={\"channel\": \"#preprocessors\", \"username\": \"docker-health-check\", \"text\": \"$message\"}" $SLACK_WEBHOOK_URL 2>/dev/null)

if [ "$response" = "ok" ]; then
    echo "Message successfully posted to Slack."
else
    echo "Failed to post message to Slack: $response"
fi
