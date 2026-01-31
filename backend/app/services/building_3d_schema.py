# backend/app/services/building_3d_schema.py
"""
Schema-Definitionen für building_3d Datenbank
=============================================

Unterstützt sowohl SQLite als auch DuckDB.

NEU 12.01.2026: DuckDB-Migration

Verwendung:
    from app.services.building_3d_schema import init_schema

    init_schema()  # Erstellt Schema basierend auf USE_DUCKDB Flag
"""

import logging
from pathlib import Path

from app.config import (
    USE_DUCKDB,
    BUILDING_3D_SQLITE_PATH,
    BUILDING_3D_DUCKDB_PATH,
    DATA_DIR,
    get_building_3d_connection,  # FIX 13.01.2026 18:50: Zentrale Connection-Factory
)

logger = logging.getLogger(__name__)

# =============================================================================
# GEMEINSAMES SCHEMA (SQL-kompatibel für beide Engines)
# =============================================================================

# Haupttabelle: buildings_3d
# HINWEIS 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
# Diese Werte werden aus GELAENDEPUNKT berechnet (Schätzung, bei Hanglagen ~1-2m ungenau).
# Für das Hauptgebäude erfolgt exakte Berechnung via Terrain-Sampling.
# Für Nachbarn reicht die Schätzung aus swissBUILDINGS3D.
# NEU 17.01.2026: Terrain-Felder für prefetch_neighbors() Enrichment
# NEU 31.01.2026: polygon JSON → geom GEOMETRY (DuckDB Spatial Extension)
#   - R-Tree Index für schnelle Point-in-Polygon Queries
#   - ST_Contains, ST_DWithin statt Python Ray-Casting
#   - ST_AsGeoJSON für Frontend-Kompatibilität
BUILDINGS_3D_TABLE = """
CREATE TABLE IF NOT EXISTS buildings_3d (
    egid INTEGER PRIMARY KEY,
    geom GEOMETRY,
    traufhoehe_m {float_type},
    firsthoehe_m {float_type},
    gebaeudehoehe_m {float_type},
    area_m2 {float_type},
    perimeter_m {float_type},
    center_e {float_type},
    center_n {float_type},
    tile_id {text_type},
    imported_at {timestamp_type},
    source {text_type} DEFAULT 'swissBUILDINGS3D_3.0',
    objektart {text_type},
    name_komplett {text_type},
    gebaeude_nutzung {text_type},
    gebaeudeeinheit {text_type},
    roof_form {text_type},
    roof_form_confidence {float_type},
    roof_orientation {text_type},
    has_3d_layers INTEGER DEFAULT 0,
    -- NEU 17.01.2026: Terrain-Sampling Felder (via swissALTI3D)
    terrain_z_min {float_type},
    terrain_z_max {float_type},
    terrain_slope_m {float_type},
    terrain_sampled_at TIMESTAMP
)
"""

# 3D-Layer Tabellen
# NEU 13.01.2026 19:00: gebaeudeeinheit als PRIMARY KEY (statt auto-increment id)
# DuckDB hat keine AUTOINCREMENT, und die gebaeudeeinheit ist eindeutig.
BUILDING_ROOFS_TABLE = """
CREATE TABLE IF NOT EXISTS building_roofs (
    gebaeudeeinheit {text_type} PRIMARY KEY,
    egid INTEGER,
    dach_min {float_type},
    dach_max {float_type},
    roof_form {text_type},
    roof_angle_deg {float_type},
    roof_orientation {text_type},
    z_levels {text_type},
    geometry_wkb {blob_type},
    has_full_geometry INTEGER DEFAULT 0,
    calculated_at {timestamp_type},
    calculation_method {text_type}
)
"""

BUILDING_WALLS_TABLE = """
CREATE TABLE IF NOT EXISTS building_walls (
    gebaeudeeinheit {text_type} PRIMARY KEY,
    egid INTEGER,
    z_min {float_type},
    z_max {float_type},
    geometry_wkb {blob_type},
    created_at {timestamp_type}
)
"""

