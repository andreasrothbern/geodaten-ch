# backend/app/config.py
"""
Zentrale Konfiguration für Geodaten-CH Backend
===============================================

Feature-Flags und Datenbank-Pfade.

NEU 13.01.2026 17:00: DuckDB ist jetzt DEFAULT!
- DuckDB wird verwendet wenn USE_DUCKDB nicht explizit "false" ist
- Für SQLite: USE_DUCKDB=false setzen

Verwendung:
    from app.config import (
        USE_DUCKDB,
        BUILDING_3D_DB_PATH,
        get_building_3d_connection,
    )
"""

import os
from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# PFADE (NEU 15.01.2026: Ephemeral vs Volume Trennung)
# =============================================================================

# DATA_DIR: Persistente Daten (Datenbanken)
# - Railway: Volume mount (/app/data) - überlebt Redeploys
# - Lokal: ./app/data
_default_data_dir = Path(__file__).parent / "data"
_data_dir_env = os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or os.getenv("DATA_DIR")
DATA_DIR = Path(_data_dir_env) if _data_dir_env else _default_data_dir
DATA_DIR.mkdir(parents=True, exist_ok=True)

# EPHEMERAL_DIR: Temporäre Daten (Tiles, Parquet)
# - Railway: Ephemeral Storage (/tmp) - wird bei Redeploy gelöscht, 100GB verfügbar
# - Lokal: ./app/data (gleich wie DATA_DIR für Einfachheit)
# NEU 15.01.2026: Tiles und Parquet-Dateien gehören hier hin!
_ephemeral_dir_env = os.getenv("EPHEMERAL_DIR")
if _ephemeral_dir_env:
    EPHEMERAL_DIR = Path(_ephemeral_dir_env)
elif os.getenv("RAILWAY_ENVIRONMENT"):
    # Railway: /tmp für Ephemeral Storage
    EPHEMERAL_DIR = Path("/tmp/geodaten")
else:
    # Lokal: gleich wie DATA_DIR
    EPHEMERAL_DIR = DATA_DIR
EPHEMERAL_DIR.mkdir(parents=True, exist_ok=True)

# Tile-Verzeichnis (GDB-Dateien, temporär)
TILES_DIR = EPHEMERAL_DIR / "tiles"
TILES_DIR.mkdir(parents=True, exist_ok=True)

# Parquet-Verzeichnis (für Batch-Import, temporär)
PARQUET_DIR = EPHEMERAL_DIR / "parquet"
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# DuckDB-Migration (building_3d.db)
# NEU 13.01.2026 17:00: DuckDB ist jetzt DEFAULT!
# - Ohne Flag oder USE_DUCKDB=true → DuckDB (Standard)
# - USE_DUCKDB=false → SQLite (Legacy-Modus)
USE_DUCKDB = os.getenv("USE_DUCKDB", "true").lower() != "false"

# 3D-Layer laden (Floor, Wall, Roof aus swissBUILDINGS3D)
LOAD_3D_LAYERS = os.getenv("LOAD_3D_LAYERS", "false").lower() == "true"

# Dachwinkel aus 3D-Geometrie berechnen (statt Heuristik)
CALC_ROOF_FROM_3D = os.getenv("CALC_ROOF_FROM_3D", "false").lower() == "true"

# NEU 13.01.2026 18:15: Tiles nach Import löschen
# Default: true - Spart Speicher (~70-80%)
# Bei false: GDB-Dateien bleiben in tiles/ erhalten
CLEANUP_TILES_AFTER_IMPORT = os.getenv("CLEANUP_TILES_AFTER_IMPORT", "true").lower() != "false"

# NEU 18.01.2026 23:15: Standard-Suchradius für Nachbar-Gebäude
# Default: 100m - wird für SQL BBox-Query verwendet
# Kann via API überschrieben werden (radius_m Parameter)
NEIGHBOR_SEARCH_RADIUS_M = float(os.getenv("NEIGHBOR_SEARCH_RADIUS_M", "100"))

