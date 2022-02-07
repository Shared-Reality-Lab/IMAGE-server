FROM node:alpine

WORKDIR /usr/src/app
# Apparently splittig this up is good for layers
# Docker images are onions
COPY orchestrator/package*.json ./
RUN npm ci
COPY orchestrator .
COPY schemas src/schemas
RUN npm run build

ENV NODE_ENV=production

EXPOSE 8080

USER node
CMD [ "node", "dist/server.js" ]
