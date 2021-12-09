FROM schemas:latest AS schemas

FROM node:alpine

RUN addgroup -g 4322 storage && addgroup node storage

WORKDIR /usr/src/app

COPY . /usr/src/app
RUN npm ci
COPY --from=schemas /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production
EXPOSE 80

USER node
CMD [ "node", "." ]
