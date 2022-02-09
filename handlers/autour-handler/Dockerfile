FROM node:alpine

RUN addgroup -g 4322 storage && addgroup node storage

WORKDIR /usr/src/app

COPY /handlers/autour-handler/*.js* ./
RUN npm ci
COPY /handlers/autour-handler/src ./src
COPY /handlers/autour-handler/types ./types
COPY /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production
EXPOSE 80

USER node
CMD [ "node", "." ]
