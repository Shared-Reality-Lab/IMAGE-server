FROM schemas:latest AS schemas

FROM node:alpine

# Set up permissions for logging
WORKDIR /var/log/IMAGE
RUN apk add supercronic
RUN mkdir temporary authorized
RUN chmod o+wx /var/log/IMAGE/temporary

WORKDIR /usr/src/app
# Apparently splittig this up is good for layers
# Docker images are onions
COPY *.js* ./
RUN npm ci
COPY src ./src
COPY --from=schemas /schemas src/schemas
RUN npm run build

COPY clean-cron ./clean-cron
RUN chown node:node clean-cron
RUN chmod 644 clean-cron

ENV NODE_ENV=production

EXPOSE 8080

USER node
CMD supercronic -quiet clean-cron & node dist/server.js
