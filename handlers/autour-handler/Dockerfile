FROM node:alpine as builder

RUN addgroup -g 4322 storage && addgroup node storage

WORKDIR /usr/src/app

COPY /handlers/autour-handler/*.js* ./
RUN npm ci
COPY /handlers/autour-handler/src ./src
COPY /handlers/autour-handler/types ./types
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
CMD [ "node", "." ]
