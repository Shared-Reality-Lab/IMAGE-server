FROM node:alpine as builder

WORKDIR /usr/src/app

# Apparently splittig this up is good for layers
# Docker images are onions
COPY /handlers/hello-haptics-handler/package*.json ./
RUN npm ci
COPY /handlers/hello-haptics-handler/*.json ./
COPY /handlers/hello-haptics-handler/.eslintrc.js ./
COPY /handlers/hello-haptics-handler/src ./src
COPY /schemas src/schemas
RUN npm run build && npm prune --production

FROM node:alpine as final

WORKDIR /usr/src/app
COPY --from=builder --chown=node:node /usr/src/app/package*.json ./
COPY --from=builder --chown=node:node /usr/src/app/dist ./dist
COPY --from=builder --chown=node:node /usr/src/app/node_modules ./node_modules

ENV NODE_ENV=production

EXPOSE 80

USER node
CMD [ "node", "dist/server.js" ]
