FROM node:alpine

RUN addgroup -g 4322 storage && addgroup node storage
WORKDIR /usr/src/app
COPY /handlers/photo-audio-handler/ /usr/src/app
RUN npm ci
COPY /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production
EXPOSE 80
USER node
CMD [ "node", "." ]