# =============================================================================
# WORKER MODE (NEU 07.02.2026 - Read-Replica Architektur)
# =============================================================================
# Ermöglicht horizontale Skalierung mit 1 Writer + N Reader Services.
#
# WORKER_MODE=writer (Default):
#   - Voller Schreibzugriff auf alle Datenbanken
#   - Für Import-Operationen, Projekt-CRUD, etc.
#   - Nur 1 Writer-Service erlaubt (DuckDB Single-Writer Lock)
#
# WORKER_MODE=reader:
#   - Nur Lesezugriff (read_only) auf alle Datenbanken
#   - Für GET-Requests, SSE-Streams, Nachbar-Queries
#   - Beliebig viele Reader-Services möglich (DuckDB Multiple-Reader)
#   - Kann mit --workers=4 laufen (kein Lock-Konflikt bei read_only)
#
WORKER_MODE = os.getenv("WORKER_MODE", "writer")
IS_READER = WORKER_MODE == "reader"
IS_WRITER = WORKER_MODE == "writer"

# =============================================================================
# DATENBANK-PFADE
# =============================================================================

# building_3d: Gebäude-Grunddaten aus swissBUILDINGS3D
BUILDING_3D_SQLITE_PATH = DATA_DIR / "building_3d.db"
BUILDING_3D_DUCKDB_PATH = DATA_DIR / "building_3d.duckdb"

# Aktiver Pfad basierend auf Feature-Flag
BUILDING_3D_DB_PATH = BUILDING_3D_DUCKDB_PATH if USE_DUCKDB else BUILDING_3D_SQLITE_PATH

# Andere Datenbanken (bleiben SQLite)
TILES_DB_PATH = DATA_DIR / "tiles.db"
BUILDING_CONTEXTS_DB_PATH = DATA_DIR / "building_contexts.db"
GERUESTBAU_DB_PATH = DATA_DIR / "geruestbau.db"
CACHE_DB_PATH = Path(os.getenv("CACHE_DB_PATH", "cache.db"))

# =============================================================================
# DUCKDB-SPEZIFISCHE KONFIGURATION
# =============================================================================

# DuckDB Temp-Verzeichnis auf Ephemeral Storage (nicht Volume!)
# NEU 15.01.2026: Temp-Dateien können 300+ MB werden und füllten das Volume
DUCKDB_TEMP_DIR = EPHEMERAL_DIR / "duckdb_temp"
DUCKDB_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# NEU 07.02.2026: Optimiert für Railway Pro Plan
# - threads: 16 (nutzt Multi-Core für parallele Queries)
# - memory_limit: 4GB (für grössere Batch-Imports)
# Lokal: Kann mit DUCKDB_THREADS=4 und DUCKDB_MEMORY_LIMIT=512MB überschrieben werden
DUCKDB_CONFIG = {
    "threads": int(os.getenv("DUCKDB_THREADS", "16")),
    "memory_limit": os.getenv("DUCKDB_MEMORY_LIMIT", "4GB"),
    "temp_directory": str(DUCKDB_TEMP_DIR),  # Temp auf Ephemeral statt Volume!
}

# =============================================================================
# CONNECTION FACTORY
# =============================================================================

