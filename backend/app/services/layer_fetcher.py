"""
Layer Fetcher Service
=====================

On-Demand Laden von 3D-Layern (Wall, Floor) für komplexe Gebäude.

Wird aufgerufen wenn:
1. Gebäude als MODERATE/COMPLEX klassifiziert ist
2. User explizit "3D-Daten laden" klickt
3. 3D-Visualisierung aktiviert wird

Ablauf:
1. Prüfen ob bereits geladen (has_3d_layers Flag)
2. Koordinaten aus buildings_3d holen
3. Tile downloaden (temporär)
4. Wall + Floor parsen (nur Features mit passender GEBAEUDEEINHEIT)
5. In DB speichern
6. has_3d_layers Flag setzen
7. Tile LÖSCHEN (Speicher sparen)

Version: 1.0 (11.01.2026)
NEU 13.01.2026 17:00: DuckDB-kompatibel via get_building_3d_connection()
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# NEU 13.01.2026 17:00: DuckDB-kompatible Connection
# FIX 14.01.2026 13:50: DATA_DIR aus config.py für Railway Volume
from app.config import get_building_3d_connection, BUILDING_3D_DB_PATH, DATA_DIR

logger = logging.getLogger(__name__)

# Pfad zur Datenbank (aus config.py)
BUILDING_3D_DB = BUILDING_3D_DB_PATH


class LayerFetcherService:
    """
    On-Demand Layer-Loader für komplexe Gebäude.

    Lädt Wall und Floor Layer nur bei Bedarf,
    um Speicher zu sparen.
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

    async def fetch_3d_layers_for_building(
        self,
        egid: str,
        gebaeudeeinheit: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Lädt Wall und Floor für ein spezifisches Gebäude.

        Args:
            egid: Eidgenössischer Gebäudeidentifikator
            gebaeudeeinheit: Optional, für präzises Matching
            force: Erzwingt Neuladenm auch wenn bereits vorhanden

        Returns:
            Dict mit Status und geladenen Daten
        """
        from app.services.building_3d_service import get_building_3d_service

        building_service = get_building_3d_service()

        # 1. Prüfen ob bereits geladen
        building = building_service.get_by_egid(int(egid))
        if not building:
            return {
                "success": False,
                "error": f"Gebäude {egid} nicht gefunden",
                "walls_count": 0,
                "floors_count": 0
            }

        if building.get('has_3d_layers') and not force:
            return {
                "success": True,
                "message": "3D-Layer bereits vorhanden",
                "walls_count": 0,
                "floors_count": 0,
                "from_cache": True
            }

        # 2. Koordinaten und gebaeudeeinheit holen
        center_e = building.get('center_e')
        center_n = building.get('center_n')

        if not center_e or not center_n:
            return {
                "success": False,
                "error": "Keine Koordinaten für Gebäude",
                "walls_count": 0,
                "floors_count": 0
            }

        if not gebaeudeeinheit:
            gebaeudeeinheit = building.get('gebaeudeeinheit')

        if not gebaeudeeinheit:
            logger.warning(f"Keine gebaeudeeinheit für EGID {egid}")
            return {
                "success": False,
                "error": "Keine gebaeudeeinheit für Layer-Verknüpfung",
                "walls_count": 0,
                "floors_count": 0
            }

        # 3. Tile downloaden (NEU 14.01.2026: Mit Auto-Reload für 'cleaned' Tiles)
        from app.services.tile_cache import get_tile_cache
        tile_cache = get_tile_cache()

        try:
            # NEU 14.01.2026: Nutzt get_or_redownload_tile_for_coordinates
            # Diese Funktion lädt 'cleaned' Tiles automatisch neu!
            tile_path, tile_id = await tile_cache.get_or_redownload_tile_for_coordinates(
                center_e, center_n
            )

            if not tile_path:
                return {
                    "success": False,
                    "error": "Tile konnte nicht geladen werden (download_url nicht vorhanden)",
                    "walls_count": 0,
                    "floors_count": 0
                }

            # 4. Layer parsen
            result = self._parse_layers_for_building(
                gdb_path=tile_path,
                target_gebaeudeeinheit=gebaeudeeinheit,
                egid=egid
            )

            # 5. In DB speichern
            walls_saved = self._save_walls(result.get('walls', []))
            floors_saved = self._save_floors(result.get('floors', []))

            # 6. has_3d_layers Flag setzen
            if walls_saved > 0 or floors_saved > 0:
                self._update_has_3d_layers(egid)

            # FIX 20.01.2026: Cleanup NICHT hier machen!
            # Das Cleanup soll NUR in tile_prefetch.py passieren, NACHDEM
            # der vollständige Prefetch (inkl. aller Layer) abgeschlossen ist.
            # Vorher wurde das GDB hier gelöscht während der Prefetch noch lief!

            return {
                "success": True,
                "walls_count": walls_saved,
                "floors_count": floors_saved,
                "gebaeudeeinheit": gebaeudeeinheit,
                "tile_id": tile_id
            }

        except Exception as e:
            logger.error(f"Fehler beim Laden der 3D-Layer für {egid}: {e}")
            return {
                "success": False,
                "error": str(e),
                "walls_count": 0,
                "floors_count": 0
            }

    def _parse_layers_for_building(
        self,
        gdb_path: Path,
        target_gebaeudeeinheit: str,
        egid: str
    ) -> Dict[str, List]:
        """
        Parsed nur die Features mit passender GEBAEUDEEINHEIT.

        Viel schneller als komplettes Tile zu parsen!
        """
        try:
            import fiona
            from shapely.geometry import shape
        except ImportError:
            logger.error("fiona/shapely nicht verfügbar")
            return {'walls': [], 'floors': []}

        result = {'walls': [], 'floors': []}

        try:
            layers = fiona.listlayers(gdb_path)

            # Wall Layer parsen
            wall_layer = None
            for layer in layers:
                if 'wall' in layer.lower():
                    wall_layer = layer
                    break

            if wall_layer:
                with fiona.open(gdb_path, layer=wall_layer) as src:
                    for feature in src:
                        props = feature['properties']
                        if props.get('GEBAEUDEEINHEIT') != target_gebaeudeeinheit:
                            continue

                        geom = shape(feature['geometry']) if feature['geometry'] else None
                        geometry_wkb = geom.wkb if geom else None

                        # FIX 12.01.2026: z_max berechnen aus GELAENDEPUNKT + GESAMTHOEHE
                        # Wall-Layer hat kein DACH_MIN, nur GELAENDEPUNKT und GESAMTHOEHE
                        gelaendepunkt = props.get('GELAENDEPUNKT')
                        gesamthoehe = props.get('GESAMTHOEHE')
                        z_max = (gelaendepunkt + gesamthoehe) if gelaendepunkt and gesamthoehe else None

                        result['walls'].append({
                            'gebaeudeeinheit': target_gebaeudeeinheit,
                            'egid': egid,
                            'z_min': gelaendepunkt,
                            'z_max': z_max,
                            'geometry_wkb': geometry_wkb
                        })

            # Floor Layer parsen
            # DEAKTIVIERT 12.01.2026 - BUG-021: Floor-Layer hat unsupported Geometry-Typ
            # fiona.errors.UnsupportedGeometryTypeError: 2147483648
            # Der Floor-Layer in swissBUILDINGS3D verwendet einen 3D-Geometrie-Typ,
            # den Fiona nicht unterstützt. Bis ein Workaround gefunden wird, ist
            # der Floor-Import deaktiviert. Die Daten sind redundant zum Building_solid.
            #
            # floor_layer = None
            # for layer in layers:
            #     if 'floor' in layer.lower():
            #         floor_layer = layer
            #         break
            #
            # if floor_layer:
            #     with fiona.open(gdb_path, layer=floor_layer) as src:
            #         for feature in src:
            #             props = feature['properties']
            #             if props.get('GEBAEUDEEINHEIT') != target_gebaeudeeinheit:
            #                 continue
            #
            #             geom = shape(feature['geometry']) if feature['geometry'] else None
            #             geometry_wkb = geom.wkb if geom else None
            #
            #             result['floors'].append({
            #                 'gebaeudeeinheit': target_gebaeudeeinheit,
            #                 'egid': egid,
            #                 'gelaendepunkt': props.get('GELAENDEPUNKT'),
            #                 'geometry_wkb': geometry_wkb
            #             })

            logger.info(
                f"[LAYER-FETCH] {target_gebaeudeeinheit}: "
                f"{len(result['walls'])} Walls, {len(result['floors'])} Floors"
            )

            return result

        except Exception as e:
            logger.error(f"Layer-Parsing-Fehler: {e}")
            return {'walls': [], 'floors': []}

    def _save_walls(self, walls: List[Dict]) -> int:
        """Speichert Wall-Daten in building_walls."""
        if not walls:
            return 0

        # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
        conn = get_building_3d_connection()
        cursor = conn.cursor()

        try:
            # FIX 19.01.2026: execute statt executemany für BLOB-Kompatibilität mit DuckDB
            # executemany hat Probleme mit BLOB-Feldern (geometry_wkb bleibt NULL)
            saved_count = 0
            for w in walls:
                try:
                    # FIX 19.01.2026: EGID als Integer konvertieren (DB-Schema: INTEGER)
                    egid_val = w['egid']
                    try:
                        egid_int = int(egid_val) if egid_val else None
                    except (ValueError, TypeError):
                        egid_int = None
                        logger.warning(f"EGID '{egid_val}' konnte nicht zu Integer konvertiert werden")

                    cursor.execute("""
                        INSERT OR REPLACE INTO building_walls
                        (gebaeudeeinheit, egid, z_min, z_max, geometry_wkb, created_at)
                        VALUES (?, ?, ?, ?, ?, current_timestamp)
                    """, (
                        w['gebaeudeeinheit'],
                        egid_int,
                        w['z_min'],
                        w['z_max'],
                        w['geometry_wkb']
                    ))
                    saved_count += 1
                except Exception as wall_err:
                    logger.warning(f"Wall speichern fehlgeschlagen: {wall_err}")

            conn.commit()
            logger.info(f"[LAYER_FETCHER] {saved_count}/{len(walls)} Walls gespeichert")
            return saved_count

        except Exception as e:
            logger.error(f"Fehler beim Speichern der Walls: {e}")
            conn.rollback()
            return 0

        finally:
            conn.close()

    def _save_floors(self, floors: List[Dict]) -> int:
        """Speichert Floor-Daten in building_floors."""
        if not floors:
            return 0

        # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
        conn = get_building_3d_connection()
        cursor = conn.cursor()

        try:
            # FIX 19.01.2026: execute statt executemany für BLOB-Kompatibilität mit DuckDB
            saved_count = 0
            for f in floors:
                try:
                    # FIX 19.01.2026: EGID als Integer konvertieren (DB-Schema: INTEGER)
                    egid_val = f['egid']
                    try:
                        egid_int = int(egid_val) if egid_val else None
                    except (ValueError, TypeError):
                        egid_int = None

                    cursor.execute("""
                        INSERT OR REPLACE INTO building_floors
                        (gebaeudeeinheit, egid, gelaendepunkt, geometry_wkb, created_at)
                        VALUES (?, ?, ?, ?, current_timestamp)
                    """, (
                        f['gebaeudeeinheit'],
                        egid_int,
                        f['gelaendepunkt'],
                        f['geometry_wkb']
                    ))
                    saved_count += 1
                except Exception as floor_err:
                    logger.warning(f"Floor speichern fehlgeschlagen: {floor_err}")

            conn.commit()
            logger.info(f"[LAYER_FETCHER] {saved_count}/{len(floors)} Floors gespeichert")
            return saved_count

        except Exception as e:
            logger.error(f"Fehler beim Speichern der Floors: {e}")
            conn.rollback()
            return 0

        finally:
            conn.close()

    def _update_has_3d_layers(self, egid: str):
        """Setzt has_3d_layers Flag in buildings_3d."""
        # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
        conn = get_building_3d_connection()
        cursor = conn.cursor()

        try:
            # FIX 18.01.2026 22:10: EGID als Integer übergeben (DB-Schema: INTEGER)
            egid_int = int(egid) if egid else None
            cursor.execute("""
                UPDATE buildings_3d
                SET has_3d_layers = 1
                WHERE egid = ?
            """, (egid_int,))

            conn.commit()

        except Exception as e:
            logger.error(f"Fehler beim Setzen von has_3d_layers: {e}")

        finally:
            conn.close()

    def get_walls_for_building(self, egid: str) -> List[Dict]:
        """Holt Wall-Daten für ein Gebäude."""
        # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
        conn = get_building_3d_connection()
        cursor = conn.cursor()

        try:
            # FIX 18.01.2026 22:10: EGID als Integer übergeben (DB-Schema: INTEGER)
            egid_int = int(egid) if egid else None
            cursor.execute("""
                SELECT gebaeudeeinheit, egid, z_min, z_max, geometry_wkb
                FROM building_walls WHERE egid = ?
            """, (egid_int,))

            results = []
            for row in cursor.fetchall():
                # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
                if isinstance(row, tuple):
                    results.append({
                        'gebaeudeeinheit': row[0],
                        'egid': row[1],
                        'z_min': row[2],
                        'z_max': row[3],
                        'geometry_wkb': row[4]
                    })
                else:
                    results.append(dict(row))
            return results

        finally:
            conn.close()

    def get_floors_for_building(self, egid: str) -> List[Dict]:
        """Holt Floor-Daten für ein Gebäude."""
        # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
        conn = get_building_3d_connection()
        cursor = conn.cursor()

        try:
            # FIX 18.01.2026 22:10: EGID als Integer übergeben (DB-Schema: INTEGER)
            egid_int = int(egid) if egid else None
            cursor.execute("""
                SELECT gebaeudeeinheit, egid, gelaendepunkt, geometry_wkb
                FROM building_floors WHERE egid = ?
            """, (egid_int,))

            results = []
            for row in cursor.fetchall():
                # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
                if isinstance(row, tuple):
                    results.append({
                        'gebaeudeeinheit': row[0],
                        'egid': row[1],
                        'gelaendepunkt': row[2],
                        'geometry_wkb': row[3]
                    })
                else:
                    results.append(dict(row))
            return results

        finally:
            conn.close()

    def get_roofs_for_building(self, egid: str) -> List[Dict]:
        """Holt Roof-Daten für ein Gebäude.

        NEU 15.01.2026 23:30 - Analog zu get_walls_for_building()
        """
        conn = get_building_3d_connection()
        cursor = conn.cursor()

        try:
            # FIX 18.01.2026 22:10: EGID als Integer übergeben (DB-Schema: INTEGER)
            egid_int = int(egid) if egid else None
            cursor.execute("""
                SELECT gebaeudeeinheit, egid, dach_min, dach_max,
                       roof_form, roof_angle_deg, roof_orientation, geometry_wkb
                FROM building_roofs WHERE egid = ?
            """, (egid_int,))

            results = []
            for row in cursor.fetchall():
                # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
                if isinstance(row, tuple):
                    results.append({
                        'gebaeudeeinheit': row[0],
                        'egid': row[1],
                        'dach_min': row[2],
                        'dach_max': row[3],
                        'roof_form': row[4],
                        'roof_angle_deg': row[5],
                        'roof_orientation': row[6],
                        'geometry_wkb': row[7]
                    })
                else:
                    results.append(dict(row))
            return results

        finally:
            conn.close()

    def has_3d_layers(self, egid: str) -> bool:
        """Prüft ob ein Gebäude 3D-Layer hat."""
        from app.services.building_3d_service import get_building_3d_service

        building = get_building_3d_service().get_by_egid(int(egid))
        return building.get('has_3d_layers', 0) == 1 if building else False


# Singleton-Accessor
_service_instance = None


def get_layer_fetcher_service() -> LayerFetcherService:
    """Gibt die Singleton-Instanz des LayerFetcherService zurück."""
    global _service_instance
    if _service_instance is None:
        _service_instance = LayerFetcherService()
    return _service_instance