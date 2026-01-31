# backend/app/services/building_3d_service.py
"""
Building 3D Data Service
========================

Unabhängiger Cache für swissBUILDINGS3D Gebäudedaten.

WICHTIG: Diese Datenbank ist UNABHÄNGIG von anderen Caches!
- Enthält NUR Rohdaten aus swissBUILDINGS3D Tiles
- Wird vom tile_prefetch.py befüllt
- Ermöglicht O(1) Lookups statt GDB-Parsing

NEU 12.01.2026: DuckDB-Migration
- Feature-Flag USE_DUCKDB in config.py
- Dual-Mode: SQLite (default) oder DuckDB
- Parquet-Pipeline für schnelleren Bulk-Import

Schema:
    buildings_3d (
        egid INTEGER PRIMARY KEY,
        polygon JSON,           -- [[e,n], [e,n], ...]
        traufhoehe_m REAL,      -- DACH_MIN - GELAENDEPUNKT (Schätzung)
        firsthoehe_m REAL,      -- DACH_MAX - GELAENDEPUNKT (Schätzung)
        gebaeudehoehe_m REAL,   -- GESAMTHOEHE aus swissBUILDINGS3D
        area_m2 REAL,
        perimeter_m REAL,
        center_e REAL,          -- LV95 Zentroid
        center_n REAL,
        tile_id TEXT,           -- Quell-Tile für Debugging
        imported_at TIMESTAMP,
        source TEXT,            -- 'swissBUILDINGS3D_3.0'
        objektart TEXT,         -- Gebäudetyp aus swissBUILDINGS3D
        name_komplett TEXT,     -- Gebäudename (wenn vorhanden)
        gebaeude_nutzung TEXT,  -- Nutzungsart
        gebaeudeeinheit TEXT,   -- Verknüpfung zu anderen Layern
        roof_form TEXT,         -- Berechnete Dachform
        roof_form_confidence REAL, -- Konfidenz der Erkennung (0-1)
        roof_orientation TEXT,  -- First-Verlauf (N-S, O-W, etc.)
        has_3d_layers INTEGER   -- Flag für erweiterte 3D-Daten
    )

    HINWEIS 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
    Berechnung: DACH_MIN/DACH_MAX - GELAENDEPUNKT (Schätzung, ~1-2m ungenau bei Hanglagen).
    Für Hauptgebäude: Exakte Berechnung via Terrain-Sampling (swissALTI3D).
    Für Nachbarn: Schätzung aus swissBUILDINGS3D reicht für 3D-Visualisierung.

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
        gebaeudehoehe = building['gebaeudehoehe_m']
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Set
from datetime import datetime
from contextlib import contextmanager
from threading import local

# NEU 12.01.2026: Zentrale Konfiguration
from app.config import (
    USE_DUCKDB,
    BUILDING_3D_DB_PATH,
    BUILDING_3D_SQLITE_PATH,
    BUILDING_3D_DUCKDB_PATH,
    DATA_DIR,
    get_db_engine_name,
    get_building_3d_connection,  # FIX 13.01.2026 18:45: Zentrale Connection-Factory
)

# Conditional imports basierend auf Engine
import sqlite3
if USE_DUCKDB:
    import duckdb

logger = logging.getLogger(__name__)

# Optimierungs-Konstanten (BATCH_IMPORT.md Anhang A)
BATCH_SIZE = 5000  # Task 2: Erhöht von 1000 auf 5000
PRAGMA_CACHE_SIZE = -64000  # 64MB Cache (nur SQLite)
PRAGMA_MMAP_SIZE = 268435456  # 256MB Memory-Mapped I/O (nur SQLite)

# DEPRECATED: Verwende BUILDING_3D_DB_PATH aus config.py
# Bleibt für Rückwärtskompatibilität
BUILDING_3D_DB = BUILDING_3D_DB_PATH


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

    NEU 12.01.2026: DuckDB-Migration
    - Unterstützt SQLite (default) und DuckDB
    - Feature-Flag USE_DUCKDB steuert die Engine
    - DuckDB: Bessere Parallelität, schnellerer Bulk-Import

    OPTIMIERUNGEN (BATCH_IMPORT.md Anhang A):
    - Task 1: Aggressive PRAGMAs (WAL, synchronous, cache_size, mmap) - nur SQLite
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
        # NEU 12.01.2026: Engine-Info speichern
        self._use_duckdb = USE_DUCKDB
        self._init_database()
        self._initialized = True
        logger.info(f"[Building3DService] Initialisiert mit {get_db_engine_name()}: {BUILDING_3D_DB_PATH}")

    def _init_database(self):
        """
        Erstellt Datenbank-Schema falls nicht vorhanden.

        NEU 13.01.2026 19:10: Verwendet zentrales Schema aus building_3d_schema.py
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Zentrales Schema verwenden (eine Quelle der Wahrheit)
        from app.services.building_3d_schema import init_schema
        init_schema()

    # =============================================================================
    # SCHEMA-DEFINITIONEN ENTFERNT (13.01.2026 19:10)
    # =============================================================================
    # Die Schema-Definitionen wurden nach building_3d_schema.py verschoben.
    # EINE Quelle der Wahrheit für alle Tabellen-Definitionen.
    # Siehe: app/services/building_3d_schema.py
    # =============================================================================

    def _setup_sqlite_connection(self, conn: sqlite3.Connection):
        """
        Task 1: Aggressive PRAGMAs für optimale SQLite Performance.

        Konfiguriert SQLite für maximale Bulk-Import-Geschwindigkeit.
        NUR für SQLite - DuckDB braucht keine PRAGMAs.
        """
        # WAL-Mode: Bessere Parallelität (Reads während Write)
        conn.execute("PRAGMA journal_mode=WAL")

        # NORMAL statt FULL: Weniger fsync, ~30% schneller
        conn.execute("PRAGMA synchronous=NORMAL")

        # Grösserer Cache: 64MB statt default 2MB
        conn.execute(f"PRAGMA cache_size={PRAGMA_CACHE_SIZE}")

        # Temp-Tabellen im RAM
        conn.execute("PRAGMA temp_store=MEMORY")

        # Memory-Mapped I/O: 256MB
        conn.execute(f"PRAGMA mmap_size={PRAGMA_MMAP_SIZE}")

    # Alias für Rückwärtskompatibilität
    def _setup_connection(self, conn):
        """Deprecated: Use _setup_sqlite_connection instead."""
        if not self._use_duckdb:
            self._setup_sqlite_connection(conn)

    @contextmanager
    def _get_connection(self, pooled: bool = True, read_only: bool = False):
        """
        Thread-lokale Connection für bessere Performance.

        NEU 12.01.2026: Dual-Mode für SQLite und DuckDB

        Args:
            pooled: True = Thread-lokale wiederverwendete Connection
                   False = Neue Connection (für spezielle Fälle)
            read_only: Nur Lese-Zugriff (relevant für DuckDB)
        """
        if self._use_duckdb:
            # DuckDB Connection
            yield from self._get_duckdb_connection(pooled, read_only)
        else:
            # SQLite Connection (Original-Logik)
            yield from self._get_sqlite_connection(pooled)

    def _get_sqlite_connection(self, pooled: bool = True):
        """SQLite-spezifisches Connection-Handling."""
        if pooled:
            # Thread-lokale Connection wiederverwenden
            if not hasattr(self._local, 'conn') or self._local.conn is None:
                self._local.conn = sqlite3.connect(
                    str(BUILDING_3D_SQLITE_PATH),
                    check_same_thread=False
                )
                self._local.conn.row_factory = sqlite3.Row
                self._setup_sqlite_connection(self._local.conn)

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
            conn = sqlite3.connect(str(BUILDING_3D_SQLITE_PATH))
            conn.row_factory = sqlite3.Row
            self._setup_sqlite_connection(conn)
            try:
                yield conn
            finally:
                conn.close()

    def _get_duckdb_connection(self, pooled: bool = True, read_only: bool = False):
        """
        DuckDB-spezifisches Connection-Handling.

        DuckDB ist thread-safe und braucht kein spezielles Pooling.
        Aber für Konsistenz verwenden wir Thread-lokale Connections.
        """
        if pooled and not read_only:
            # Thread-lokale Connection wiederverwenden (für Writes)
            # FIX 13.01.2026 18:45: Zentrale Connection-Factory verwenden
            if not hasattr(self._local, 'duckdb_conn') or self._local.duckdb_conn is None:
                self._local.duckdb_conn = get_building_3d_connection()

            try:
                yield self._local.duckdb_conn
            except Exception:
                # Bei Fehler: Connection zurücksetzen
                if hasattr(self._local, 'duckdb_conn') and self._local.duckdb_conn:
                    try:
                        self._local.duckdb_conn.rollback()
                    except Exception:
                        pass
                raise
        else:
            # Neue Connection (read_only oder nicht gepoolt)
            # FIX 13.01.2026 18:45: Zentrale Connection-Factory verwenden
            conn = get_building_3d_connection()
            try:
                yield conn
            finally:
                conn.close()

    def _row_to_dict(self, row, columns: list = None) -> Dict[str, Any]:
        """
        Konvertiert eine Datenbankzeile zu einem Dict.

        NEU 12.01.2026: Funktioniert mit SQLite Row und DuckDB Tuple
        """
        if row is None:
            return None

        if self._use_duckdb:
            # DuckDB gibt Tuples zurück - wir brauchen die Spaltennamen
            if columns:
                return dict(zip(columns, row))
            else:
                # Fallback: Annahme der Standard-Spalten
                return dict(row) if hasattr(row, 'keys') else None
        else:
            # SQLite Row hat .keys()
            return dict(row)

    def _fetch_one_as_dict(self, conn, sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """
        Führt Query aus und gibt erste Zeile als Dict zurück.

        NEU 12.01.2026: Funktioniert mit SQLite und DuckDB
        """
        if self._use_duckdb:
            result = conn.execute(sql, params or [])
            row = result.fetchone()
            if not row:
                return None
            # DuckDB: Spaltennamen aus description holen
            columns = [desc[0] for desc in result.description]
            return dict(zip(columns, row))
        else:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def _fetch_all_as_dicts(self, conn, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Führt Query aus und gibt alle Zeilen als List[Dict] zurück.

        NEU 12.01.2026: Funktioniert mit SQLite und DuckDB
        """
        if self._use_duckdb:
            result = conn.execute(sql, params or [])
            rows = result.fetchall()
            if not rows:
                return []
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in rows]
        else:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return [dict(row) for row in cursor.fetchall()]

    def _parse_polygon(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parst das Polygon-Feld von GeoJSON-String zu Koordinaten-Liste.

        NEU 31.01.2026: ST_AsGeoJSON(geom) liefert GeoJSON-Format:
        {"type": "Polygon", "coordinates": [[[e1,n1], [e2,n2], ...]]}

        Wir extrahieren nur die Koordinaten-Liste: [[e1,n1], [e2,n2], ...]
        """
        if result and result.get('polygon'):
            polygon = result['polygon']
            if isinstance(polygon, str):
                try:
                    geojson = json.loads(polygon)
                    # GeoJSON Polygon: coordinates ist [[ring1], [ring2], ...]
                    # Wir nehmen nur den äusseren Ring (index 0)
                    if isinstance(geojson, dict) and 'coordinates' in geojson:
                        result['polygon'] = geojson['coordinates'][0]
                    else:
                        # Fallback: War vielleicht schon JSON-Array
                        result['polygon'] = geojson
                except json.JSONDecodeError:
                    result['polygon'] = None
            elif isinstance(polygon, dict) and 'coordinates' in polygon:
                # Bereits als Dict geparsed (DuckDB nativ)
                result['polygon'] = polygon['coordinates'][0]
        return result

    def get_by_egid(self, egid: int) -> Optional[Dict[str, Any]]:
        """
        Holt Gebäudedaten per EGID.

        NEU 31.01.2026: Verwendet ST_AsGeoJSON(geom) für Frontend-kompatibles Format.

        Args:
            egid: Eidgenössischer Gebäudeidentifikator

        Returns:
            Dict mit Polygon, Höhen, etc. oder None
        """
        with self._get_connection() as conn:
            # NEU 31.01.2026: ST_AsGeoJSON für Polygon-Export
            sql = """
                SELECT egid, ST_AsGeoJSON(geom) as polygon,
                       traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                       area_m2, perimeter_m, center_e, center_n,
                       tile_id, imported_at, source, objektart, name_komplett,
                       gebaeude_nutzung, gebaeudeeinheit, roof_form,
                       roof_form_confidence, roof_orientation, has_3d_layers,
                       terrain_z_min, terrain_z_max, terrain_slope_m, terrain_sampled_at
                FROM buildings_3d
                WHERE egid = ?
            """
            result = self._fetch_one_as_dict(conn, sql, (egid,))

            if not result:
                return None

            return self._parse_polygon(result)

    def get_egids_with_3d_layers(self, tile_id: str) -> Set[int]:
        """
        NEU 14.01.2026: Holt alle EGIDs mit has_3d_layers=1 für ein Tile.

        Wird vom Prefetch verwendet um Gebäude mit detaillierten 3D-Daten
        nicht zu überschreiben.

        Args:
            tile_id: Tile-Referenz (z.B. "1088-22")

        Returns:
            Set von EGIDs die has_3d_layers=1 haben
        """
        result = set()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT egid FROM buildings_3d WHERE tile_id = ? AND has_3d_layers = 1",
                    (tile_id,)
                )
                rows = cursor.fetchall()

                for row in rows:
                    if isinstance(row, tuple):
                        result.add(int(row[0]))
                    else:
                        result.add(int(row['egid']))

        except Exception as e:
            logger.warning(f"Fehler beim Laden der 3D-Layer EGIDs: {e}")

        return result

    def get_by_coordinates(
        self,
        e: float,
        n: float,
        tolerance_m: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Sucht Gebäude per Koordinaten mit Point-in-Polygon Check.

        NEU 31.01.2026: Verwendet DuckDB Spatial Extension (ST_Contains mit R-Tree).
        ~25x schneller als Python Ray-Casting (~2ms statt ~50ms).

        Args:
            e: LV95 Easting
            n: LV95 Northing
            tolerance_m: Suchradius in Metern (Fallback wenn kein Polygon-Match)

        Returns:
            Gebäude dessen Polygon den Punkt enthält, oder None
        """
        with self._get_connection() as conn:
            # PRIMÄR: Point-in-Polygon mit R-Tree Index
            # ST_Contains nutzt automatisch den Spatial Index
            sql_contains = """
                SELECT egid, ST_AsGeoJSON(geom) as polygon,
                       traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                       area_m2, perimeter_m, center_e, center_n,
                       tile_id, objektart, gebaeudeeinheit, has_3d_layers,
                       0.0 as distance_m
                FROM buildings_3d
                WHERE geom IS NOT NULL
                  AND ST_Contains(geom, ST_Point(?, ?))
                LIMIT 1
            """
            result = self._fetch_one_as_dict(conn, sql_contains, (e, n))

            if result:
                result = self._parse_polygon(result)
                logger.info(f"[get_by_coordinates] ST_Contains MATCH: ({e:.1f}, {n:.1f}) → EGID {result.get('egid')}")
                return result

            # FALLBACK: Nächstes Gebäude im Radius (wenn Punkt nicht in Polygon)
            # z.B. bei Koordinate auf Strasse neben Gebäude
            sql_fallback = """
                SELECT egid, ST_AsGeoJSON(geom) as polygon,
                       traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                       area_m2, perimeter_m, center_e, center_n,
                       tile_id, objektart, gebaeudeeinheit, has_3d_layers,
                       ST_Distance(geom, ST_Point(?, ?)) as distance_m
                FROM buildings_3d
                WHERE geom IS NOT NULL
                  AND ST_DWithin(geom, ST_Point(?, ?), ?)
                ORDER BY distance_m
                LIMIT 1
            """
            result = self._fetch_one_as_dict(conn, sql_fallback, (e, n, e, n, tolerance_m))

            if result:
                result = self._parse_polygon(result)
                logger.info(
                    f"[get_by_coordinates] ST_DWithin Fallback: ({e:.1f}, {n:.1f}) → "
                    f"EGID {result.get('egid')} (dist={result.get('distance_m', 0):.1f}m)"
                )
                return result

            logger.debug(f"[get_by_coordinates] Kein Gebäude im {tolerance_m}m Radius um ({e:.1f}, {n:.1f})")
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

        NEU 31.01.2026: Verwendet WKB-Geometrie statt JSON-Polygon.
        Das Gebäude-Dict kann enthalten:
        - geom_wkb: bytes - WKB-Binary (bevorzugt)
        - polygon: List - Wird ignoriert (Legacy, nur für Logging)

        Args:
            building: Dict mit egid, geom_wkb, höhen, etc.

        Returns:
            True bei Erfolg
        """
        egid = building.get('egid')
        if not egid:
            logger.warning("Cannot save building without EGID")
            return False

        # NEU 31.01.2026: WKB-Geometrie verwenden
        geom_wkb = building.get('geom_wkb')
        if geom_wkb is None:
            logger.warning(f"[SAVE] EGID {egid} hat kein geom_wkb - Geometrie wird NULL")

        # FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt (Schätzung für Nachbarn)
        params = (
            egid,
            geom_wkb,  # WKB binary statt JSON
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
        )

        with self._get_connection() as conn:
            insert_sql = self._get_prepared_insert()

            if self._use_duckdb:
                # DuckDB: INSERT OR REPLACE funktioniert seit v0.8
                conn.execute(insert_sql, params)
            else:
                cursor = conn.cursor()
                cursor.execute(insert_sql, params)
                conn.commit()

            return True

    def _get_prepared_insert(self):
        """
        Task 4: Prepared Statement für Bulk-Insert.

        NEU 31.01.2026: Verwendet ST_GeomFromWKB für GEOMETRY-Spalte.
        Der zweite Parameter ist WKB-Binary, nicht JSON!

        NEU 14.01.2026: UPSERT-Logik - nur Gebäude OHNE 3D-Layer werden aktualisiert!
        Gebäude mit has_3d_layers=1 behalten ihre detaillierten Daten.

        FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
        Schätzung aus GELAENDEPUNKT für Nachbar-Gebäude.
        """
        if self._prepared_insert is None:
            # UPSERT: INSERT neue Gebäude, UPDATE nur wenn has_3d_layers=0
            # NEU 31.01.2026: geom mit ST_GeomFromWKB statt polygon JSON (19 Spalten)
            # HINWEIS: Im ON CONFLICT Teil ist excluded.geom BEREITS GEOMETRY (keine erneute Konvertierung!)
            self._prepared_insert = """
                INSERT INTO buildings_3d
                (egid, geom, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                 area_m2, perimeter_m, center_e, center_n, tile_id, source,
                 objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                 roof_form, roof_form_confidence, roof_orientation, has_3d_layers)
                VALUES (?, ST_GeomFromWKB(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (egid) DO UPDATE SET
                    geom = COALESCE(excluded.geom, buildings_3d.geom),
                    traufhoehe_m = COALESCE(excluded.traufhoehe_m, buildings_3d.traufhoehe_m),
                    firsthoehe_m = COALESCE(excluded.firsthoehe_m, buildings_3d.firsthoehe_m),
                    gebaeudehoehe_m = COALESCE(excluded.gebaeudehoehe_m, buildings_3d.gebaeudehoehe_m),
                    area_m2 = COALESCE(excluded.area_m2, buildings_3d.area_m2),
                    perimeter_m = COALESCE(excluded.perimeter_m, buildings_3d.perimeter_m),
                    center_e = COALESCE(excluded.center_e, buildings_3d.center_e),
                    center_n = COALESCE(excluded.center_n, buildings_3d.center_n),
                    tile_id = COALESCE(excluded.tile_id, buildings_3d.tile_id),
                    source = COALESCE(excluded.source, buildings_3d.source),
                    objektart = COALESCE(excluded.objektart, buildings_3d.objektart),
                    name_komplett = COALESCE(excluded.name_komplett, buildings_3d.name_komplett),
                    gebaeude_nutzung = COALESCE(excluded.gebaeude_nutzung, buildings_3d.gebaeude_nutzung),
                    gebaeudeeinheit = COALESCE(excluded.gebaeudeeinheit, buildings_3d.gebaeudeeinheit),
                    roof_form = COALESCE(excluded.roof_form, buildings_3d.roof_form),
                    roof_form_confidence = COALESCE(excluded.roof_form_confidence, buildings_3d.roof_form_confidence),
                    roof_orientation = COALESCE(excluded.roof_orientation, buildings_3d.roof_orientation)
                WHERE buildings_3d.has_3d_layers = 0 OR buildings_3d.has_3d_layers IS NULL
            """
        return self._prepared_insert

    def drop_indexes(self):
        """
        Task 3 + C.8: Indexes vor Bulk-Import droppen.

        Beschleunigt den Import erheblich.
        NEU 12.01.2026: Funktioniert mit SQLite und DuckDB
        FIX 14.01.2026: Alle 7 Indexes droppen (vorher nur 2!)
        """
        # All index names from building_3d_schema.py INDEXES
        all_indexes = [
            "idx_buildings_3d_coords",
            "idx_buildings_3d_tile",
            "idx_buildings_3d_objektart",
            "idx_buildings_3d_gebaeudeeinheit",
            "idx_roofs_egid",
            "idx_walls_egid",
            "idx_floors_egid",
        ]

        with self._get_connection() as conn:
            dropped = 0
            if self._use_duckdb:
                for idx_name in all_indexes:
                    try:
                        conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
                        dropped += 1
                    except Exception as e:
                        logger.debug(f"[OPTIMIZE] Index {idx_name} skip: {e}")
            else:
                cursor = conn.cursor()
                for idx_name in all_indexes:
                    try:
                        cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
                        dropped += 1
                    except Exception as e:
                        logger.debug(f"[OPTIMIZE] Index {idx_name} skip: {e}")
                conn.commit()
            logger.info(f"[OPTIMIZE] {dropped}/{len(all_indexes)} indexes dropped ({get_db_engine_name()})")

    def create_indexes(self):
        """
        Task 3 + C.8: Indexes nach Bulk-Import erstellen.

        NEU 12.01.2026: Funktioniert mit SQLite und DuckDB
        FIX 14.01.2026: Alle 7 Indexes erstellen (vorher nur 2!)
        """
        # All index definitions from building_3d_schema.py INDEXES
        all_index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_buildings_3d_coords ON buildings_3d(center_e, center_n)",
            "CREATE INDEX IF NOT EXISTS idx_buildings_3d_tile ON buildings_3d(tile_id)",
            "CREATE INDEX IF NOT EXISTS idx_buildings_3d_objektart ON buildings_3d(objektart)",
            "CREATE INDEX IF NOT EXISTS idx_buildings_3d_gebaeudeeinheit ON buildings_3d(gebaeudeeinheit)",
            "CREATE INDEX IF NOT EXISTS idx_roofs_egid ON building_roofs(egid)",
            "CREATE INDEX IF NOT EXISTS idx_walls_egid ON building_walls(egid)",
            "CREATE INDEX IF NOT EXISTS idx_floors_egid ON building_floors(egid)",
        ]

        start = datetime.now()
        created = 0

        with self._get_connection() as conn:
            if self._use_duckdb:
                for idx_sql in all_index_sql:
                    try:
                        conn.execute(idx_sql)
                        created += 1
                    except Exception as e:
                        logger.debug(f"[OPTIMIZE] Index skip: {e}")
            else:
                cursor = conn.cursor()
                for idx_sql in all_index_sql:
                    try:
                        cursor.execute(idx_sql)
                        created += 1
                    except Exception as e:
                        logger.debug(f"[OPTIMIZE] Index skip: {e}")
                conn.commit()

        duration = (datetime.now() - start).total_seconds()
        logger.info(f"[OPTIMIZE] {created}/{len(all_index_sql)} indexes created in {duration:.2f}s ({get_db_engine_name()})")

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

        # Daten vorbereiten (WKB-Geometrie, ungültige filtern)
        # NEU 31.01.2026: Verwendet geom_wkb statt polygon JSON
        prepared_data = []
        for building in buildings:
            egid = building.get('egid')
            if not egid:
                continue

            # NEU 31.01.2026: WKB-Geometrie verwenden
            geom_wkb = building.get('geom_wkb')
            if geom_wkb is None:
                logger.debug(f"[BULK_SAVE] EGID {egid} hat kein geom_wkb")

            # FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt
            prepared_data.append((
                egid,
                geom_wkb,  # WKB binary statt JSON
                building.get('traufhoehe_m'),
                building.get('firsthoehe_m'),
                building.get('gebaeudehoehe_m'),
                building.get('area_m2'),
                building.get('perimeter_m'),
                building.get('center_e') or building.get('coord_e'),
                building.get('center_n') or building.get('coord_n'),
                tile_id or building.get('tile_id'),
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

        if not prepared_data:
            return 0

        saved_count = 0

        # Task 4: Prepared Statement wiederverwenden
        insert_sql = self._get_prepared_insert()

        with self._get_connection() as conn:
            if self._use_duckdb:
                # DuckDB: executemany nicht verfügbar, verwende Batch-Insert
                saved_count = self._bulk_save_duckdb(conn, prepared_data, insert_sql, tile_id)
            else:
                # SQLite: Original-Logik mit cursor.executemany
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

        duration = (datetime.now() - start_time).total_seconds()
        duration_ms = duration * 1000
        ms_per_building = (duration_ms / saved_count) if saved_count > 0 else 0
        logger.info(
            f"[BULK] {saved_count} Gebäude gespeichert | "
            f"tile: {tile_id} | {duration:.2f}s | {ms_per_building:.2f}ms/Gebäude | "
            f"Engine: {get_db_engine_name()}"
        )

        # NEU 14.01.2026: Import-Metriken für Baseline-Messung aktualisieren
        from app.services.tile_prefetch import update_import_metrics
        update_import_metrics(db_write_buildings_ms=duration_ms)

        return saved_count

    def _bulk_save_duckdb(self, conn, prepared_data: list, insert_sql: str, tile_id: str = None) -> int:
        """
        DuckDB-spezifischer Bulk-Insert.

        NEU 13.01.2026: Vereinfacht - INSERT OR REPLACE handled Duplikate automatisch.
        DuckDB hat kein executemany, daher einzelne Inserts in einer Transaction.
        """
        saved_count = 0
        start_time = datetime.now()

        try:
            # Transaction starten für bessere Performance
            conn.execute("BEGIN TRANSACTION")

            # INSERT OR REPLACE handled Duplikate automatisch
            for row in prepared_data:
                try:
                    conn.execute(insert_sql, row)
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save EGID {row[0]}: {e}")

            conn.execute("COMMIT")

            # Import loggen
            duration = (datetime.now() - start_time).total_seconds()
            if tile_id:
                conn.execute("""
                    INSERT INTO import_log (tile_id, buildings_count, duration_seconds, source)
                    VALUES (?, ?, ?, ?)
                """, [tile_id, saved_count, duration, 'tile_prefetch_duckdb'])

        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error(f"DuckDB bulk_save failed: {e}")
            raise

        return saved_count

    def exists(self, egid: int) -> bool:
        """
        Prüft ob ein Gebäude in der DB existiert.

        NEU 12.01.2026: Dual-Mode für SQLite und DuckDB
        """
        with self._get_connection() as conn:
            if self._use_duckdb:
                result = conn.execute("SELECT 1 FROM buildings_3d WHERE egid = ?", [egid]).fetchone()
                return result is not None
            else:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM buildings_3d WHERE egid = ?", (egid,))
                return cursor.fetchone() is not None

    def get_stats(self) -> Dict[str, Any]:
        """
        Gibt Statistiken zur Datenbank zurück.

        NEU 12.01.2026: Dual-Mode für SQLite und DuckDB
        NEU 14.01.2026: Roofs und Walls Statistiken hinzugefügt
        """
        with self._get_connection() as conn:
            if self._use_duckdb:
                total_buildings = conn.execute("SELECT COUNT(*) FROM buildings_3d").fetchone()[0]
                total_tiles = conn.execute("SELECT COUNT(DISTINCT tile_id) FROM buildings_3d").fetchone()[0]

                # NEU 14.01.2026: Roofs und Walls zählen
                try:
                    total_roofs = conn.execute("SELECT COUNT(*) FROM building_roofs").fetchone()[0]
                except:
                    total_roofs = 0
                try:
                    total_walls = conn.execute("SELECT COUNT(*) FROM building_walls").fetchone()[0]
                except:
                    total_walls = 0

                result = conn.execute("""
                    SELECT tile_id, COUNT(*) as count
                    FROM buildings_3d
                    GROUP BY tile_id
                    ORDER BY count DESC
                    LIMIT 5
                """)
                columns = [desc[0] for desc in result.description]
                top_tiles = [dict(zip(columns, row)) for row in result.fetchall()]
            else:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM buildings_3d")
                total_buildings = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT tile_id) FROM buildings_3d")
                total_tiles = cursor.fetchone()[0]

                # NEU 14.01.2026: Roofs und Walls zählen
                try:
                    cursor.execute("SELECT COUNT(*) FROM building_roofs")
                    total_roofs = cursor.fetchone()[0]
                except:
                    total_roofs = 0
                try:
                    cursor.execute("SELECT COUNT(*) FROM building_walls")
                    total_walls = cursor.fetchone()[0]
                except:
                    total_walls = 0

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
                "total_roofs": total_roofs,
                "total_walls": total_walls,
                "total_tiles": total_tiles,
                "top_tiles": top_tiles,
                "db_path": str(BUILDING_3D_DB_PATH),
                "engine": get_db_engine_name()
            }

    def get_neighbors(
        self,
        egid: int,
        radius_m: float = 50.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Findet Nachbargebäude zu einem EGID.

        NEU 31.01.2026: Verwendet ST_DWithin mit R-Tree Index (~5ms statt ~100ms).

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

        # NEU 31.01.2026: ST_DWithin für Spatial-basierte Radius-Suche
        sql = """
            SELECT egid, ST_AsGeoJSON(geom) as polygon,
                   center_e, center_n, traufhoehe_m, firsthoehe_m,
                   gebaeudehoehe_m, tile_id, has_3d_layers,
                   ST_Distance(geom, ST_Point(?, ?)) as distance_m
            FROM buildings_3d
            WHERE egid != ?
              AND geom IS NOT NULL
              AND ST_DWithin(geom, ST_Point(?, ?), ?)
            ORDER BY distance_m ASC
            LIMIT ?
        """
        params = (e, n, egid, e, n, radius_m, limit)

        with self._get_connection() as conn:
            rows = self._fetch_all_as_dicts(conn, sql, params)

            results = []
            for result in rows:
                result = self._parse_polygon(result)
                results.append(result)

            return results

    def get_neighbors_by_coordinates(
        self,
        center_e: float,
        center_n: float,
        radius_m: float = 100.0,
        exclude_egids: Optional[List[int]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        NEU 29.01.2026: Findet Nachbargebäude per Koordinaten (ohne EGID).
        NEU 31.01.2026: Verwendet ST_DWithin für Spatial-basierte Suche.

        Wird verwendet wenn GDB gelöscht wurde (status='cleaned') aber
        Daten bereits in DB sind.

        Args:
            center_e: LV95 E-Koordinate des Zentrums
            center_n: LV95 N-Koordinate des Zentrums
            radius_m: Suchradius in Metern
            exclude_egids: EGIDs die übersprungen werden sollen
            limit: Max. Anzahl Nachbarn

        Returns:
            Liste von Nachbargebäuden mit Distanz
        """
        exclude_egids = exclude_egids or []

        # NEU 31.01.2026: ST_DWithin für echte Distanz-Berechnung
        sql = """
            SELECT
                egid, ST_AsGeoJSON(geom) as polygon, center_e, center_n,
                traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                has_3d_layers, tile_id,
                ST_Distance(geom, ST_Point(?, ?)) as distance_m
            FROM buildings_3d
            WHERE geom IS NOT NULL
              AND ST_DWithin(geom, ST_Point(?, ?), ?)
              AND has_3d_layers = 1
        """

        params = [center_e, center_n, center_e, center_n, radius_m]

        # Exclude-Filter
        if exclude_egids:
            placeholders = ','.join(['?' for _ in exclude_egids])
            sql += f" AND egid NOT IN ({placeholders})"
            params.extend(exclude_egids)

        sql += f" ORDER BY distance_m LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = self._fetch_all_as_dicts(conn, sql, params)

            results = []
            for result in rows:
                result = self._parse_polygon(result)
                results.append(result)

            logger.info(f"[DB-NEIGHBORS] {len(results)} Nachbarn im {radius_m}m Radius gefunden")
            return results

    def check_egids_complete(self, egids: List[int]) -> Dict[str, List[int]]:
        """
        NEU 22.01.2026: Prüft welche EGIDs vollständig in der DB sind.

        Vollständig bedeutet:
        - has_3d_layers = 1
        - geom IS NOT NULL (NEU 31.01.2026: GEOMETRY statt polygon JSON)
        - traufhoehe_m IS NOT NULL OR firsthoehe_m IS NOT NULL

        Args:
            egids: Liste der zu prüfenden EGIDs

        Returns:
            Dict mit:
            - 'complete': Liste der vollständigen EGIDs
            - 'missing': Liste der fehlenden/unvollständigen EGIDs
        """
        if not egids:
            return {'complete': [], 'missing': []}

        complete = []
        missing = []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # DuckDB und SQLite: IN-Clause mit Parametern
                # NEU 31.01.2026: geom statt polygon
                placeholders = ','.join(['?' for _ in egids])
                cursor.execute(f"""
                    SELECT egid FROM buildings_3d
                    WHERE egid IN ({placeholders})
                      AND has_3d_layers = 1
                      AND geom IS NOT NULL
                      AND (traufhoehe_m IS NOT NULL OR firsthoehe_m IS NOT NULL)
                """, egids)

                rows = cursor.fetchall()

                # Gefundene EGIDs sammeln
                found_set = set()
                for row in rows:
                    if isinstance(row, tuple):
                        found_set.add(int(row[0]))
                    else:
                        found_set.add(int(row['egid']))

                # Aufteilen in complete/missing
                for egid in egids:
                    if egid in found_set:
                        complete.append(egid)
                    else:
                        missing.append(egid)

                logger.info(
                    f"[CHECK_COMPLETE] {len(complete)}/{len(egids)} EGIDs vollständig, "
                    f"{len(missing)} fehlen: {missing}"
                )

        except Exception as e:
            logger.error(f"[CHECK_COMPLETE] Fehler: {e}")
            # Bei Fehler: Alle als fehlend markieren (sicher)
            missing = list(egids)

        return {'complete': complete, 'missing': missing}

    def get_buildings_by_egids(self, egids: List[int]) -> List[Dict[str, Any]]:
        """
        NEU 22.01.2026: Lädt mehrere Gebäude per EGID-Liste aus der DB.

        WICHTIG: Diese Funktion macht KEINEN GDB-Zugriff und triggert
        KEINEN Prefetch. Sie liest NUR aus der DB.

        NEU 31.01.2026: Verwendet ST_AsGeoJSON(geom) für Frontend-kompatibles Format.

        Inkludiert auch Roof- und Wall-Daten falls vorhanden.

        Args:
            egids: Liste der zu ladenden EGIDs

        Returns:
            Liste von Gebäude-Dicts (mit polygon, höhen, roof_data, wall_data)
        """
        if not egids:
            return []

        results = []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Gebäude-Grunddaten laden
                # NEU 31.01.2026: ST_AsGeoJSON(geom) statt SELECT *
                placeholders = ','.join(['?' for _ in egids])
                cursor.execute(f"""
                    SELECT egid, ST_AsGeoJSON(geom) as polygon,
                           traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                           area_m2, perimeter_m, center_e, center_n,
                           tile_id, imported_at, source, objektart, name_komplett,
                           gebaeude_nutzung, gebaeudeeinheit, roof_form,
                           roof_form_confidence, roof_orientation, has_3d_layers,
                           terrain_z_min, terrain_z_max, terrain_slope_m, terrain_sampled_at
                    FROM buildings_3d
                    WHERE egid IN ({placeholders})
                """, egids)

                rows = cursor.fetchall()

                # Spaltennamen für Dict-Konvertierung
                if rows:
                    if isinstance(rows[0], tuple):
                        # DuckDB: Spaltennamen aus cursor.description
                        columns = [desc[0] for desc in cursor.description]
                        buildings_raw = [dict(zip(columns, row)) for row in rows]
                    else:
                        # SQLite Row
                        buildings_raw = [dict(row) for row in rows]
                else:
                    buildings_raw = []

                # Roof-Daten laden
                cursor.execute(f"""
                    SELECT egid, dach_min, dach_max, gebaeudeeinheit
                    FROM building_roofs
                    WHERE egid IN ({placeholders})
                """, egids)
                roof_rows = cursor.fetchall()

                roof_by_egid = {}
                for row in roof_rows:
                    if isinstance(row, tuple):
                        egid = int(row[0])
                        roof_by_egid[egid] = {
                            'dach_min': row[1],
                            'dach_max': row[2],
                            'gebaeudeeinheit': row[3]
                        }
                    else:
                        egid = int(row['egid'])
                        roof_by_egid[egid] = {
                            'dach_min': row['dach_min'],
                            'dach_max': row['dach_max'],
                            'gebaeudeeinheit': row['gebaeudeeinheit']
                        }

                # Wall-Daten laden
                cursor.execute(f"""
                    SELECT egid, z_min, z_max, gebaeudeeinheit
                    FROM building_walls
                    WHERE egid IN ({placeholders})
                """, egids)
                wall_rows = cursor.fetchall()

                wall_by_egid = {}
                for row in wall_rows:
                    if isinstance(row, tuple):
                        egid = int(row[0])
                        wall_by_egid[egid] = {
                            'z_min': row[1],
                            'z_max': row[2],
                            'gebaeudeeinheit': row[3]
                        }
                    else:
                        egid = int(row['egid'])
                        wall_by_egid[egid] = {
                            'z_min': row['z_min'],
                            'z_max': row['z_max'],
                            'gebaeudeeinheit': row['gebaeudeeinheit']
                        }

                # Ergebnisse zusammenbauen
                for building in buildings_raw:
                    building = self._parse_polygon(building)
                    egid = building.get('egid')

                    # Roof-Daten hinzufügen
                    if egid in roof_by_egid:
                        building['roof_data'] = roof_by_egid[egid]

                    # Wall-Daten hinzufügen
                    if egid in wall_by_egid:
                        building['wall_data'] = wall_by_egid[egid]

                    results.append(building)

                logger.debug(f"[GET_BY_EGIDS] {len(results)} Gebäude aus DB geladen")

        except Exception as e:
            logger.error(f"[GET_BY_EGIDS] Fehler: {e}")

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
            print(f"  Gebaeudehoehe: {building.get('gebaeudehoehe_m')}m")
            print(f"  Area: {building.get('area_m2')}m2")
            print(f"  Tile: {building.get('tile_id')}")
            print(f"  has_3d_layers: {building.get('has_3d_layers')}")
            if building.get('polygon'):
                print(f"  Polygon: {len(building['polygon'])} points")
            # Hinweis: traufhoehe/firsthoehe kommen aus building_roofs
            print(f"  Hinweis: Trauf-/Firsthöhe aus building_roofs.dach_min/dach_max")
        else:
            print(f"Building EGID {args.lookup} not found")
