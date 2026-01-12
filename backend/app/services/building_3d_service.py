# backend/app/services/building_3d_service.py
"""
Building 3D Data Service
========================

Unabhängiger Cache für swissBUILDINGS3D Gebäudedaten.

WICHTIG: Diese Datenbank ist UNABHÄNGIG von anderen Caches!
- Enthält NUR Rohdaten aus swissBUILDINGS3D Tiles
- Wird vom tile_prefetch.py befüllt
- Ermöglicht O(1) Lookups statt GDB-Parsing

Schema:
    buildings_3d (
        egid INTEGER PRIMARY KEY,
        polygon JSON,           -- [[e,n], [e,n], ...]
        traufhoehe_m REAL,
        firsthoehe_m REAL,
        gebaeudehoehe_m REAL,
        area_m2 REAL,
        perimeter_m REAL,
        center_e REAL,          -- LV95 Zentroid
        center_n REAL,
        tile_id TEXT,           -- Quell-Tile für Debugging
        imported_at TIMESTAMP,
        source TEXT,            -- 'swissBUILDINGS3D_3.0'
        -- NEU 11.01.2026: Erweiterte Attribute
        objektart TEXT,         -- Gebäudetyp aus swissBUILDINGS3D
        name_komplett TEXT,     -- Gebäudename (wenn vorhanden)
        gebaeude_nutzung TEXT,  -- Nutzungsart
        gebaeudeeinheit TEXT,   -- Verknüpfung zu anderen Layern
        roof_form TEXT,         -- Berechnete Dachform
        roof_form_confidence REAL, -- Konfidenz der Erkennung (0-1)
        roof_orientation TEXT,  -- First-Verlauf (N-S, O-W, etc.)
        has_3d_layers INTEGER   -- Flag für erweiterte 3D-Daten
    )

    building_roofs (id, gebaeudeeinheit, egid, dach_min, dach_max,
                    roof_form, roof_angle_deg, roof_orientation, z_levels,
                    geometry_wkb, has_full_geometry, calculated_at, calculation_method)

    building_walls (id, gebaeudeeinheit, egid, z_min, z_max,
                    geometry_wkb, created_at)

    building_floors (id, gebaeudeeinheit, egid, gelaendepunkt,
                     geometry_wkb, created_at)

Batch-Import:
    python -m app.services.building_3d_service --import-tile 1332-21

Verwendung:
    from app.services.building_3d_service import get_building_3d_service

    service = get_building_3d_service()
    building = service.get_by_egid(1243792)
    if building:
        polygon = building['polygon']
        traufhoehe = building['traufhoehe_m']
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager
from threading import local

logger = logging.getLogger(__name__)

# Optimierungs-Konstanten (BATCH_IMPORT.md Anhang A)
BATCH_SIZE = 5000  # Task 2: Erhöht von 1000 auf 5000
PRAGMA_CACHE_SIZE = -64000  # 64MB Cache
PRAGMA_MMAP_SIZE = 268435456  # 256MB Memory-Mapped I/O

# Pfad zur Datenbank - UNABHÄNGIG von anderen DBs
DATA_DIR = Path(__file__).parent.parent / "data"
BUILDING_3D_DB = DATA_DIR / "building_3d.db"


class Building3DService:
    """
    Service für swissBUILDINGS3D Gebäudedaten.

    UNABHÄNGIG von:
    - smart_building_cache.db (Bundle-Cache)
    - building_contexts.db (Zonen, Terrain, etc.)
    - tiles.db (Tile-Metadaten)

    Enthält NUR:
    - Polygon (Gebäudegrundriss)
    - Höhen (Trauf, First, Gesamt)
    - Geometrie-Daten (Fläche, Umfang, Zentroid)

    OPTIMIERUNGEN (BATCH_IMPORT.md Anhang A):
    - Task 1: Aggressive PRAGMAs (WAL, synchronous, cache_size, mmap)
    - Task 2: Batch-Size 5000 (statt 1000)
    - Task 3: Deferred Index für Batch-Import
    - Task 4: Prepared Statements (wiederverwendet)
    - Task 5: Thread-lokale Connection Pooling
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # Task 5: Thread-lokaler Storage für Connections
        self._local = local()
        # Task 4: Prepared Statement Cache
        self._prepared_insert = None
        self._init_database()
        self._initialized = True

    def _init_database(self):
        """Erstellt Datenbank-Schema falls nicht vorhanden."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(BUILDING_3D_DB) as conn:
            cursor = conn.cursor()

            # Haupttabelle für Gebäudedaten (erweitert 11.01.2026)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS buildings_3d (
                    egid INTEGER PRIMARY KEY,
                    polygon TEXT,
                    traufhoehe_m REAL,
                    firsthoehe_m REAL,
                    gebaeudehoehe_m REAL,
                    area_m2 REAL,
                    perimeter_m REAL,
                    center_e REAL,
                    center_n REAL,
                    tile_id TEXT,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'swissBUILDINGS3D_3.0',
                    -- NEU 11.01.2026: Erweiterte Attribute
                    objektart TEXT,
                    name_komplett TEXT,
                    gebaeude_nutzung TEXT,
                    gebaeudeeinheit TEXT,
                    roof_form TEXT,
                    roof_form_confidence REAL,
                    roof_orientation TEXT,
                    has_3d_layers INTEGER DEFAULT 0
                )
            """)

            # NEU 11.01.2026: building_roofs Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS building_roofs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gebaeudeeinheit TEXT NOT NULL,
                    egid TEXT,
                    dach_min REAL,
                    dach_max REAL,
                    roof_form TEXT,
                    roof_angle_deg REAL,
                    roof_orientation TEXT,
                    z_levels TEXT,
                    geometry_wkb BLOB,
                    has_full_geometry INTEGER DEFAULT 0,
                    calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    calculation_method TEXT
                )
            """)

            # NEU 11.01.2026: building_walls Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS building_walls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gebaeudeeinheit TEXT NOT NULL,
                    egid TEXT,
                    z_min REAL,
                    z_max REAL,
                    geometry_wkb BLOB,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # NEU 11.01.2026: building_floors Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS building_floors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gebaeudeeinheit TEXT NOT NULL,
                    egid TEXT,
                    gelaendepunkt REAL,
                    geometry_wkb BLOB,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Index für Koordinaten-Suche (Nachbargebäude)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_buildings_3d_coords
                ON buildings_3d(center_e, center_n)
            """)

            # Index für Tile-Zuordnung (Batch-Operationen)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_buildings_3d_tile
                ON buildings_3d(tile_id)
            """)

            # Import-Log für Batch-Tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS import_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tile_id TEXT,
                    buildings_count INTEGER,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds REAL,
                    source TEXT
                )
            """)

            conn.commit()

        logger.info(f"Building 3D database initialized: {BUILDING_3D_DB}")

    def _setup_connection(self, conn: sqlite3.Connection):
        """
        Task 1: Aggressive PRAGMAs für optimale Performance.

        Konfiguriert SQLite für maximale Bulk-Import-Geschwindigkeit.
        """
        # WAL-Mode: Bessere Parallelität (Reads während Write)
        conn.execute("PRAGMA journal_mode=WAL")

        # NORMAL statt FULL: Weniger fsync, ~30% schneller
        # Risiko: Bei Crash können letzte Transaktionen verloren gehen
        # Für Batch-Import OK, da wir bei Fehler sowieso neu starten
        conn.execute("PRAGMA synchronous=NORMAL")

        # Grösserer Cache: 64MB statt default 2MB
        conn.execute(f"PRAGMA cache_size={PRAGMA_CACHE_SIZE}")

        # Temp-Tabellen im RAM
        conn.execute("PRAGMA temp_store=MEMORY")

        # Memory-Mapped I/O: 256MB
        conn.execute(f"PRAGMA mmap_size={PRAGMA_MMAP_SIZE}")

    @contextmanager
    def _get_connection(self, pooled: bool = True):
        """
        Task 5: Thread-lokale Connection für bessere Performance.

        Args:
            pooled: True = Thread-lokale wiederverwendete Connection
                   False = Neue Connection (für spezielle Fälle)
        """
        if pooled:
            # Thread-lokale Connection wiederverwenden
            if not hasattr(self._local, 'conn') or self._local.conn is None:
                self._local.conn = sqlite3.connect(
                    BUILDING_3D_DB,
                    check_same_thread=False
                )
                self._local.conn.row_factory = sqlite3.Row
                self._setup_connection(self._local.conn)

            try:
                yield self._local.conn
            except Exception:
                # Bei Fehler: Connection zurücksetzen
                if hasattr(self._local, 'conn') and self._local.conn:
                    try:
                        self._local.conn.rollback()
                    except Exception:
                        pass
                raise
        else:
            # Neue Connection (nicht gepoolt)
            conn = sqlite3.connect(BUILDING_3D_DB)
            conn.row_factory = sqlite3.Row
            self._setup_connection(conn)
            try:
                yield conn
            finally:
                conn.close()

    def get_by_egid(self, egid: int) -> Optional[Dict[str, Any]]:
        """
        Holt Gebäudedaten per EGID.

        Args:
            egid: Eidgenössischer Gebäudeidentifikator

        Returns:
            Dict mit Polygon, Höhen, etc. oder None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM buildings_3d WHERE egid = ?
            """, (egid,))

            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)

            # Polygon von JSON string zu Liste konvertieren
            if result.get('polygon'):
                try:
                    result['polygon'] = json.loads(result['polygon'])
                except json.JSONDecodeError:
                    result['polygon'] = None

            return result

    def get_by_coordinates(
        self,
        e: float,
        n: float,
        tolerance_m: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Sucht Gebäude per Koordinaten mit Point-in-Polygon Check.

        FIX 12.01.2026 03:00 BUG-018: Verwendet jetzt Point-in-Polygon statt
        nur nächstes Zentrum. Bei Reihenhäusern liegt der Hauseingang oft
        näher am Nachbar-Zentrum als am eigenen Gebäude-Zentrum.

        Args:
            e: LV95 Easting
            n: LV95 Northing
            tolerance_m: Suchradius in Metern

        Returns:
            Gebäude dessen Polygon den Punkt enthält, oder None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Alle Kandidaten im Radius laden (nicht nur nächstes!)
            cursor.execute("""
                SELECT *,
                       ((center_e - ?) * (center_e - ?) +
                        (center_n - ?) * (center_n - ?)) as dist_sq
                FROM buildings_3d
                WHERE center_e BETWEEN ? AND ?
                  AND center_n BETWEEN ? AND ?
                ORDER BY dist_sq ASC
            """, (
                e, e, n, n,
                e - tolerance_m, e + tolerance_m,
                n - tolerance_m, n + tolerance_m
            ))

            rows = cursor.fetchall()
            if not rows:
                logger.debug(f"[get_by_coordinates] Keine Kandidaten im {tolerance_m}m Radius um ({e:.1f}, {n:.1f})")
                return None

            logger.debug(f"[get_by_coordinates] {len(rows)} Kandidaten im {tolerance_m}m Radius um ({e:.1f}, {n:.1f})")

            # Point-in-Polygon Check für alle Kandidaten
            for row in rows:
                result = dict(row)
                egid = result.get('egid')
                dist = (result['dist_sq'] ** 0.5) if result.get('dist_sq') else 0

                # Polygon parsen
                polygon = None
                if result.get('polygon'):
                    try:
                        polygon = json.loads(result['polygon']) if isinstance(result['polygon'], str) else result['polygon']
                    except json.JSONDecodeError:
                        pass

                if not polygon:
                    logger.debug(f"[get_by_coordinates] EGID {egid}: Kein Polygon, überspringe")
                    continue

                # Point-in-Polygon Check
                if self._point_in_polygon(e, n, polygon):
                    logger.info(f"[get_by_coordinates] Point-in-Polygon MATCH: ({e:.1f}, {n:.1f}) → EGID {egid} (dist={dist:.1f}m)")
                    result['distance_m'] = dist
                    del result['dist_sq']
                    result['polygon'] = polygon
                    return result
                else:
                    logger.debug(f"[get_by_coordinates] EGID {egid}: Point-in-Polygon FALSE (dist={dist:.1f}m)")

            # Kein Match - None zurückgeben damit Stufe 2/3 verwendet wird
            first = dict(rows[0])
            first_egid = first.get('egid')
            first_dist = (first['dist_sq'] ** 0.5) if first.get('dist_sq') else 0
            logger.warning(
                f"[get_by_coordinates] Kein Polygon-Match für ({e:.1f}, {n:.1f}). "
                f"Nächstes Zentrum wäre EGID {first_egid} (dist={first_dist:.1f}m). "
                f"Geprüft: {len(rows)} Kandidaten. → Fallback auf Stufe 2/3"
            )
            return None

    def _point_in_polygon(self, px: float, py: float, polygon: list) -> bool:
        """
        Prüft ob ein Punkt innerhalb eines Polygons liegt (Ray-Casting).

        Args:
            px, py: Punkt-Koordinaten
            polygon: Liste von [x, y] Koordinaten

        Returns:
            True wenn Punkt im Polygon liegt
        """
        n = len(polygon)
        if n < 3:
            return False

        inside = False
        j = n - 1

        for i in range(n):
            if isinstance(polygon[i], dict):
                xi, yi = polygon[i].get('x', 0), polygon[i].get('y', 0)
                xj, yj = polygon[j].get('x', 0), polygon[j].get('y', 0)
            else:
                xi, yi = polygon[i][0], polygon[i][1]
                xj, yj = polygon[j][0], polygon[j][1]

            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside

            j = i

        return inside

    def save(self, building: Dict[str, Any]) -> bool:
        """
        Speichert ein Gebäude in der Datenbank.

        Args:
            building: Dict mit egid, polygon, höhen, etc.

        Returns:
            True bei Erfolg
        """
        egid = building.get('egid')
        if not egid:
            logger.warning("Cannot save building without EGID")
            return False

        # Polygon zu JSON serialisieren
        polygon = building.get('polygon')
        if polygon and not isinstance(polygon, str):
            polygon = json.dumps(polygon)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # NEU 11.01.2026: Erweiterte Spalten
            cursor.execute("""
                INSERT OR REPLACE INTO buildings_3d
                (egid, polygon, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                 area_m2, perimeter_m, center_e, center_n, tile_id, source,
                 objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                 roof_form, roof_form_confidence, roof_orientation, has_3d_layers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                egid,
                polygon,
                building.get('traufhoehe_m'),
                building.get('firsthoehe_m'),
                building.get('gebaeudehoehe_m'),
                building.get('area_m2'),
                building.get('perimeter_m'),
                building.get('center_e') or building.get('coord_e'),
                building.get('center_n') or building.get('coord_n'),
                building.get('tile_id'),
                building.get('source', 'swissBUILDINGS3D_3.0'),
                building.get('objektart'),
                building.get('name_komplett'),
                building.get('gebaeude_nutzung'),
                building.get('gebaeudeeinheit'),
                building.get('roof_form'),
                building.get('roof_form_confidence'),
                building.get('roof_orientation'),
                building.get('has_3d_layers', 0)
            ))

            conn.commit()
            return True

    def _get_prepared_insert(self):
        """
        Task 4: Prepared Statement für Bulk-Insert.

        Wiederverwendet das gleiche Statement für alle Inserts.
        NEU 11.01.2026: Erweiterte Spalten für 3D-Layer.
        """
        if self._prepared_insert is None:
            self._prepared_insert = """
                INSERT OR REPLACE INTO buildings_3d
                (egid, polygon, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                 area_m2, perimeter_m, center_e, center_n, tile_id, source,
                 objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                 roof_form, roof_form_confidence, roof_orientation, has_3d_layers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        return self._prepared_insert

    def drop_indexes(self):
        """
        Task 3: Indexes vor Bulk-Import droppen.

        Beschleunigt den Import erheblich, da SQLite keine
        Index-Updates bei jedem Insert machen muss.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP INDEX IF EXISTS idx_buildings_3d_coords")
            cursor.execute("DROP INDEX IF EXISTS idx_buildings_3d_tile")
            conn.commit()
            logger.info("[OPTIMIZE] Indexes dropped for faster import")

    def create_indexes(self):
        """
        Task 3: Indexes nach Bulk-Import erstellen.

        Einmaliges Index-Erstellen am Ende ist viel schneller
        als inkrementelle Updates während des Imports.
        """
        start = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_buildings_3d_coords
                ON buildings_3d(center_e, center_n)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_buildings_3d_tile
                ON buildings_3d(tile_id)
            """)

            conn.commit()

        duration = (datetime.now() - start).total_seconds()
        logger.info(f"[OPTIMIZE] Indexes created in {duration:.2f}s")

    def bulk_save(
        self,
        buildings: List[Dict[str, Any]],
        tile_id: str = None,
        skip_index_update: bool = False
    ) -> int:
        """
        Speichert mehrere Gebäude in einer Transaktion.

        OPTIMIERT 10.01.2026 (BATCH_IMPORT.md Anhang A):
        - Task 1: PRAGMAs via _setup_connection()
        - Task 2: BATCH_SIZE = 5000 (statt 1000)
        - Task 3: skip_index_update für Batch-Import
        - Task 4: Prepared Statement wiederverwendet
        - Task 5: Connection Pooling via _get_connection()

        Args:
            buildings: Liste von Gebäude-Dicts
            tile_id: Optionale Tile-ID für alle Gebäude
            skip_index_update: True bei Batch-Import (Index am Ende erstellen)

        Returns:
            Anzahl gespeicherter Gebäude
        """
        if not buildings:
            return 0

        start_time = datetime.now()

        # Daten vorbereiten (Polygon serialisieren, ungültige filtern)
        # NEU 11.01.2026: Erweiterte Spalten für 3D-Layer
        prepared_data = []
        for building in buildings:
            egid = building.get('egid')
            if not egid:
                continue

            polygon = building.get('polygon')
            if polygon and not isinstance(polygon, str):
                polygon = json.dumps(polygon)

            prepared_data.append((
                egid,
                polygon,
                building.get('traufhoehe_m'),
                building.get('firsthoehe_m'),
                building.get('gebaeudehoehe_m'),
                building.get('area_m2'),
                building.get('perimeter_m'),
                building.get('center_e') or building.get('coord_e'),
                building.get('center_n') or building.get('coord_n'),
                tile_id or building.get('tile_id'),
                building.get('source', 'swissBUILDINGS3D_3.0'),
                # Erweiterte Attribute (11.01.2026)
                building.get('objektart'),
                building.get('name_komplett'),
                building.get('gebaeude_nutzung'),
                building.get('gebaeudeeinheit'),
                building.get('roof_form'),
                building.get('roof_form_confidence'),
                building.get('roof_orientation'),
                building.get('has_3d_layers', 0)
            ))

        if not prepared_data:
            return 0

        saved_count = 0

        # Task 4: Prepared Statement wiederverwenden
        insert_sql = self._get_prepared_insert()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Task 2: Batch-Insert mit BATCH_SIZE = 5000
            for i in range(0, len(prepared_data), BATCH_SIZE):
                batch = prepared_data[i:i + BATCH_SIZE]

                try:
                    cursor.executemany(insert_sql, batch)
                    saved_count += len(batch)
                except Exception as e:
                    logger.warning(f"Batch-Insert Fehler: {e}")
                    # Fallback: Einzelne Inserts für diesen Batch
                    for row in batch:
                        try:
                            cursor.execute(insert_sql, row)
                            saved_count += 1
                        except Exception as e2:
                            logger.warning(f"Failed to save EGID {row[0]}: {e2}")

            conn.commit()

            # Import loggen
            duration = (datetime.now() - start_time).total_seconds()
            if tile_id:
                cursor.execute("""
                    INSERT INTO import_log (tile_id, buildings_count, duration_seconds, source)
                    VALUES (?, ?, ?, ?)
                """, (tile_id, saved_count, duration, 'tile_prefetch'))
                conn.commit()

        ms_per_building = (duration * 1000 / saved_count) if saved_count > 0 else 0
        logger.info(
            f"[BULK] {saved_count} Gebäude gespeichert | "
            f"tile: {tile_id} | {duration:.2f}s | {ms_per_building:.2f}ms/Gebäude"
        )
        return saved_count

    def exists(self, egid: int) -> bool:
        """Prüft ob ein Gebäude in der DB existiert."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM buildings_3d WHERE egid = ?", (egid,))
            return cursor.fetchone() is not None

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken zur Datenbank zurück."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM buildings_3d")
            total_buildings = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT tile_id) FROM buildings_3d")
            total_tiles = cursor.fetchone()[0]

            cursor.execute("""
                SELECT tile_id, COUNT(*) as count
                FROM buildings_3d
                GROUP BY tile_id
                ORDER BY count DESC
                LIMIT 5
            """)
            top_tiles = [dict(r) for r in cursor.fetchall()]

            return {
                "total_buildings": total_buildings,
                "total_tiles": total_tiles,
                "top_tiles": top_tiles,
                "db_path": str(BUILDING_3D_DB)
            }

    def get_neighbors(
        self,
        egid: int,
        radius_m: float = 50.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Findet Nachbargebäude zu einem EGID.

        Args:
            egid: Zentrales Gebäude
            radius_m: Suchradius
            limit: Max. Anzahl Nachbarn

        Returns:
            Liste von Nachbargebäuden mit Distanz
        """
        # Zuerst Zentroid des Gebäudes holen
        building = self.get_by_egid(egid)
        if not building or not building.get('center_e'):
            return []

        e, n = building['center_e'], building['center_n']

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *,
                       sqrt((center_e - ?) * (center_e - ?) +
                            (center_n - ?) * (center_n - ?)) as distance_m
                FROM buildings_3d
                WHERE egid != ?
                  AND center_e BETWEEN ? AND ?
                  AND center_n BETWEEN ? AND ?
                ORDER BY distance_m ASC
                LIMIT ?
            """, (
                e, e, n, n,
                egid,
                e - radius_m, e + radius_m,
                n - radius_m, n + radius_m,
                limit
            ))

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result.get('polygon'):
                    try:
                        result['polygon'] = json.loads(result['polygon'])
                    except json.JSONDecodeError:
                        result['polygon'] = None
                results.append(result)

            return results


# Singleton-Accessor
_service_instance = None

def get_building_3d_service() -> Building3DService:
    """Gibt die Singleton-Instanz des Building3DService zurück."""
    global _service_instance
    if _service_instance is None:
        _service_instance = Building3DService()
    return _service_instance


# CLI für Batch-Import
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Building 3D Service CLI")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--lookup", type=int, help="Lookup building by EGID")

    args = parser.parse_args()

    service = get_building_3d_service()

    if args.stats:
        stats = service.get_stats()
        print(f"Building 3D Database Statistics:")
        print(f"  Total buildings: {stats['total_buildings']}")
        print(f"  Total tiles: {stats['total_tiles']}")
        print(f"  Database: {stats['db_path']}")
        if stats['top_tiles']:
            print(f"  Top tiles:")
            for tile in stats['top_tiles']:
                print(f"    {tile['tile_id']}: {tile['count']} buildings")

    elif args.lookup:
        building = service.get_by_egid(args.lookup)
        if building:
            print(f"Found building EGID {args.lookup}:")
            print(f"  Traufhoehe: {building.get('traufhoehe_m')}m")
            print(f"  Firsthoehe: {building.get('firsthoehe_m')}m")
            print(f"  Area: {building.get('area_m2')}m2")
            print(f"  Tile: {building.get('tile_id')}")
            if building.get('polygon'):
                print(f"  Polygon: {len(building['polygon'])} points")
        else:
            print(f"Building EGID {args.lookup} not found")
