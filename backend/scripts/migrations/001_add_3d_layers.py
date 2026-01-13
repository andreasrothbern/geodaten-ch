#!/usr/bin/env python3
"""
Migration 001: Add 3D Layer Tables
==================================

Erweitert das DB-Schema für vollständige 3D-Daten aus swissBUILDINGS3D 3.0.

Änderungen:
1. buildings_3d: Neue Spalten für Attribute und Dach-Metadaten
2. building_roofs: Dachgeometrie und berechnete Dachform
3. building_walls: 3D-Fassadengeometrie
4. building_floors: Exakter Grundriss (für komplexe Gebäude)

Ausführung:
    python scripts/migrations/001_add_3d_layers.py

Rollback:
    python scripts/migrations/001_add_3d_layers.py --rollback

Version: 1.0 (11.01.2026)
"""

import sqlite3
import logging
import sys
from pathlib import Path
from datetime import datetime

# Backend-Pfad für Imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.building_3d_service import BUILDING_3D_DB

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MIGRATION_VERSION = "001_add_3d_layers"


def get_connection():
    """Erstellt eine Datenbankverbindung."""
    conn = sqlite3.connect(BUILDING_3D_DB)
    conn.row_factory = sqlite3.Row
    return conn


def check_column_exists(conn, table: str, column: str) -> bool:
    """Prüft ob eine Spalte existiert."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def check_table_exists(conn, table: str) -> bool:
    """Prüft ob eine Tabelle existiert."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table,))
    return cursor.fetchone() is not None


def migrate_buildings_3d(conn):
    """
    Erweitert buildings_3d um neue Spalten.

    Neue Spalten:
    - objektart: Gebäudetyp aus swissBUILDINGS3D
    - name_komplett: Gebäudename (wenn vorhanden)
    - gebaeude_nutzung: Nutzungsart
    - gebaeudeeinheit: Verknüpfung zu anderen Layern
    - roof_form: Berechnete Dachform
    - roof_form_confidence: Konfidenz der Erkennung (0-1)
    - roof_orientation: First-Verlauf (N-S, O-W, etc.)
    - has_3d_layers: Flag für erweiterte 3D-Daten
    """
    cursor = conn.cursor()

    new_columns = [
        ("objektart", "TEXT"),
        ("name_komplett", "TEXT"),
        ("gebaeude_nutzung", "TEXT"),
        ("gebaeudeeinheit", "TEXT"),
        ("roof_form", "TEXT"),
        ("roof_form_confidence", "REAL"),
        ("roof_orientation", "TEXT"),
        ("has_3d_layers", "INTEGER DEFAULT 0"),
    ]

    added = 0
    for column_name, column_type in new_columns:
        if not check_column_exists(conn, "buildings_3d", column_name):
            cursor.execute(f"ALTER TABLE buildings_3d ADD COLUMN {column_name} {column_type}")
            logger.info(f"  + Spalte hinzugefügt: buildings_3d.{column_name}")
            added += 1
        else:
            logger.info(f"  - Spalte existiert bereits: buildings_3d.{column_name}")

    # Index für gebaeudeeinheit (wichtig für Layer-Verknüpfung)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_buildings_3d_gebaeudeeinheit
        ON buildings_3d(gebaeudeeinheit)
    """)

    conn.commit()
    return added


def create_building_roofs(conn):
    """
    Erstellt die building_roofs Tabelle.

    Enthält:
    - Berechnete Dachform und Neigung (immer, aus Pre-Import)
    - 3D-Geometrie (nur für komplexe Gebäude, on-demand)
    """
    cursor = conn.cursor()

    if check_table_exists(conn, "building_roofs"):
        logger.info("  - Tabelle building_roofs existiert bereits")
        return False

    cursor.execute("""
        CREATE TABLE building_roofs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gebaeudeeinheit TEXT NOT NULL,
            egid TEXT,

            -- Berechnete Werte (aus 3D-Geometrie)
            dach_min REAL,              -- Traufhöhe (m ü.M.)
            dach_max REAL,              -- Firsthöhe (m ü.M.)
            roof_form TEXT,             -- Erkannte Dachform
            roof_angle_deg REAL,        -- Berechnete Neigung
            roof_orientation TEXT,      -- First-Verlauf
            z_levels TEXT,              -- JSON: [546.9, 551.0, ...] für Analyse

            -- 3D-Geometrie (nur für komplexe Gebäude, on-demand)
            geometry_wkb BLOB,          -- 3D MultiPolygon als WKB (NULL bei Pre-Import)
            has_full_geometry INTEGER DEFAULT 0,

            -- Metadaten
            calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            calculation_method TEXT     -- 'z_level_analysis', 'manual', 'estimated'
        )
    """)

    cursor.execute("""
        CREATE INDEX idx_roofs_gebaeudeeinheit ON building_roofs(gebaeudeeinheit)
    """)
    cursor.execute("""
        CREATE INDEX idx_roofs_egid ON building_roofs(egid)
    """)

    conn.commit()
    logger.info("  + Tabelle erstellt: building_roofs")
    return True


def create_building_walls(conn):
    """
    Erstellt die building_walls Tabelle.

    Wird nur on-demand für komplexe Gebäude befüllt.
    Enthält 3D-Fassadengeometrie.
    """
    cursor = conn.cursor()

    if check_table_exists(conn, "building_walls"):
        logger.info("  - Tabelle building_walls existiert bereits")
        return False

    cursor.execute("""
        CREATE TABLE building_walls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gebaeudeeinheit TEXT NOT NULL,
            egid TEXT,

            -- Höhen
            z_min REAL,                 -- Geländepunkt
            z_max REAL,                 -- Traufhöhe

            -- 3D-Geometrie
            geometry_wkb BLOB,          -- 3D MultiPolygon als WKB

            -- Metadaten
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX idx_walls_gebaeudeeinheit ON building_walls(gebaeudeeinheit)
    """)
    cursor.execute("""
        CREATE INDEX idx_walls_egid ON building_walls(egid)
    """)

    conn.commit()
    logger.info("  + Tabelle erstellt: building_walls")
    return True


def create_building_floors(conn):
    """
    Erstellt die building_floors Tabelle.

    Wird nur on-demand für komplexe Gebäude befüllt.
    Floor ≈ Building_solid (Median +0.02%), aber exakter für Fassadenpositionen.
    """
    cursor = conn.cursor()

    if check_table_exists(conn, "building_floors"):
        logger.info("  - Tabelle building_floors existiert bereits")
        return False

    cursor.execute("""
        CREATE TABLE building_floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gebaeudeeinheit TEXT NOT NULL,
            egid TEXT,

            -- Höhe
            gelaendepunkt REAL,         -- Terrainhöhe

            -- 3D-Geometrie (2.5D - alle Z gleich)
            geometry_wkb BLOB,          -- MultiPolygon als WKB

            -- Metadaten
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX idx_floors_gebaeudeeinheit ON building_floors(gebaeudeeinheit)
    """)
    cursor.execute("""
        CREATE INDEX idx_floors_egid ON building_floors(egid)
    """)

    conn.commit()
    logger.info("  + Tabelle erstellt: building_floors")
    return True


def create_migration_log(conn):
    """Erstellt eine Migrations-Log Tabelle falls nicht vorhanden."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migration_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)
    conn.commit()


