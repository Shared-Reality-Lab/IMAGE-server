FROM node:lts-alpine

WORKDIR /usr/src/app
# Apparently splittig this up is good for layers
# Docker images are onions
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

ENV NODE_ENV=production

EXPOSE 80

CMD [ "node", "dist/server.js" ]
