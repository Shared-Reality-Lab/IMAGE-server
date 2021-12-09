FROM schemas:latest AS schemas

FROM node:alpine

RUN addgroup -g 4322 storage && addgroup node storage

WORKDIR /usr/src/app
RUN chown node:storage .
USER node

COPY *.js* ./
RUN npm ci
COPY src ./src
COPY types ./types
COPY --from=schemas /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production
EXPOSE 80

CMD [ "node", "." ]
