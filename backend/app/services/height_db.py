"""
Building Height Database Service
================================

SQLite-basierte Datenbank für Gebäudehöhen aus swissBUILDINGS3D.
Wird als Fallback verwendet, bevor auf Schätzungen zurückgegriffen wird.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, Tuple
from contextlib import contextmanager

# Pfad zur Höhendatenbank
DATA_DIR = Path(__file__).parent.parent / "data"
HEIGHT_DB_PATH = DATA_DIR / "building_heights.db"


def get_db_path() -> Path:
    """Gibt den Pfad zur Höhendatenbank zurück"""
    return HEIGHT_DB_PATH


def init_database():
    """Initialisiert die Höhendatenbank mit dem Schema"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(HEIGHT_DB_PATH) as conn:
        cursor = conn.cursor()

        # Haupttabelle für Gebäudehöhen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_heights (
                egid INTEGER PRIMARY KEY,
                height_m REAL NOT NULL,
                height_type TEXT DEFAULT 'measured',  -- measured, estimated, lidar
                source TEXT,  -- z.B. 'swissBUILDINGS3D_3.0_BE'
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index für schnelle Lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_egid ON building_heights(egid)
        """)

        # Metadaten-Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                canton TEXT,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                records_imported INTEGER,
                data_version TEXT
            )
        """)

        conn.commit()

    print(f"✅ Höhendatenbank initialisiert: {HEIGHT_DB_PATH}")


def get_building_height(egid: int) -> Optional[Tuple[float, str]]:
    """
    Höhe für ein Gebäude aus der Datenbank abrufen.

    Args:
        egid: Eidgenössischer Gebäudeidentifikator

    Returns:
        Tuple (Höhe in Metern, Quelle) oder None wenn nicht gefunden
    """
    if not HEIGHT_DB_PATH.exists():
        return None

    try:
        with sqlite3.connect(HEIGHT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT height_m, source FROM building_heights WHERE egid = ?",
                (egid,)
            )
            result = cursor.fetchone()

            if result:
                return (result[0], f"database:{result[1]}")
            return None

    except sqlite3.Error as e:
        print(f"SQLite Error: {e}")
        return None


def insert_building_height(
    egid: int,
    height_m: float,
    source: str = "unknown",
    height_type: str = "measured"
):
    """
    Gebäudehöhe in die Datenbank einfügen.

    Args:
        egid: Eidgenössischer Gebäudeidentifikator
        height_m: Höhe in Metern
        source: Datenquelle (z.B. 'swissBUILDINGS3D_3.0_BE')
        height_type: Art der Höhe ('measured', 'estimated', 'lidar')
    """
    with sqlite3.connect(HEIGHT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO building_heights (egid, height_m, height_type, source)
            VALUES (?, ?, ?, ?)
        """, (egid, height_m, height_type, source))
        conn.commit()


def bulk_insert_heights(data: list, source: str = "unknown"):
    """
    Mehrere Gebäudehöhen auf einmal einfügen (für Import).

    Args:
        data: Liste von (egid, height_m) Tuples
        source: Datenquelle
    """
    with sqlite3.connect(HEIGHT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR REPLACE INTO building_heights (egid, height_m, source)
            VALUES (?, ?, ?)
        """, [(egid, height, source) for egid, height in data])
        conn.commit()

    return len(data)


def get_database_stats() -> dict:
    """Statistiken über die Höhendatenbank abrufen"""
    if not HEIGHT_DB_PATH.exists():
        return {"exists": False, "records": 0}

    try:
        with sqlite3.connect(HEIGHT_DB_PATH) as conn:
            cursor = conn.cursor()

            # Anzahl Einträge
            cursor.execute("SELECT COUNT(*) FROM building_heights")
            count = cursor.fetchone()[0]

            # Quellen
            cursor.execute("""
                SELECT source, COUNT(*) as cnt
                FROM building_heights
                GROUP BY source
            """)
            sources = {row[0]: row[1] for row in cursor.fetchall()}

            # Letzte Imports
            cursor.execute("""
                SELECT source_file, canton, import_date, records_imported
                FROM import_metadata
                ORDER BY import_date DESC
                LIMIT 5
            """)
            imports = [
                {
                    "file": row[0],
                    "canton": row[1],
                    "date": row[2],
                    "records": row[3]
                }
                for row in cursor.fetchall()
            ]

            return {
                "exists": True,
                "records": count,
                "sources": sources,
                "recent_imports": imports,
                "db_size_mb": round(HEIGHT_DB_PATH.stat().st_size / 1024 / 1024, 2)
            }

    except sqlite3.Error as e:
        return {"exists": True, "error": str(e)}


def log_import(source_file: str, canton: str, records: int, version: str = None):
    """Import in Metadaten-Tabelle protokollieren"""
    with sqlite3.connect(HEIGHT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO import_metadata (source_file, canton, records_imported, data_version)
            VALUES (?, ?, ?, ?)
        """, (source_file, canton, records, version))
        conn.commit()
