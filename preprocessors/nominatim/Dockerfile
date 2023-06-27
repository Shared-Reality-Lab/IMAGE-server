FROM node:alpine as builder

WORKDIR /usr/src/app
COPY /preprocessors/nominatim/ /usr/src/app
RUN npm ci
COPY /schemas src/schemas
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