def get_building_3d_connection(read_only: bool = False):
    """
    Factory für building_3d Datenbank-Verbindung.

    Gibt je nach USE_DUCKDB SQLite oder DuckDB Connection zurück.

    NEU 07.02.2026: Read-Replica Architektur
    =========================================
    - WORKER_MODE=reader → Immer read_only=True (kein Schreibzugriff)
    - WORKER_MODE=writer → Normaler Schreibzugriff

    Args:
        read_only: Für Writer-Modus: Explizit read_only anfordern (optional).
                   Für Reader-Modus: Wird IGNORIERT, immer read_only=True.

    Returns:
        Connection-Objekt (sqlite3.Connection oder duckdb.Connection)

    Beispiel:
        with get_building_3d_connection() as conn:
            result = conn.execute("SELECT * FROM buildings_3d LIMIT 1")

    NEU 31.01.2026: Spatial Extension wird automatisch geladen für ST_Contains, ST_DWithin.
    """
    if USE_DUCKDB:
        import duckdb

        # NEU 07.02.2026: Read-Replica Architektur
        # Reader-Services: Immer read_only (kein Write-Lock, mehrere parallel möglich)
        # Writer-Services: Normaler Schreibzugriff (nur 1 Writer erlaubt)
        if IS_READER:
            # Reader: read_only=True, keine Config nötig (kein Write-Lock)
            conn = duckdb.connect(str(BUILDING_3D_DUCKDB_PATH), read_only=True)
        else:
            # Writer: Voller Schreibzugriff mit DUCKDB_CONFIG
            conn = duckdb.connect(str(BUILDING_3D_DUCKDB_PATH), config=DUCKDB_CONFIG)

        # Spatial Extension für GEOMETRY-Typ und R-Tree Index
        conn.execute("INSTALL spatial")
        conn.execute("LOAD spatial")
        return conn
    else:
        import sqlite3
        # SQLite: read_only via URI-Parameter
        if IS_READER:
            conn = sqlite3.connect(
                f"file:{BUILDING_3D_SQLITE_PATH}?mode=ro",
                uri=True
            )
        else:
            conn = sqlite3.connect(str(BUILDING_3D_SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        return conn


def get_db_engine_name() -> str:
    """Gibt den Namen der aktiven DB-Engine zurück."""
    return "DuckDB" if USE_DUCKDB else "SQLite"


def get_sqlite_connection(db_path: Union[str, Path], read_only: bool = False):
    """
    Factory für SQLite-Verbindungen mit Read-Replica Support.

    NEU 07.02.2026: Read-Replica Architektur
    =========================================
    - WORKER_MODE=reader → Immer read_only=True (kein Schreibzugriff)
    - WORKER_MODE=writer → Normaler Schreibzugriff

    Args:
        db_path: Pfad zur SQLite-Datenbank
        read_only: Für Writer-Modus: Explizit read_only anfordern (optional).
                   Für Reader-Modus: Wird IGNORIERT, immer read_only=True.

    Returns:
        sqlite3.Connection mit row_factory=sqlite3.Row

    Beispiel:
        from app.config import get_sqlite_connection, GERUESTBAU_DB_PATH
        conn = get_sqlite_connection(GERUESTBAU_DB_PATH)
    """
    import sqlite3

    db_path_str = str(db_path)

    # Reader-Service: Immer read_only (kein Write-Lock, mehrere parallel möglich)
    if IS_READER or read_only:
        conn = sqlite3.connect(
            f"file:{db_path_str}?mode=ro",
            uri=True
        )
    else:
        conn = sqlite3.connect(db_path_str)

    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# LOGGING BEI IMPORT
# =============================================================================

# Storage-Pfade
logger.info(f"[CONFIG] DATA_DIR (Volume): {DATA_DIR}")
logger.info(f"[CONFIG] EPHEMERAL_DIR (Temp): {EPHEMERAL_DIR}")
if DATA_DIR != EPHEMERAL_DIR:
    logger.info("[CONFIG] Storage-Trennung aktiv: DBs → Volume, Tiles → Ephemeral")

if USE_DUCKDB:
    logger.info(f"[CONFIG] DuckDB aktiviert: {BUILDING_3D_DUCKDB_PATH}")
    logger.info(f"[CONFIG] DuckDB-Config: {DUCKDB_CONFIG}")
else:
    logger.info(f"[CONFIG] SQLite aktiv: {BUILDING_3D_SQLITE_PATH}")

if LOAD_3D_LAYERS:
    logger.info("[CONFIG] 3D-Layer-Import aktiviert")

if CALC_ROOF_FROM_3D:
    logger.info("[CONFIG] Dachwinkel-Berechnung aus 3D aktiviert")

if CLEANUP_TILES_AFTER_IMPORT:
    logger.info("[CONFIG] Tile-Cleanup nach Import aktiviert")

# Worker Mode
logger.info(f"[CONFIG] WORKER_MODE: {WORKER_MODE}")
if IS_READER:
    logger.info("[CONFIG] Reader-Modus: Nur Lesezugriff, keine Schreiboperationen")
else:
    logger.info("[CONFIG] Writer-Modus: Voller Schreibzugriff")
