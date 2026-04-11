FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY data/ ./data/
COPY server/ ./server/

ENV NODE_ENV=production

CMD ["node", "server/server.js"]
