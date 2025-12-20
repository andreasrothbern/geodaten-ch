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

# Nginx Config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Built files kopieren
COPY --from=builder /app/dist /usr/share/nginx/html

# Port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
