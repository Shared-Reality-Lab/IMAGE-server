FROM node:alpine

RUN addgroup -g 4322 storage && addgroup node storage

WORKDIR /usr/src/app

COPY /handlers/generic-tts-handler/*.js* ./
RUN npm ci
COPY /handlers/generic-tts-handler/src ./src
COPY /handlers/generic-tts-handler/types ./types
COPY /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production
EXPOSE 80

USER node
CMD [ "node", "." ]
