"""
Roof 3D Data Service
====================

Service für Dach-Daten aus swissBUILDINGS3D 3.0 Roof_solid Layer.

Zwei Modi:
1. **Pre-Import (Batch):** Nur berechnete Werte (Dachform, Neigung, Z-Levels)
2. **On-Demand:** Vollständige 3D-Geometrie für komplexe Gebäude

Schema:
    building_roofs (
        id INTEGER PRIMARY KEY,
        gebaeudeeinheit TEXT NOT NULL,  -- Verknüpfung zu buildings_3d
        egid TEXT,
        dach_min REAL,                  -- Traufhöhe (m ü.M.)
        dach_max REAL,                  -- Firsthöhe (m ü.M.)
        roof_form TEXT,                 -- 'flachdach', 'satteldach', etc.
        roof_angle_deg REAL,            -- Berechnete Neigung
        roof_orientation TEXT,          -- First-Verlauf
        z_levels TEXT,                  -- JSON: [546.9, 551.0, ...]
        geometry_wkb BLOB,              -- 3D-Geometrie (NULL bei Pre-Import)
        has_full_geometry INTEGER,
        calculated_at TIMESTAMP,
        calculation_method TEXT
    )

Version: 1.0 (11.01.2026)
NEU 13.01.2026 17:00: DuckDB-kompatibel via get_building_3d_connection()
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

# NEU 13.01.2026 17:00: DuckDB-kompatible Connection
from app.config import get_building_3d_connection, BUILDING_3D_DB_PATH, USE_DUCKDB

logger = logging.getLogger(__name__)

# Pfad zur Datenbank (NEU 13.01.2026: aus config)
DATA_DIR = Path(__file__).parent.parent / "data"
BUILDING_3D_DB = BUILDING_3D_DB_PATH


class Roof3DService:
    """
    Service für Dach-Daten aus Roof_solid Layer.

    Speichert:
    - Berechnete Dachform (Pre-Import)
    - Z-Level-Verteilung für Analyse
    - Optionale 3D-Geometrie (on-demand)
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
        self._initialized = True

    @contextmanager
    def _get_connection(self, read_only: bool = False):
        """
        Erstellt eine Datenbankverbindung (DuckDB oder SQLite).

        NEU 13.01.2026 17:00: Verwendet get_building_3d_connection() aus config.
        """
        conn = get_building_3d_connection(read_only=read_only)
        # PRAGMA nur für SQLite, nicht für DuckDB
        if not USE_DUCKDB:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
        finally:
            conn.close()

    def save(self, roof: Dict[str, Any]) -> bool:
        """
        Speichert Dach-Daten.

        Args:
            roof: Dict mit gebaeudeeinheit, dach_min, dach_max, roof_form, etc.

        Returns:
            True bei Erfolg
        """
        gebaeudeeinheit = roof.get('gebaeudeeinheit')
        if not gebaeudeeinheit:
            logger.warning("Cannot save roof without gebaeudeeinheit")
            return False

        # Z-Levels zu JSON serialisieren
        z_levels = roof.get('z_levels')
        if z_levels and not isinstance(z_levels, str):
            z_levels = json.dumps(z_levels)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO building_roofs
                (gebaeudeeinheit, egid, dach_min, dach_max,
                 roof_form, roof_angle_deg, roof_orientation, z_levels,
                 geometry_wkb, has_full_geometry, calculation_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gebaeudeeinheit,
                roof.get('egid'),
                roof.get('dach_min'),
                roof.get('dach_max'),
                roof.get('roof_form'),
                roof.get('roof_angle_deg'),
                roof.get('roof_orientation'),
                z_levels,
                roof.get('geometry_wkb'),
                roof.get('has_full_geometry', 0),
                roof.get('calculation_method', 'z_level_analysis')
            ))

            conn.commit()
            return True

    def bulk_save(self, roofs: List[Dict[str, Any]]) -> int:
        """
        Speichert mehrere Dächer in einer Transaktion.

        Args:
            roofs: Liste von Dach-Dicts

        Returns:
            Anzahl gespeicherter Einträge
        """
        if not roofs:
            return 0

        # Daten vorbereiten
        prepared_data = []
        for roof in roofs:
            gebaeudeeinheit = roof.get('gebaeudeeinheit')
            if not gebaeudeeinheit:
                continue

            z_levels = roof.get('z_levels')
            if z_levels and not isinstance(z_levels, str):
                z_levels = json.dumps(z_levels)

            prepared_data.append((
                gebaeudeeinheit,
                roof.get('egid'),
                roof.get('dach_min'),
                roof.get('dach_max'),
                roof.get('roof_form'),
                roof.get('roof_angle_deg'),
                roof.get('roof_orientation'),
                z_levels,
                roof.get('geometry_wkb'),
                roof.get('has_full_geometry', 0),
                roof.get('calculation_method', 'z_level_analysis')
            ))

        if not prepared_data:
            return 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.executemany("""
                INSERT OR REPLACE INTO building_roofs
                (gebaeudeeinheit, egid, dach_min, dach_max,
                 roof_form, roof_angle_deg, roof_orientation, z_levels,
                 geometry_wkb, has_full_geometry, calculation_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, prepared_data)

            conn.commit()

        logger.info(f"[ROOF] {len(prepared_data)} Dach-Einträge gespeichert")
        return len(prepared_data)

    def get_by_gebaeudeeinheit(self, gebaeudeeinheit: str) -> Optional[Dict[str, Any]]:
        """Holt Dach-Daten per Gebäudeeinheit."""
        with self._get_connection(read_only=True) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gebaeudeeinheit, egid, dach_min, dach_max,
                       roof_form, roof_angle_deg, roof_orientation, z_levels,
                       geometry_wkb, has_full_geometry, calculation_method
                FROM building_roofs WHERE gebaeudeeinheit = ?
            """, (gebaeudeeinheit,))

            row = cursor.fetchone()
            if not row:
                return None

            # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
            if isinstance(row, tuple):
                result = {
                    'gebaeudeeinheit': row[0], 'egid': row[1],
                    'dach_min': row[2], 'dach_max': row[3],
                    'roof_form': row[4], 'roof_angle_deg': row[5],
                    'roof_orientation': row[6], 'z_levels': row[7],
                    'geometry_wkb': row[8], 'has_full_geometry': row[9],
                    'calculation_method': row[10]
                }
            else:
                result = dict(row)

            # Z-Levels parsen
            if result.get('z_levels'):
                try:
                    z_levels_data = result['z_levels']
                    result['z_levels'] = json.loads(z_levels_data) if isinstance(z_levels_data, str) else z_levels_data
                except json.JSONDecodeError:
                    result['z_levels'] = None

            return result

    def get_by_egid(self, egid: str) -> Optional[Dict[str, Any]]:
        """Holt Dach-Daten per EGID."""
        with self._get_connection(read_only=True) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gebaeudeeinheit, egid, dach_min, dach_max,
                       roof_form, roof_angle_deg, roof_orientation, z_levels,
                       geometry_wkb, has_full_geometry, calculation_method
                FROM building_roofs WHERE egid = ?
            """, (egid,))

            row = cursor.fetchone()
            if not row:
                return None

            # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
            if isinstance(row, tuple):
                result = {
                    'gebaeudeeinheit': row[0], 'egid': row[1],
                    'dach_min': row[2], 'dach_max': row[3],
                    'roof_form': row[4], 'roof_angle_deg': row[5],
                    'roof_orientation': row[6], 'z_levels': row[7],
                    'geometry_wkb': row[8], 'has_full_geometry': row[9],
                    'calculation_method': row[10]
                }
            else:
                result = dict(row)

            # Z-Levels parsen
            if result.get('z_levels'):
                try:
                    z_levels_data = result['z_levels']
                    result['z_levels'] = json.loads(z_levels_data) if isinstance(z_levels_data, str) else z_levels_data
                except json.JSONDecodeError:
                    result['z_levels'] = None

            return result

    def update_with_geometry(self, gebaeudeeinheit: str, geometry_wkb: bytes) -> bool:
        """
        Aktualisiert einen Eintrag mit vollständiger 3D-Geometrie.

        Wird aufgerufen beim On-Demand Fetch für komplexe Gebäude.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE building_roofs
                SET geometry_wkb = ?,
                    has_full_geometry = 1,
                    calculated_at = CURRENT_TIMESTAMP
                WHERE gebaeudeeinheit = ?
            """, (geometry_wkb, gebaeudeeinheit))

            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        with self._get_connection(read_only=True) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM building_roofs")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM building_roofs WHERE has_full_geometry = 1")
            with_geometry = cursor.fetchone()[0]

            cursor.execute("""
                SELECT roof_form, COUNT(*) as count
                FROM building_roofs
                WHERE roof_form IS NOT NULL
                GROUP BY roof_form
                ORDER BY count DESC
            """)
            # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
            forms = {}
            for row in cursor.fetchall():
                if isinstance(row, tuple):
                    forms[row[0]] = row[1]
                else:
                    forms[row['roof_form']] = row['count']

            return {
                "total_roofs": total,
                "with_full_geometry": with_geometry,
                "roof_forms": forms
            }

    def fetch_geometry_on_demand(self, egid: str) -> Optional[bytes]:
        """
        Lädt 3D-Geometrie on-demand aus der GDB für komplexe Gebäude.

        NEU 12.01.2026: Geometrie wird NICHT beim Prefetch gespeichert.
        Diese Funktion holt sie bei Bedarf aus der gecachten GDB-Datei.

        Args:
            egid: EGID des Gebäudes

        Returns:
            WKB-Geometrie als bytes oder None
        """
        import time
        start = time.time()

        # 1. Tile-ID aus building_3d holen
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tile_id, gebaeudeeinheit FROM buildings_3d WHERE egid = ?
            """, (egid,))
            row = cursor.fetchone()

            if not row:
                logger.warning(f"Gebäude {egid} nicht in building_3d.db gefunden")
                return None

            # NEU 13.01.2026 17:30: DuckDB gibt Tuple zurück, SQLite Row
            if isinstance(row, tuple):
                tile_id = row[0]
                gebaeudeeinheit = row[1]
            else:
                tile_id = row['tile_id']
                gebaeudeeinheit = row['gebaeudeeinheit']

        if not tile_id:
            logger.warning(f"Keine tile_id für EGID {egid}")
            return None

        # 2. GDB-Pfad aus tile_cache holen
        from app.services.tile_cache import get_gdb_path_for_tile
        gdb_path = get_gdb_path_for_tile(tile_id)

        if not gdb_path or not gdb_path.exists():
            logger.warning(f"GDB für Tile {tile_id} nicht gefunden")
            return None

        # 3. Geometrie aus GDB extrahieren
        try:
            import fiona
            from shapely.geometry import shape

            layers = fiona.listlayers(gdb_path)
            target_layer = None
            for layer in layers:
                if 'roof' in layer.lower() and 'solid' in layer.lower():
                    target_layer = layer
                    break

            if not target_layer:
                logger.warning(f"Kein Roof_solid Layer in {gdb_path}")
                return None

            # FIX 12.01.2026: EGID zu int konvertieren für Vergleich
            # GDB speichert EGID als int, Parameter kommt als str
            try:
                egid_int = int(egid) if egid else None
            except ValueError:
                egid_int = None

            with fiona.open(gdb_path, layer=target_layer) as src:
                for feature in src:
                    props = feature['properties']

                    # Suche nach gebaeudeeinheit oder EGID
                    if gebaeudeeinheit and props.get('GEBAEUDEEINHEIT') == gebaeudeeinheit:
                        pass  # Found!
                    elif egid_int and props.get('EGID') == egid_int:
                        pass  # Found by EGID (int comparison)!
                    else:
                        continue

                    # Gefunden - Geometrie extrahieren
                    if feature['geometry'] is not None:
                        geom = shape(feature['geometry'])
                        geometry_wkb = geom.wkb

                        # In DB speichern für nächstes Mal
                        if gebaeudeeinheit:
                            self.update_with_geometry(gebaeudeeinheit, geometry_wkb)

                        elapsed_ms = (time.time() - start) * 1000
                        logger.info(
                            f"[GEOMETRY] On-demand für EGID {egid} geladen | "
                            f"{len(geometry_wkb)} bytes | {elapsed_ms:.0f}ms"
                        )
                        return geometry_wkb

            logger.warning(f"Geometrie für EGID {egid} nicht in GDB gefunden")
            return None

        except Exception as e:
            logger.error(f"Fehler beim Laden der Geometrie für {egid}: {e}")
            return None

    def fetch_all_layers_on_demand(self, egid: str) -> dict:
        """
        NEU 12.01.2026: Lädt ALLE 3D-Layer (Roof_solid, Roof, Wall) für komplexe Gebäude.

        Args:
            egid: EGID des Gebäudes

        Returns:
            Dict mit geladenen Geometrien:
            {
                'roof_solid': bytes | None,
                'roof': bytes | None,
                'wall': bytes | None,
                'loaded_layers': ['Roof_solid', 'Wall', ...]
            }
        """
        import time
        start = time.time()
        result = {
            'roof_solid': None,
            'roof': None,
            'wall': None,
            'loaded_layers': []
        }

        # 1. Tile-ID und gebaeudeeinheit aus building_3d holen
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tile_id, gebaeudeeinheit FROM buildings_3d WHERE egid = ?
            """, (egid,))
            row = cursor.fetchone()

            if not row:
                logger.warning(f"[ALL_LAYERS] Gebäude {egid} nicht in building_3d.db")
                return result

            # NEU 13.01.2026 17:30: DuckDB gibt Tuple zurück, SQLite Row
            if isinstance(row, tuple):
                tile_id = row[0]
                gebaeudeeinheit = row[1]
            else:
                tile_id = row['tile_id']
                gebaeudeeinheit = row['gebaeudeeinheit']

        if not tile_id:
            logger.warning(f"[ALL_LAYERS] Keine tile_id für EGID {egid}")
            return result

        # 2. GDB-Pfad holen
        from app.services.tile_cache import get_gdb_path_for_tile
        gdb_path = get_gdb_path_for_tile(tile_id)

        if not gdb_path or not gdb_path.exists():
            logger.warning(f"[ALL_LAYERS] GDB für Tile {tile_id} nicht gefunden")
            return result

        # 3. Alle Layer laden
        try:
            import fiona
            from shapely.geometry import shape

            # EGID zu int für Vergleich
            try:
                egid_int = int(egid) if egid else None
            except ValueError:
                egid_int = None

            layers = fiona.listlayers(gdb_path)

            # Layer-Mapping: GDB-Layer → Result-Key
            layer_mapping = {
                'Roof_solid': 'roof_solid',
                'Roof': 'roof',
                'Wall': 'wall'
            }

            for gdb_layer, result_key in layer_mapping.items():
                if gdb_layer not in layers:
                    continue

                with fiona.open(gdb_path, layer=gdb_layer) as src:
                    for feature in src:
                        props = feature['properties']

                        # Suche nach gebaeudeeinheit oder EGID
                        match = False
                        if gebaeudeeinheit and props.get('GEBAEUDEEINHEIT') == gebaeudeeinheit:
                            match = True
                        elif egid_int and props.get('EGID') == egid_int:
                            match = True

                        if not match:
                            continue

                        # Gefunden - Geometrie extrahieren
                        if feature['geometry'] is not None:
                            geom = shape(feature['geometry'])
                            result[result_key] = geom.wkb
                            result['loaded_layers'].append(gdb_layer)

                            # FIX 12.01.2026: Wall-Attribute extrahieren für z_min/z_max
                            if gdb_layer == 'Wall':
                                gelaendepunkt = props.get('GELAENDEPUNKT')
                                gesamthoehe = props.get('GESAMTHOEHE')
                                result['wall_props'] = {
                                    'z_min': gelaendepunkt,
                                    'z_max': (gelaendepunkt + gesamthoehe) if gelaendepunkt and gesamthoehe else None
                                }

                            # FIX 12.01.2026: Roof-Attribute extrahieren für dach_min/dach_max
                            if gdb_layer == 'Roof_solid':
                                result['roof_props'] = {
                                    'dach_min': props.get('DACH_MIN'),
                                    'dach_max': props.get('DACH_MAX'),
                                    'gelaendepunkt': props.get('GELAENDEPUNKT'),
                                    'gesamthoehe': props.get('GESAMTHOEHE')
                                }

                            break  # Nur erstes Match pro Layer

            # 4. In DB speichern (auch bei EGID-basiertem Lookup!)
            self._save_all_layers_to_db(egid, gebaeudeeinheit, result)

            elapsed_ms = (time.time() - start) * 1000
            logger.info(
                f"[ALL_LAYERS] EGID {egid} | Layers: {result['loaded_layers']} | {elapsed_ms:.0f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"[ALL_LAYERS] Fehler für {egid}: {e}")
            return result

    def _save_all_layers_to_db(self, egid: str, gebaeudeeinheit: str | None, data: dict):
        """Speichert alle geladenen Layer in die entsprechenden Tabellen."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Roof_solid → building_roofs
                # FIX 12.01.2026: dach_min/dach_max aus roof_props hinzufügen
                if data.get('roof_solid'):
                    roof_props = data.get('roof_props', {})
                    cursor.execute("""
                        INSERT OR REPLACE INTO building_roofs
                        (gebaeudeeinheit, egid, dach_min, dach_max, geometry_wkb, 
                         has_full_geometry, calculated_at, calculation_method)
                        VALUES (?, ?, ?, ?, ?, 1, current_timestamp, 'on_demand_complex')
                    """, (
                        gebaeudeeinheit or f"egid_{egid}",
                        egid,
                        roof_props.get('dach_min'),
                        roof_props.get('dach_max'),
                        data['roof_solid']
                    ))

                # Wall → building_walls
                # FIX 12.01.2026: z_min und z_max aus wall_props hinzufügen
                if data.get('wall'):
                    wall_props = data.get('wall_props', {})
                    cursor.execute("""
                        INSERT OR REPLACE INTO building_walls
                        (gebaeudeeinheit, egid, z_min, z_max, geometry_wkb, created_at)
                        VALUES (?, ?, ?, ?, ?, current_timestamp)
                    """, (
                        gebaeudeeinheit or f"egid_{egid}",
                        egid,
                        wall_props.get('z_min'),
                        wall_props.get('z_max'),
                        data['wall']
                    ))

                # FIX 12.01.2026: has_3d_layers Flag setzen
                cursor.execute("""
                    UPDATE buildings_3d SET has_3d_layers = 1 WHERE egid = ?
                """, (egid,))

                conn.commit()
                logger.debug(f"[ALL_LAYERS] Saved to DB: EGID {egid}")

        except Exception as e:
            logger.error(f"[ALL_LAYERS] DB save error for {egid}: {e}")


# Singleton-Accessor
_service_instance = None


def get_roof_3d_service() -> Roof3DService:
    """Gibt die Singleton-Instanz des Roof3DService zurück."""
    global _service_instance
    if _service_instance is None:
        _service_instance = Roof3DService()
    return _service_instance