BUILDING_FLOORS_TABLE = """
CREATE TABLE IF NOT EXISTS building_floors (
    gebaeudeeinheit {text_type} PRIMARY KEY,
    egid INTEGER,
    gelaendepunkt {float_type},
    geometry_wkb {blob_type},
    created_at {timestamp_type}
)
"""

# Import-Log für Batch-Tracking
# NEU 13.01.2026 19:15: Aus building_3d_service.py hierher verschoben
IMPORT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS import_log (
    tile_id {text_type} PRIMARY KEY,
    buildings_count INTEGER,
    imported_at {timestamp_type},
    duration_seconds {float_type},
    source {text_type}
)
"""

# Indizes
# NEU 13.01.2026 19:15: gebaeudeeinheit ist jetzt PRIMARY KEY, kein Index nötig
# NEU 17.01.2026: idx_buildings_3d_enrichment für prefetch_neighbors() Abfragen
# NEU 31.01.2026: Spatial Index separat (RTREE-Syntax)
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_buildings_3d_coords ON buildings_3d(center_e, center_n)",
    "CREATE INDEX IF NOT EXISTS idx_buildings_3d_tile ON buildings_3d(tile_id)",
    "CREATE INDEX IF NOT EXISTS idx_buildings_3d_objektart ON buildings_3d(objektart)",
    "CREATE INDEX IF NOT EXISTS idx_buildings_3d_gebaeudeeinheit ON buildings_3d(gebaeudeeinheit)",
    "CREATE INDEX IF NOT EXISTS idx_buildings_3d_enrichment ON buildings_3d(terrain_sampled_at, has_3d_layers)",
    "CREATE INDEX IF NOT EXISTS idx_roofs_egid ON building_roofs(egid)",
    "CREATE INDEX IF NOT EXISTS idx_walls_egid ON building_walls(egid)",
    "CREATE INDEX IF NOT EXISTS idx_floors_egid ON building_floors(egid)",
]

# NEU 31.01.2026: Spatial Index wird separat erstellt (andere Syntax)
SPATIAL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_buildings_3d_geom ON buildings_3d USING RTREE(geom)",
]

# =============================================================================
# TYP-MAPPINGS
# =============================================================================

SQLITE_TYPES = {
    "json_type": "TEXT",
    "float_type": "REAL",
    "text_type": "TEXT",
    "timestamp_type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "blob_type": "BLOB",
}

DUCKDB_TYPES = {
    "json_type": "JSON",  # Native JSON-Unterstützung!
    "float_type": "DOUBLE",
    "text_type": "VARCHAR",
    "timestamp_type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "blob_type": "BLOB",
}


# =============================================================================
# SCHEMA-INITIALISIERUNG
# =============================================================================

def _get_formatted_sql(template: str, use_duckdb: bool) -> str:
    """Formatiert SQL-Template mit den richtigen Typen."""
    types = DUCKDB_TYPES if use_duckdb else SQLITE_TYPES
    return template.format(**types)


def init_sqlite_schema() -> None:
    """Initialisiert SQLite-Schema für building_3d.db"""
    import sqlite3

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(BUILDING_3D_SQLITE_PATH) as conn:
        cursor = conn.cursor()

        # Tabellen erstellen
        for table_sql in [BUILDINGS_3D_TABLE, BUILDING_ROOFS_TABLE,
                          BUILDING_WALLS_TABLE, BUILDING_FLOORS_TABLE,
                          IMPORT_LOG_TABLE]:
            sql = _get_formatted_sql(table_sql, use_duckdb=False)
            cursor.execute(sql)

        # Indizes erstellen
        for index_sql in INDEXES:
            cursor.execute(index_sql)

        conn.commit()

    logger.info(f"[SCHEMA] SQLite-Schema initialisiert: {BUILDING_3D_SQLITE_PATH}")


def init_duckdb_schema() -> None:
    """Initialisiert DuckDB-Schema für building_3d.duckdb"""
    # FIX 13.01.2026 18:50: Zentrale Connection-Factory verwenden
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_building_3d_connection() as conn:
        # Tabellen erstellen
        for table_sql in [BUILDINGS_3D_TABLE, BUILDING_ROOFS_TABLE,
                          BUILDING_WALLS_TABLE, BUILDING_FLOORS_TABLE,
                          IMPORT_LOG_TABLE]:
            sql = _get_formatted_sql(table_sql, use_duckdb=True)
            conn.execute(sql)

        # FIX 24.01.2026: Indizes bei DuckDB immer neu erstellen (Korruptionsproblem)
        # DROP + CREATE statt nur CREATE IF NOT EXISTS
        for index_sql in INDEXES:
            # Extrahiere Index-Name aus SQL
            # Format: "CREATE INDEX IF NOT EXISTS idx_name ON ..."
            parts = index_sql.split()
            if "IF" in parts and "NOT" in parts:
                idx_name = parts[5]  # idx_name ist nach "EXISTS"
            else:
                idx_name = parts[2]  # idx_name ist nach "INDEX"

            # Drop und neu erstellen
            conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
            # Entferne "IF NOT EXISTS" und erstelle neu
            clean_sql = index_sql.replace("IF NOT EXISTS ", "")
            conn.execute(clean_sql)

        # NEU 31.01.2026: Spatial Indexes (RTREE) erstellen
        for spatial_sql in SPATIAL_INDEXES:
            parts = spatial_sql.split()
            if "IF" in parts and "NOT" in parts:
                idx_name = parts[5]
            else:
                idx_name = parts[2]

            # Drop und neu erstellen
            conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
            clean_sql = spatial_sql.replace("IF NOT EXISTS ", "")
            try:
                conn.execute(clean_sql)
                logger.info(f"[SCHEMA] Spatial Index erstellt: {idx_name}")
            except Exception as e:
                logger.warning(f"[SCHEMA] Spatial Index {idx_name} fehlgeschlagen: {e}")

        # Checkpoint für Persistenz
        conn.execute("CHECKPOINT")

    logger.info(f"[SCHEMA] DuckDB-Schema initialisiert (Indizes rebuilt): {BUILDING_3D_DUCKDB_PATH}")


def init_schema() -> None:
    """
    Initialisiert das Schema basierend auf USE_DUCKDB Flag.

    Wird automatisch beim Import von building_3d_service aufgerufen.
    """
    if USE_DUCKDB:
        init_duckdb_schema()
    else:
        init_sqlite_schema()


def get_schema_info() -> dict:
    """Gibt Informationen über das aktive Schema zurück."""
    return {
        "engine": "DuckDB" if USE_DUCKDB else "SQLite",
        "db_path": str(BUILDING_3D_DUCKDB_PATH if USE_DUCKDB else BUILDING_3D_SQLITE_PATH),
        "tables": ["buildings_3d", "building_roofs", "building_walls", "building_floors"],
        "type_mappings": DUCKDB_TYPES if USE_DUCKDB else SQLITE_TYPES,
    }


# =============================================================================
# VIEW-DEFINITIONEN (Optional, für komplexe Queries)
# =============================================================================

BUILDING_COMPLETE_VIEW = """
CREATE VIEW IF NOT EXISTS building_complete AS
SELECT
    b.*,
    r.dach_min AS roof_dach_min,
    r.dach_max AS roof_dach_max,
    r.roof_angle_deg,
    r.geometry_wkb AS roof_geometry,
    w.z_min AS wall_z_min,
    w.z_max AS wall_z_max,
    w.geometry_wkb AS wall_geometry,
    f.gelaendepunkt AS floor_gelaendepunkt,
    f.geometry_wkb AS floor_geometry
FROM buildings_3d b
LEFT JOIN building_roofs r ON b.egid = r.egid
LEFT JOIN building_walls w ON b.egid = w.egid
LEFT JOIN building_floors f ON b.egid = f.egid
"""


def create_views() -> None:
    """Erstellt optionale Views für komplexe Queries."""
    # FIX 13.01.2026 18:50: Zentrale Connection-Factory verwenden
    if USE_DUCKDB:
        with get_building_3d_connection() as conn:
            conn.execute(BUILDING_COMPLETE_VIEW)
    else:
        import sqlite3
        with sqlite3.connect(BUILDING_3D_SQLITE_PATH) as conn:
            conn.execute(BUILDING_COMPLETE_VIEW)

    logger.info("[SCHEMA] Views erstellt")
