# Geodaten Schweiz - Frontend
# ============================

# Build Stage
FROM node:20-alpine AS builder

WORKDIR /app

# Dependencies installieren
COPY package.json package-lock.json* ./
RUN npm ci

# Source kopieren und bauen
COPY . .

# API URL setzen (wird von Railway als ENV übergeben)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Production Stage
FROM nginx:alpine

# Nginx Config als Template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Built files kopieren
COPY --from=builder /app/dist /usr/share/nginx/html

# Railway setzt PORT dynamisch
ENV PORT=80

CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
