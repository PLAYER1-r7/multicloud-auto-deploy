# =============================================================
# Stage 1: React SPA を /sns/ サブパス用にビルド
# =============================================================
FROM node:20-alpine AS react-builder

# /sns/ パスでアセット参照するよう設定
ENV VITE_BASE_PATH=/sns/
# API は相対 URL (nginx がプロキシ転送)
ENV VITE_API_URL=

WORKDIR /app
COPY services/frontend_react/package*.json ./
RUN npm ci
COPY services/frontend_react/ .
RUN npm run build

# =============================================================
# Stage 2: nginx で静的サイト + React SPA を配信
# =============================================================
FROM nginx:alpine

# 静的サイトのファイルをルートに配置
COPY static-site/index.html  /usr/share/nginx/html/index.html
COPY static-site/error.html  /usr/share/nginx/html/error.html

# React SPA を /sns/ サブディレクトリに配置
COPY --from=react-builder /app/dist /usr/share/nginx/html/sns

# nginx 設定
COPY static-site/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8090
CMD ["nginx", "-g", "daemon off;"]
