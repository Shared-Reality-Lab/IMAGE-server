FROM node:alpine as builder


WORKDIR /usr/src/app
COPY orchestrator/*.js* ./
RUN npm ci
COPY orchestrator/src ./src
COPY schemas src/schemas
RUN npm run build && npm prune --production

FROM node:alpine as final

RUN apk add memcached
# Remove telnet later
RUN apk add telnet
# Set up for logging
WORKDIR /var/log/IMAGE
RUN apk add supercronic
RUN chmod o+wx .

WORKDIR /usr/src/app
COPY orchestrator/clean-cron ./clean-cron
RUN chown node:node clean-cron
RUN chmod 644 clean-cron

COPY --from=builder --chown=node:node /usr/src/app/*.js* ./
COPY --from=builder --chown=node:node /usr/src/app/dist ./dist
COPY --from=builder --chown=node:node /usr/src/app/node_modules ./node_modules

ENV NODE_ENV=production

EXPOSE 8080

USER node
CMD supercronic -quiet clean-cron & node dist/server.js
