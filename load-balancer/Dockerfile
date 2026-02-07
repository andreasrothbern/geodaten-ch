# =============================================================================
# Geodaten-CH Load Balancer
# =============================================================================
# Nginx-basierter Load Balancer für Read-Replica Architektur
# Stand: 07.02.2026
# =============================================================================

FROM nginx:alpine

# envsubst für Environment-Variable Substitution
RUN apk add --no-cache gettext

# Nginx Config mit Platzhaltern
COPY nginx.conf /etc/nginx/nginx.conf.template

# Startup-Script für Variable-Substitution
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
