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

# Start - verwendet $PORT von Railway
# --workers 4 für parallele Request-Verarbeitung
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
