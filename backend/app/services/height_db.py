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

        # Haupttabelle für Gebäudehöhen (Legacy, wird noch unterstützt)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_heights (
                egid INTEGER PRIMARY KEY,
                height_m REAL NOT NULL,
                height_type TEXT DEFAULT 'measured',  -- measured, estimated, lidar
                source TEXT,  -- z.B. 'swissBUILDINGS3D_3.0_BE'
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Erweiterte Tabelle für alle Höhentypen (Gerüstbau-relevant)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_heights_detailed (
                egid INTEGER PRIMARY KEY,
                traufhoehe_m REAL,           -- Dachhöhe min - Terrain (Eave height)
                firsthoehe_m REAL,           -- Dachhöhe max - Terrain (Ridge height)
                gebaeudehoehe_m REAL,        -- Gesamthöhe (Building height)
                dach_max_m REAL,             -- Absolut ü.M.
                dach_min_m REAL,             -- Absolut ü.M.
                terrain_m REAL,              -- Geländepunkt ü.M.
                source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index für schnelle Lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_egid ON building_heights(egid)
        """)

        # Koordinaten-basierte Höhentabelle (für Gebäude ohne EGID)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_heights_by_coord (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lv95_e REAL NOT NULL,
                lv95_n REAL NOT NULL,
                uuid TEXT,
                traufhoehe_m REAL,
                firsthoehe_m REAL,
                gebaeudehoehe_m REAL,
                dach_max_m REAL,
                dach_min_m REAL,
                terrain_m REAL,
                source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indizes für koordinatenbasierte Suche
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coord_e ON building_heights_by_coord(lv95_e)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coord_n ON building_heights_by_coord(lv95_n)
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

    print(f"[OK] Hoehendatenbank initialisiert: {HEIGHT_DB_PATH}")


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


def get_building_heights_detailed(egid: int) -> Optional[dict]:
    """
    Alle Höhenwerte für ein Gebäude aus der Datenbank abrufen.

    Args:
        egid: Eidgenössischer Gebäudeidentifikator

    Returns:
        Dict mit allen Höhenwerten oder None wenn nicht gefunden
        {
            "traufhoehe_m": float,      # Höhe Dachtraufe
            "firsthoehe_m": float,      # Höhe Dachfirst
            "gebaeudehoehe_m": float,   # Gesamthöhe Gebäude
            "dach_max_m": float,        # Absolut ü.M.
            "dach_min_m": float,        # Absolut ü.M.
            "terrain_m": float,         # Terrain ü.M.
            "source": str
        }
    """
    if not HEIGHT_DB_PATH.exists():
        return None

    try:
        with sqlite3.connect(HEIGHT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                       dach_max_m, dach_min_m, terrain_m, source
                FROM building_heights_detailed
                WHERE egid = ?
            """, (egid,))
            result = cursor.fetchone()

            if result:
                return {
                    "traufhoehe_m": result[0],
                    "firsthoehe_m": result[1],
                    "gebaeudehoehe_m": result[2],
                    "dach_max_m": result[3],
                    "dach_min_m": result[4],
                    "terrain_m": result[5],
                    "source": f"database:{result[6]}"
                }
            return None

    except sqlite3.Error as e:
        print(f"SQLite Error: {e}")
        return None


