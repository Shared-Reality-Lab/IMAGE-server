FROM node:alpine as builder

RUN addgroup -g 4322 storage && addgroup node storage
WORKDIR /usr/src/app
COPY /handlers/osm-streets-handler/ /usr/src/app
RUN npm ci
COPY /schemas src/schemas
COPY /config /app/config
RUN npm run build && npm prune --production

FROM node:alpine as final

WORKDIR /usr/src/app
COPY --from=builder --chown=node:node /usr/src/app/dist ./dist
COPY --from=builder --chown=node:node /usr/src/app/node_modules ./node_modules
COPY --from=builder --chown=node:node /usr/src/app/package*.json ./

ENV NODE_ENV=production
EXPOSE 80
USER node
CMD [ "node", "." ]
