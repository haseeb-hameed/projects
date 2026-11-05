FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt "psycopg[binary]>=3,<4"
ARG ENABLE_AI=false
RUN if [ "$ENABLE_AI" = "true" ]; then pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir "ultralytics>=8.3,<9" opencv-python-headless; fi
COPY backend ./backend
COPY models ./models
COPY --from=web /app/dist ./dist
ENV SERVE_WEB=1
EXPOSE 8001
WORKDIR /app/backend
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8001","--ws-max-size","4096"]
