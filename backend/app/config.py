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
# PFADE
# =============================================================================

# Basis-Verzeichnis für Daten
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

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

# NEU 13.01.2026 18:15: All-Layer-Import beim Prefetch
# Default: true - Importiert Building_solid + Roof_solid + Wall zusammen
# Bei false: Nur Building_solid + Roof_solid (Walls on-demand)
IMPORT_ALL_LAYERS = os.getenv("IMPORT_ALL_LAYERS", "true").lower() != "false"

# NEU 13.01.2026 18:15: Tiles nach Import löschen
# Default: true - Spart Speicher (~70-80%)
# Bei false: GDB-Dateien bleiben in tiles/ erhalten
CLEANUP_TILES_AFTER_IMPORT = os.getenv("CLEANUP_TILES_AFTER_IMPORT", "true").lower() != "false"

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

DUCKDB_CONFIG = {
    "threads": int(os.getenv("DUCKDB_THREADS", "4")),
    "memory_limit": os.getenv("DUCKDB_MEMORY_LIMIT", "512MB"),
}

# =============================================================================
# CONNECTION FACTORY
# =============================================================================

def get_building_3d_connection(read_only: bool = False):
    """
    Factory für building_3d Datenbank-Verbindung.

    Gibt je nach USE_DUCKDB SQLite oder DuckDB Connection zurück.

    Args:
        read_only: IGNORIERT für DuckDB! Akzeptiert für API-Kompatibilität.
                   DuckDB erlaubt keine gemischten read_only/write Connections
                   zur gleichen Datei.

    Returns:
        Connection-Objekt (sqlite3.Connection oder duckdb.Connection)

    Beispiel:
        with get_building_3d_connection() as conn:
            result = conn.execute("SELECT * FROM buildings_3d LIMIT 1")

    WICHTIG (DuckDB): Alle Connections zur gleichen DB müssen die gleiche
    Konfiguration verwenden! read_only wird IGNORIERT um Konflikte zu vermeiden.
    """
    if USE_DUCKDB:
        import duckdb
        # FIX 14.01.2026: read_only Parameter IGNORIEREN!
        # DuckDB erlaubt keine gemischten read_only/write Connections.
        # Wenn eine write-Connection existiert und jemand read_only=True anfordert,
        # gibt es einen "different configuration" Fehler.
        # Lösung: Immer write-Modus verwenden (DuckDB kann trotzdem lesen).
        # FIX 14.01.2026: DUCKDB_CONFIG übergeben für Multi-Threading!
        return duckdb.connect(str(BUILDING_3D_DUCKDB_PATH), config=DUCKDB_CONFIG)
    else:
        import sqlite3
        conn = sqlite3.connect(str(BUILDING_3D_SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        return conn


def get_db_engine_name() -> str:
    """Gibt den Namen der aktiven DB-Engine zurück."""
    return "DuckDB" if USE_DUCKDB else "SQLite"


# =============================================================================
# LOGGING BEI IMPORT
# =============================================================================

if USE_DUCKDB:
    logger.info(f"[CONFIG] DuckDB aktiviert: {BUILDING_3D_DUCKDB_PATH}")
    logger.info(f"[CONFIG] DuckDB-Config: {DUCKDB_CONFIG}")
else:
    logger.info(f"[CONFIG] SQLite aktiv: {BUILDING_3D_SQLITE_PATH}")

if LOAD_3D_LAYERS:
    logger.info("[CONFIG] 3D-Layer-Import aktiviert")

if CALC_ROOF_FROM_3D:
    logger.info("[CONFIG] Dachwinkel-Berechnung aus 3D aktiviert")

if IMPORT_ALL_LAYERS:
    logger.info("[CONFIG] All-Layer-Import aktiviert (Building+Roof+Wall)")
else:
    logger.info("[CONFIG] Standard-Import (Building+Roof, Wall on-demand)")

if CLEANUP_TILES_AFTER_IMPORT:
    logger.info("[CONFIG] Tile-Cleanup nach Import aktiviert")
