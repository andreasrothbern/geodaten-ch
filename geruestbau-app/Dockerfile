# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Dependencies
COPY package*.json ./
RUN npm ci

# Build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
