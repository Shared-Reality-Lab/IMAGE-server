FROM node:alpine

# Set up permissions for logging
WORKDIR /var/log/IMAGE
RUN apk add supercronic
RUN chmod o+wx .

WORKDIR /usr/src/app
# Apparently splittig this up is good for layers
# Docker images are onions
COPY orchestrator/*.js* ./
RUN npm ci
COPY orchestrator/src ./src
COPY schemas src/schemas
RUN npm run build

COPY orchestrator/clean-cron ./clean-cron
RUN chown node:node clean-cron
RUN chmod 644 clean-cron

ENV NODE_ENV=production

EXPOSE 8080

USER node
CMD supercronic -quiet clean-cron & node dist/server.js
