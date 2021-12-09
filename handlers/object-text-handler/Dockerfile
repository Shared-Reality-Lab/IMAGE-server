FROM schemas:latest AS schemas

FROM node:alpine

WORKDIR /usr/src/app
RUN chown node:node .
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
