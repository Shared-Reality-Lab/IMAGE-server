FROM node:alpine as builder

RUN addgroup -g 4322 storage && addgroup node storage
WORKDIR /usr/src/app
COPY /handlers/photo-audio-haptics-handler/ /usr/src/app
RUN npm ci
COPY /schemas src/schemas
COPY /config ./src/config
RUN npm run build && npm prune --production

FROM node:alpine as final

RUN apk add --no-cache curl

WORKDIR /usr/src/app
COPY --from=builder --chown=node:node /usr/src/app/package*.json ./
COPY --from=builder --chown=node:node /usr/src/app/dist ./dist
COPY --from=builder --chown=node:node /usr/src/app/node_modules ./node_modules

ENV NODE_ENV=production
EXPOSE 80
USER node

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD [ "node", "." ]
