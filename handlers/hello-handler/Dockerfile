FROM node:alpine

RUN apk add --no-cache curl

WORKDIR /usr/src/app

# Apparently splittig this up is good for layers
# Docker images are onions
COPY /handlers/hello-handler/package*.json ./
RUN npm ci
COPY /handlers/hello-handler/*.json ./
COPY /handlers/hello-handler/.eslintrc.js ./
COPY /schemas src/schemas
COPY /config ./src/config
COPY /handlers/hello-handler/src ./src
RUN npm run build

ENV NODE_ENV=production

EXPOSE 80

USER node

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD [ "node", "dist/server.js" ]
