FROM node:alpine AS builder

WORKDIR /usr/src/app
COPY /handlers/motd/ /usr/src/app
RUN npm ci
COPY /schemas src/schemas
COPY /config src/config/ 
RUN npm run build && npm prune --production

FROM node:alpine AS final

RUN apk add --no-cache curl

WORKDIR /usr/src/app
COPY --from=builder --chown=node:node /usr/src/app/dist ./dist
COPY --from=builder --chown=node:node /usr/src/app/node_modules ./node_modules
COPY --from=builder --chown=node:node /usr/src/app/package*.json ./

ENV NODE_ENV=production
EXPOSE 80
USER node

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

CMD [ "node", "." ]
