"""
Tile Cache Service
==================

Persistenter Cache für swissBUILDINGS3D Tiles (GDB-Dateien).

Architektur (3 Stufen):
  1. EGID → Tile-ID Index (SQLite)
  2. Koordinaten → Tile-ID (Berechnung, kein API-Call!)
  3. Tile-ID → Lokaler Pfad (Disk-Cache)

Vorteile:
  - Tile-Download nur 1x pro Tile (statt bei jedem Request)
  - EGID-Lookup ohne GDB-Parsing (nach erstem Import)
  - ~8-15s → ~1ms für gecachte Gebäude
"""

import sqlite3
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from contextlib import contextmanager

# Pfade
DATA_DIR = Path(__file__).parent.parent / "data"
TILES_DIR = DATA_DIR / "tiles"
TILE_CACHE_DB = DATA_DIR / "tiles.db"


def lv95_to_tile_id(e: float, n: float) -> str:
    """
    Convert LV95 coordinates to swissBUILDINGS3D tile reference.

    The tiles are based on a 1km grid. The tile reference has format:
    XXXX-YY where XXXX is the main tile and YY is the sub-tile (1-4 x 1-4 grid).

    Args:
        e: LV95 Easting (typically 2480000-2850000)
        n: LV95 Northing (typically 1070000-1300000)

    Returns:
        Tile reference string like "1088-22"

    Example:
        >>> lv95_to_tile_id(2600450, 1199830)
        '1088-22'
    """
    # Ensure LV95 (convert from LV03 if needed)
    if e < 1_000_000:
        e = e + 2_000_000
        n = n + 1_000_000

    # km-Grid position
    e_km = int(e / 1000)  # e.g., 2600123 -> 2600
    n_km = int(n / 1000)  # e.g., 1199456 -> 1199

    # Main tile is based on 4km grid (4 sub-tiles per main tile)
    main_e = (e_km - 2480) // 4  # Offset from western border
    main_n = (n_km - 1070) // 4  # Offset from southern border

    # Sub-tile within the 4km main tile (1-4 in each direction)
    sub_e = ((e_km - 2480) % 4) + 1
    sub_n = ((n_km - 1070) % 4) + 1

    # Main tile number (combining E and N)
    main_tile = 1000 + main_e * 10 + main_n

    # Sub-tile (2 digits: row * 10 + col)
    sub_tile = sub_n * 10 + sub_e

    return f"{main_tile}-{sub_tile}"


