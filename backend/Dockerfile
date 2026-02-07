# Geodaten Schweiz API - Backend
# ================================

FROM python:3.11-slim

# Arbeitsverzeichnis
WORKDIR /app

# System-Dependencies (inkl. GDAL/Fiona für GDB-Parsing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libexpat1 \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendung kopieren
COPY app ./app/

# Port (Railway setzt PORT dynamisch)
ENV PORT=8000

# Data directory (Railway Volume mount)
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data

# =============================================================================
# READ-REPLICA ARCHITEKTUR (NEU 07.02.2026)
# =============================================================================
# WORKER_MODE Environment Variable steuert den Service-Typ:
#
#   WORKER_MODE=writer (Default):
#     - Voller Schreibzugriff auf DuckDB
#     - UVICORN_WORKERS=1 PFLICHT (DuckDB Single-Writer Lock!)
#     - Für: POST/PUT/DELETE, Tile-Import, Projekt-CRUD
#
#   WORKER_MODE=reader:
#     - read_only DuckDB Connection (kein Write-Lock)
#     - UVICORN_WORKERS=4 möglich (parallele Prozesse)
#     - Für: GET-Requests, SSE-Streams, Nachbar-Queries
#
# Skalierung:
#   - Writer: 1 Service × 1 Worker × DUCKDB_THREADS=16
#   - Reader: N Services × 4 Worker × DUCKDB_THREADS=8
#   - Load Balancer routet GET → Reader, POST/PUT/DELETE → Writer
#
# Siehe: docs/architecture/RAILWAY_DEPLOYMENT.md
# =============================================================================

# Worker-Anzahl über Environment Variable
# Writer: 1 (PFLICHT!), Reader: 4 (empfohlen)
ENV UVICORN_WORKERS=1

# Start - verwendet $PORT von Railway und $UVICORN_WORKERS
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers ${UVICORN_WORKERS}
