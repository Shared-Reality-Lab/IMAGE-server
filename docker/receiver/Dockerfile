FROM schemas:latest AS schemas

FROM node:lts-alpine

WORKDIR /usr/src/app
# Apparently splittig this up is good for layers
# Docker images are onions
COPY package*.json ./
RUN npm ci
COPY . .
COPY --from=schemas /schemas/request.schema.json src/
RUN npm run build

ENV NODE_ENV=production

EXPOSE 8080

CMD [ "node", "dist/server.js" ]
