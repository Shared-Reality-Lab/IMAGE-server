FROM node:alpine

RUN apk add --no-cache curl

WORKDIR /usr/src/app

# Apparently splittig this up is good for layers
# Docker images are onions
COPY /preprocessors/hello-preprocessor/package*.json ./
RUN npm ci
COPY /schemas src/schemas
COPY /preprocessors/hello-preprocessor/ .
RUN npm run build

ENV NODE_ENV=production
EXPOSE 8080
USER node

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

CMD [ "node", "dist/server.js" ]
