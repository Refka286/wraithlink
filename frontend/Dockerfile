FROM node:20-alpine

RUN addgroup -S wraithlink && adduser -S wraithlink -G wraithlink

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm ci

COPY . .

RUN chown -R wraithlink:wraithlink /app

USER wraithlink

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