class TileCacheService:
    """
    Service für persistenten Tile-Cache.

    Speichert:
    - tiles.db: Index (tile_id → Metadaten, egid → tile_id)
    - tiles/: GDB-Verzeichnisse (tile_id.gdb/)
    """

    def __init__(self):
        """Initialisiert den Tile-Cache."""
        self._init_storage()

    def _init_storage(self):
        """Erstellt Verzeichnisse und Datenbank-Schema."""
        # Verzeichnisse
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TILES_DIR.mkdir(parents=True, exist_ok=True)

        # Schema
        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()

            # Tiles-Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tiles (
                    tile_id TEXT PRIMARY KEY,
                    local_path TEXT NOT NULL,
                    download_url TEXT,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size_mb REAL,
                    building_count INTEGER DEFAULT 0,
                    bbox_west REAL,
                    bbox_south REAL,
                    bbox_east REAL,
                    bbox_north REAL
                )
            """)

            # EGID → Tile-ID Index
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS egid_tile_index (
                    egid INTEGER PRIMARY KEY,
                    tile_id TEXT NOT NULL,
                    lv95_e REAL,
                    lv95_n REAL,
                    FOREIGN KEY (tile_id) REFERENCES tiles(tile_id)
                )
            """)

            # Index für schnelle Tile-Lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_egid_tile
                ON egid_tile_index(tile_id)
            """)

            conn.commit()

    def get_tile_path(self, tile_id: str) -> Optional[Path]:
        """
        Prüft ob ein Tile im Cache ist und gibt den Pfad zurück.

        Args:
            tile_id: Tile-Referenz (z.B. "1088-22")

        Returns:
            Path zum GDB-Verzeichnis oder None
        """
        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT local_path FROM tiles WHERE tile_id = ?",
                (tile_id,)
            )
            result = cursor.fetchone()

            if result:
                path = Path(result[0])
                if path.exists():
                    return path
                # Pfad in DB aber nicht auf Disk → Entry löschen
                cursor.execute("DELETE FROM tiles WHERE tile_id = ?", (tile_id,))
                conn.commit()

        return None

    def get_tile_for_coordinates(self, e: float, n: float) -> Optional[Path]:
        """
        Gibt den gecachten Tile-Pfad für Koordinaten zurück.

        Berechnet Tile-ID aus Koordinaten (KEIN API-Call!).

        Args:
            e: LV95 Easting
            n: LV95 Northing

        Returns:
            Path zum GDB-Verzeichnis oder None wenn nicht gecacht
        """
        tile_id = lv95_to_tile_id(e, n)
        return self.get_tile_path(tile_id)

    def store_tile(
        self,
        tile_id: str,
        gdb_path: Path,
        download_url: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> Path:
        """
        Speichert ein heruntergeladenes Tile im Cache.

        Args:
            tile_id: Tile-Referenz (z.B. "1088-22")
            gdb_path: Pfad zum GDB-Verzeichnis (wird kopiert)
            download_url: Original-Download-URL (für Metadaten)
            bbox: Bounding Box (west, south, east, north)

        Returns:
            Pfad zum gecachten GDB-Verzeichnis
        """
        # Zielverzeichnis
        target_path = TILES_DIR / f"{tile_id}.gdb"

        # Kopieren wenn nicht bereits am Ziel
        if gdb_path != target_path:
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(gdb_path, target_path)

        # Grösse berechnen
        size_bytes = sum(
            f.stat().st_size
            for f in target_path.glob("**/*")
            if f.is_file()
        )
        size_mb = round(size_bytes / (1024 * 1024), 2)

        # In DB speichern
        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tiles
                (tile_id, local_path, download_url, file_size_mb,
                 bbox_west, bbox_south, bbox_east, bbox_north)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tile_id,
                str(target_path),
                download_url,
                size_mb,
                bbox[0] if bbox else None,
                bbox[1] if bbox else None,
                bbox[2] if bbox else None,
                bbox[3] if bbox else None
            ))
            conn.commit()

        return target_path

    def register_egid(self, egid: int, tile_id: str, e: float = None, n: float = None):
        """
        Registriert eine EGID → Tile-ID Zuordnung.

        Wird nach GDB-Parsing aufgerufen.
        """
        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO egid_tile_index
                (egid, tile_id, lv95_e, lv95_n)
                VALUES (?, ?, ?, ?)
            """, (egid, tile_id, e, n))
            conn.commit()

    def bulk_register_egids(self, entries: List[Dict[str, Any]], tile_id: str):
        """
        Registriert mehrere EGIDs auf einmal.

        Args:
            entries: Liste von {egid, lv95_e, lv95_n}
            tile_id: Zugehöriges Tile
        """
        if not entries:
            return

        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO egid_tile_index
                (egid, tile_id, lv95_e, lv95_n)
                VALUES (:egid, :tile_id, :lv95_e, :lv95_n)
            """, [{**e, "tile_id": tile_id} for e in entries])

            # Building-Count im Tile aktualisieren
            cursor.execute("""
                UPDATE tiles SET building_count = ?
                WHERE tile_id = ?
            """, (len(entries), tile_id))

            conn.commit()

    def get_tile_for_egid(self, egid: int) -> Optional[str]:
        """
        Findet das Tile für eine EGID (O(1) Lookup).

        Args:
            egid: Eidgenössischer Gebäudeidentifikator

        Returns:
            Tile-ID oder None
        """
        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tile_id FROM egid_tile_index WHERE egid = ?",
                (egid,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück."""
        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()

            # Tile-Anzahl
            cursor.execute("SELECT COUNT(*) FROM tiles")
            tile_count = cursor.fetchone()[0]

            # EGID-Anzahl
            cursor.execute("SELECT COUNT(*) FROM egid_tile_index")
            egid_count = cursor.fetchone()[0]

            # Gesamtgrösse
            cursor.execute("SELECT COALESCE(SUM(file_size_mb), 0) FROM tiles")
            total_size_mb = cursor.fetchone()[0]

            # Neueste Tiles
            cursor.execute("""
                SELECT tile_id, downloaded_at, building_count, file_size_mb
                FROM tiles
                ORDER BY downloaded_at DESC
                LIMIT 5
            """)
            recent = [
                {
                    "tile_id": row[0],
                    "downloaded_at": row[1],
                    "building_count": row[2],
                    "file_size_mb": row[3]
                }
                for row in cursor.fetchall()
            ]

            return {
                "tile_count": tile_count,
                "egid_count": egid_count,
                "total_size_mb": round(total_size_mb, 2),
                "tiles_dir": str(TILES_DIR),
                "db_path": str(TILE_CACHE_DB),
                "recent_tiles": recent
            }

    def clear_cache(self, older_than_days: int = None) -> int:
        """
        Löscht Cache-Einträge.

        Args:
            older_than_days: Nur Tiles älter als X Tage löschen.
                            None = alles löschen.

        Returns:
            Anzahl gelöschter Tiles
        """
        with sqlite3.connect(TILE_CACHE_DB) as conn:
            cursor = conn.cursor()

            if older_than_days:
                cursor.execute("""
                    SELECT tile_id, local_path FROM tiles
                    WHERE downloaded_at < datetime('now', ?)
                """, (f"-{older_than_days} days",))
            else:
                cursor.execute("SELECT tile_id, local_path FROM tiles")

            tiles_to_delete = cursor.fetchall()

            for tile_id, local_path in tiles_to_delete:
                # Dateien löschen
                path = Path(local_path)
                if path.exists():
                    shutil.rmtree(path, ignore_errors=True)

                # DB-Einträge löschen
                cursor.execute(
                    "DELETE FROM egid_tile_index WHERE tile_id = ?",
                    (tile_id,)
                )
                cursor.execute(
                    "DELETE FROM tiles WHERE tile_id = ?",
                    (tile_id,)
                )

            conn.commit()
            return len(tiles_to_delete)


# Singleton-Instanz
_tile_cache: Optional[TileCacheService] = None


def get_tile_cache() -> TileCacheService:
    """Gibt die Singleton-Instanz des TileCacheService zurück."""
    global _tile_cache
    if _tile_cache is None:
        _tile_cache = TileCacheService()
    return _tile_cache
