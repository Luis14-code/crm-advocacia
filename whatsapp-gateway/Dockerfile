FROM node:20-bookworm-slim

WORKDIR /app

# git: o Baileys puxa uma dependência via git (libsignal); build-essential/python: node-gyp.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git python3 make g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Dependências (sem as opcionais pesadas: sharp/jimp etc. não são necessárias p/ texto)
COPY package.json ./
RUN npm install --omit=dev --omit=optional --no-audit --no-fund

COPY server.js ./

ENV PORT=3000
EXPOSE 3000

CMD ["node", "server.js"]