def insert_building_heights_detailed(
    egid: int,
    traufhoehe_m: Optional[float] = None,
    firsthoehe_m: Optional[float] = None,
    gebaeudehoehe_m: Optional[float] = None,
    dach_max_m: Optional[float] = None,
    dach_min_m: Optional[float] = None,
    terrain_m: Optional[float] = None,
    source: str = "unknown"
):
    """
    Detaillierte Gebäudehöhen in die Datenbank einfügen.
    """
    with sqlite3.connect(HEIGHT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO building_heights_detailed
            (egid, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
             dach_max_m, dach_min_m, terrain_m, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (egid, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
              dach_max_m, dach_min_m, terrain_m, source))
        conn.commit()


def bulk_insert_heights_detailed(data: list, source: str = "unknown"):
    """
    Mehrere detaillierte Gebäudehöhen auf einmal einfügen.

    Args:
        data: Liste von dicts mit {egid, traufhoehe_m, firsthoehe_m, ...}
        source: Datenquelle
    """
    with sqlite3.connect(HEIGHT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR REPLACE INTO building_heights_detailed
            (egid, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
             dach_max_m, dach_min_m, terrain_m, source)
            VALUES (:egid, :traufhoehe_m, :firsthoehe_m, :gebaeudehoehe_m,
                    :dach_max_m, :dach_min_m, :terrain_m, :source)
        """, [{**d, "source": source} for d in data])
        conn.commit()

    return len(data)


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


def get_building_height_by_coordinates(
    e: float,
    n: float,
    tolerance_m: float = 25.0
) -> Optional[dict]:
    """
    Gebäudehöhe per Koordinaten suchen (für Gebäude ohne EGID).

    Sucht das nächstgelegene Gebäude innerhalb der Toleranz.

    Args:
        e: Easting (LV03 oder LV95)
        n: Northing (LV03 oder LV95)
        tolerance_m: Suchradius in Metern (default 25m)

    Returns:
        Dict mit Höhenwerten oder None wenn nicht gefunden
    """
    if not HEIGHT_DB_PATH.exists():
        return None

    # Convert LV03 to LV95 if needed (DB stores LV95)
    if e < 1_000_000:
        e = e + 2_000_000
        n = n + 1_000_000

    # Ensure table exists (migration support)
    try:
        init_database()
    except Exception:
        pass

    try:
        with sqlite3.connect(HEIGHT_DB_PATH) as conn:
            cursor = conn.cursor()

            # Suche im Rechteck ±tolerance, sortiert nach Distanz
            cursor.execute("""
                SELECT uuid, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                       dach_max_m, dach_min_m, terrain_m, source, lv95_e, lv95_n,
                       ((lv95_e - ?) * (lv95_e - ?) + (lv95_n - ?) * (lv95_n - ?)) as dist_sq
                FROM building_heights_by_coord
                WHERE lv95_e BETWEEN ? AND ?
                  AND lv95_n BETWEEN ? AND ?
                ORDER BY dist_sq
                LIMIT 1
            """, (e, e, n, n,
                  e - tolerance_m, e + tolerance_m,
                  n - tolerance_m, n + tolerance_m))
            result = cursor.fetchone()

            if result:
                dist_m = (result[10] ** 0.5) if result[10] else 0
                return {
                    "uuid": result[0],
                    "traufhoehe_m": result[1],
                    "firsthoehe_m": result[2],
                    "gebaeudehoehe_m": result[3],
                    "dach_max_m": result[4],
                    "dach_min_m": result[5],
                    "terrain_m": result[6],
                    "source": f"database_coord:{result[7]}",
                    "matched_e": result[8],
                    "matched_n": result[9],
                    "distance_m": round(dist_m, 1)
                }
            return None

    except sqlite3.Error as err:
        print(f"SQLite Error in coord lookup: {err}")
        return None


def bulk_insert_heights_by_coord(data: list, source: str = "unknown") -> int:
    """
    Mehrere koordinatenbasierte Gebäudehöhen einfügen.

    Args:
        data: Liste von dicts mit {lv95_e, lv95_n, uuid, traufhoehe_m, ...}
        source: Datenquelle

    Returns:
        Anzahl eingefügter Datensätze
    """
    if not data:
        return 0

    with sqlite3.connect(HEIGHT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO building_heights_by_coord
            (lv95_e, lv95_n, uuid, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
             dach_max_m, dach_min_m, terrain_m, source)
            VALUES (:lv95_e, :lv95_n, :uuid, :traufhoehe_m, :firsthoehe_m, :gebaeudehoehe_m,
                    :dach_max_m, :dach_min_m, :terrain_m, :source)
        """, [{**d, "source": source} for d in data])
        conn.commit()

    return len(data)
