FROM node:alpine

WORKDIR /usr/src/app

# Apparently splittig this up is good for layers
# Docker images are onions
COPY /handlers/hello-haptics-handler/package*.json ./
RUN npm ci
COPY /handlers/hello-haptics-handler/*.json ./
COPY /handlers/hello-haptics-handler/.eslintrc.js ./
COPY /handlers/hello-haptics-handler/src ./src
COPY /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production

EXPOSE 80

USER node
CMD [ "node", "dist/server.js" ]
