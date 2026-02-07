#!/bin/sh
# =============================================================================
# Docker Entrypoint für Load Balancer
# =============================================================================
# Ersetzt Environment-Variablen in nginx.conf und startet nginx
# Stand: 07.02.2026
# =============================================================================

set -e

# Environment-Variablen mit Defaults
export WRITER_HOST="${WRITER_HOST:-backend-writer}"
export WRITER_PORT="${WRITER_PORT:-8000}"
export READER1_HOST="${READER1_HOST:-backend-reader-1}"
export READER1_PORT="${READER1_PORT:-8001}"
export READER2_HOST="${READER2_HOST:-backend-reader-2}"
export READER2_PORT="${READER2_PORT:-8002}"
export READER3_HOST="${READER3_HOST:-backend-reader-3}"
export READER3_PORT="${READER3_PORT:-8003}"

echo "[Load Balancer] Konfiguration:"
echo "  Writer: ${WRITER_HOST}:${WRITER_PORT}"
echo "  Reader 1: ${READER1_HOST}:${READER1_PORT}"
echo "  Reader 2: ${READER2_HOST}:${READER2_PORT}"
echo "  Reader 3: ${READER3_HOST}:${READER3_PORT}"

# Environment-Variablen in nginx.conf ersetzen
envsubst '${WRITER_HOST} ${WRITER_PORT} ${READER1_HOST} ${READER1_PORT} ${READER2_HOST} ${READER2_PORT} ${READER3_HOST} ${READER3_PORT}' \
    < /etc/nginx/nginx.conf.template \
    > /etc/nginx/nginx.conf

echo "[Load Balancer] nginx.conf generiert"

# Nginx starten
exec "$@"
