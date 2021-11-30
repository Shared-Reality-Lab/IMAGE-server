FROM schemas:latest AS schemas

FROM node:alpine

WORKDIR /usr/src/app
# Apparently splittig this up is good for layers
# Docker images are onions
COPY package*.json ./
RUN npm ci
COPY *.json ./
COPY .eslintrc.js ./
COPY src ./src
COPY --from=schemas /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production

EXPOSE 80

CMD [ "node", "dist/server.js" ]
