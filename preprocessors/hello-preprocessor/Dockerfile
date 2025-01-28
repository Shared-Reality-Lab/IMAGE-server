FROM node:alpine

WORKDIR /usr/src/app

# Apparently splittig this up is good for layers
# Docker images are onions
COPY /preprocessors/hello-preprocessor/package*.json ./
RUN npm ci
COPY /schemas src/schemas
COPY /config /app/config
COPY /preprocessors/hello-preprocessor/ .
RUN npm run build

ENV NODE_ENV=production

EXPOSE 8080

USER node
CMD [ "node", "dist/server.js" ]
