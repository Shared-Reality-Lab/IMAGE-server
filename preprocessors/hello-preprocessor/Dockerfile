FROM node:alpine

WORKDIR /usr/src/app

# Apparently splittig this up is good for layers
# Docker images are onions
COPY /preprocessors/hello-preprocessor/package*.json ./
RUN npm ci
COPY /preprocessors/hello-preprocessor/ .
COPY /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production

EXPOSE 8080

USER node
CMD [ "node", "dist/server.js" ]
