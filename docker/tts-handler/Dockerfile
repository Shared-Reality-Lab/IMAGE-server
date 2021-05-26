FROM schemas:latest AS schemas

FROM node:alpine
WORKDIR /usr/src/app

COPY *.js* ./
RUN npm ci
COPY src ./src
COPY --from=schemas /schemas src/schemas
RUN npm run build

ENV NODE_ENV=production
EXPOSE 80

CMD [ "npm", "start" ]
