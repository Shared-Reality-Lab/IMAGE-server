FROM node:alpine

WORKDIR /usr/src/app

COPY /handlers/object-text-handler/*.js* ./
RUN npm ci
COPY /handlers/object-text-handler/src ./src
COPY /handlers/object-text-handler/types ./types
COPY /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production
EXPOSE 80

USER node
CMD [ "node", "." ]