def is_migration_applied(conn) -> bool:
    """Prüft ob diese Migration bereits angewendet wurde."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM migration_log WHERE version = ?
    """, (MIGRATION_VERSION,))
    return cursor.fetchone() is not None


def mark_migration_applied(conn, description: str):
    """Markiert die Migration als angewendet."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO migration_log (version, description)
        VALUES (?, ?)
    """, (MIGRATION_VERSION, description))
    conn.commit()


def run_migration():
    """Führt die Migration aus."""
    logger.info(f"=== Migration {MIGRATION_VERSION} ===")
    logger.info(f"Datenbank: {BUILDING_3D_DB}")

    conn = get_connection()

    # Migrations-Log erstellen
    create_migration_log(conn)

    # Prüfen ob bereits angewendet
    if is_migration_applied(conn):
        logger.info("Migration wurde bereits angewendet. Nichts zu tun.")
        conn.close()
        return True

    try:
        # 1. buildings_3d erweitern
        logger.info("\n1. Erweitere buildings_3d...")
        columns_added = migrate_buildings_3d(conn)

        # 2. building_roofs erstellen
        logger.info("\n2. Erstelle building_roofs...")
        roofs_created = create_building_roofs(conn)

        # 3. building_walls erstellen
        logger.info("\n3. Erstelle building_walls...")
        walls_created = create_building_walls(conn)

        # 4. building_floors erstellen
        logger.info("\n4. Erstelle building_floors...")
        floors_created = create_building_floors(conn)

        # Migration als angewendet markieren
        description = f"Added {columns_added} columns to buildings_3d, created roofs/walls/floors tables"
        mark_migration_applied(conn, description)

        logger.info(f"\n=== Migration erfolgreich ===")
        logger.info(f"  - {columns_added} neue Spalten in buildings_3d")
        logger.info(f"  - building_roofs: {'erstellt' if roofs_created else 'existierte'}")
        logger.info(f"  - building_walls: {'erstellt' if walls_created else 'existierte'}")
        logger.info(f"  - building_floors: {'erstellt' if floors_created else 'existierte'}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Migration fehlgeschlagen: {e}")
        conn.rollback()
        conn.close()
        return False


def run_rollback():
    """Macht die Migration rückgängig (VORSICHT!)."""
    logger.info(f"=== Rollback {MIGRATION_VERSION} ===")
    logger.warning("WARNUNG: Dies löscht die 3D-Layer Tabellen und deren Daten!")

    confirm = input("Fortfahren? (ja/nein): ")
    if confirm.lower() != "ja":
        logger.info("Rollback abgebrochen.")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Tabellen löschen
        cursor.execute("DROP TABLE IF EXISTS building_roofs")
        logger.info("  - building_roofs gelöscht")

        cursor.execute("DROP TABLE IF EXISTS building_walls")
        logger.info("  - building_walls gelöscht")

        cursor.execute("DROP TABLE IF EXISTS building_floors")
        logger.info("  - building_floors gelöscht")

        # Spalten können in SQLite nicht einfach gelöscht werden
        # Wir markieren nur die Migration als nicht angewendet
        cursor.execute("DELETE FROM migration_log WHERE version = ?", (MIGRATION_VERSION,))

        conn.commit()
        logger.info("Rollback erfolgreich.")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Rollback fehlgeschlagen: {e}")
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migration 001: Add 3D Layer Tables")
    parser.add_argument("--rollback", action="store_true", help="Rollback der Migration")

    args = parser.parse_args()

    if args.rollback:
        success = run_rollback()
    else:
        success = run_migration()

    sys.exit(0 if success else 1)