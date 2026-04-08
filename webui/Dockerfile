FROM node:20-slim

WORKDIR /app/webui

COPY webui/package.json /app/webui/package.json
COPY webui/package-lock.json /app/webui/package-lock.json
RUN npm ci

COPY webui /app/webui

RUN chmod +x /app/webui/scripts/start-dev.sh

CMD ["sh", "/app/webui/scripts/start-dev.sh"]
