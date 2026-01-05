"""
Tile Prefetch Service
=====================

Background-Job der alle EGIDs in einem Tile im Index registriert.

Ablauf:
1. User fragt Gebäude A an
2. Gebäude A wird sofort zurückgegeben
3. Im Hintergrund: Dieser Job registriert ALLE EGIDs im Tile-Index (tiles.db)
4. Nächste EGID-Lookups im selben Tile: O(1) statt Tile-Scan

Verwendet asyncio.create_task() für fire-and-forget Background-Ausführung.

HINWEIS (04.01.2026): Speicherung in building_geodata.db wurde entfernt.
Nur noch EGID-Index-Registrierung in tiles.db.
"""

import asyncio
import logging
import math
from pathlib import Path
from datetime import datetime
from typing import Optional, Set
from threading import Lock

from app.services.tile_cache import get_tile_cache

logger = logging.getLogger(__name__)

# Tracking: Welche Tiles werden gerade geprefetcht (verhindert Duplikate)
_prefetch_in_progress: Set[str] = set()
_prefetch_lock = Lock()


async def prefetch_tile_buildings(
    tile_id: str,
    gdb_path: Path,
    exclude_egid: Optional[str] = None
) -> int:
    """
    Registriert alle EGIDs aus einem Tile im Index (tiles.db).

    Läuft im Hintergrund, blockiert nicht die ursprüngliche Anfrage.
    HINWEIS: Speichert NICHT mehr in building_geodata.db (entfernt 04.01.2026).

    Args:
        tile_id: Tile-Referenz (z.B. "1088-22")
        gdb_path: Pfad zum GDB-Verzeichnis
        exclude_egid: EGID die nicht registriert werden soll (wurde schon registriert)

    Returns:
        Anzahl registrierter EGIDs
    """
    # Check ob bereits ein Prefetch für dieses Tile läuft
    with _prefetch_lock:
        if tile_id in _prefetch_in_progress:
            logger.debug(f"Prefetch für {tile_id} läuft bereits, überspringe")
            return 0
        _prefetch_in_progress.add(tile_id)

    try:
        logger.info(f"🔄 EGID-Registrierung gestartet für Tile {tile_id}")
        start_time = datetime.now()

        # GDB parsen
        buildings = _parse_all_buildings_from_gdb(gdb_path)

        if not buildings:
            logger.warning(f"Keine Gebäude in Tile {tile_id} gefunden")
            return 0

        tile_cache = get_tile_cache()

        registered_count = 0
        skipped_count = 0

        for building in buildings:
            egid = building.get("egid")

            # Skip wenn kein EGID oder explizit ausgeschlossen
            if not egid:
                continue
            if exclude_egid and str(egid) == str(exclude_egid):
                skipped_count += 1
                continue

            # EGID im Tile-Index registrieren (für O(1) Lookups)
            try:
                tile_cache.register_egid(
                    egid=egid,
                    tile_id=tile_id,
                    e=building.get("coord_e"),
                    n=building.get("coord_n")
                )
                registered_count += 1

            except Exception as e:
                logger.warning(f"Fehler beim Registrieren EGID {egid}: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"✅ EGID-Registrierung abgeschlossen: {tile_id} | "
            f"{registered_count} registriert, {skipped_count} übersprungen | "
            f"{elapsed:.1f}s"
        )

        return registered_count

    except Exception as e:
        logger.error(f"Prefetch-Fehler für {tile_id}: {e}")
        return 0

    finally:
        # Lock freigeben
        with _prefetch_lock:
            _prefetch_in_progress.discard(tile_id)


def _parse_all_buildings_from_gdb(gdb_path: Path) -> list:
    """
    Parsed alle Gebäude aus einem GDB-Verzeichnis.

    Extrahiert Polygon, Höhen und Metadaten für jedes Gebäude.

    Returns:
        Liste von Gebäude-Dicts
    """
    try:
        import geopandas as gpd
        import fiona
    except ImportError:
        logger.error("geopandas/fiona nicht verfügbar für Prefetch")
        return []

    buildings = []

    try:
        layers = fiona.listlayers(gdb_path)

        # Building-Layer finden
        target_layer = None
        for layer in layers:
            if 'building' in layer.lower() and 'solid' in layer.lower():
                target_layer = layer
                break
        if not target_layer:
            for layer in layers:
                if 'building' in layer.lower():
                    target_layer = layer
                    break
        if not target_layer and layers:
            target_layer = layers[0]

        if not target_layer:
            return []

        # GDB laden
        gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona')

        for _, row in gdf.iterrows():
            egid = row.get('EGID')
            geom = row.get('geometry')

            if egid is None:
                continue

            try:
                egid_int = int(egid)
                if egid_int <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            # Polygon extrahieren (2D Footprint)
            polygon = None
            center_e, center_n = None, None
            area_m2, perimeter_m = None, None

            if geom is not None:
                try:
                    # 3D → 2D Projektion
                    if hasattr(geom, 'geoms'):
                        # MultiPolygon
                        all_coords_2d = []
                        for g in geom.geoms:
                            if hasattr(g, 'exterior'):
                                coords = [(c[0], c[1]) for c in g.exterior.coords]
                                all_coords_2d.extend(coords)
                        if all_coords_2d:
                            from shapely.geometry import MultiPoint
                            hull = MultiPoint(all_coords_2d).convex_hull
                            if hasattr(hull, 'exterior'):
                                polygon = [[round(c[0], 2), round(c[1], 2)]
                                          for c in hull.exterior.coords]
                    elif hasattr(geom, 'exterior'):
                        # Single Polygon
                        polygon = [[round(c[0], 2), round(c[1], 2)]
                                  for c in geom.exterior.coords]

                    # Zentroid
                    centroid = geom.centroid
                    center_e = round(centroid.x, 1)
                    center_n = round(centroid.y, 1)

                    # Fläche und Umfang
                    if hasattr(geom, 'area'):
                        area_m2 = round(abs(geom.area), 2)
                    if polygon:
                        perimeter_m = round(sum(
                            math.sqrt((polygon[i+1][0] - polygon[i][0])**2 +
                                      (polygon[i+1][1] - polygon[i][1])**2)
                            for i in range(len(polygon) - 1)
                        ), 2)

                except Exception as e:
                    logger.debug(f"Geometrie-Fehler für EGID {egid}: {e}")

            # Höhen extrahieren
            dach_max = row.get('DACH_MAX')
            dach_min = row.get('DACH_MIN')
            gelaendepunkt = row.get('GELAENDEPUNKT')
            gesamthoehe = row.get('GESAMTHOEHE')

            terrain_f = float(gelaendepunkt) if gelaendepunkt is not None else None
            dach_max_f = float(dach_max) if dach_max is not None else None
            dach_min_f = float(dach_min) if dach_min is not None else None
            gesamt_f = float(gesamthoehe) if gesamthoehe is not None else None

            traufhoehe = None
            firsthoehe = None

            if terrain_f is not None:
                if dach_min_f is not None:
                    traufhoehe = round(dach_min_f - terrain_f, 2)
                if dach_max_f is not None:
                    firsthoehe = round(dach_max_f - terrain_f, 2)

            buildings.append({
                "egid": egid_int,
                "polygon": polygon,
                "traufhoehe_m": traufhoehe,
                "firsthoehe_m": firsthoehe,
                "gebaeudehoehe_m": round(gesamt_f, 2) if gesamt_f else (firsthoehe or traufhoehe),
                "area_m2": area_m2,
                "perimeter_m": perimeter_m,
                "center_e": center_e,
                "center_n": center_n,
                "coord_e": center_e,
                "coord_n": center_n,
            })

        return buildings

    except Exception as e:
        logger.error(f"GDB-Parsing-Fehler: {e}")
        return []


def schedule_prefetch(tile_id: str, gdb_path: Path, exclude_egid: Optional[str] = None):
    """
    Plant einen Prefetch-Job im Hintergrund.

    Fire-and-forget: Kehrt sofort zurück, Job läuft async.

    Args:
        tile_id: Tile-Referenz
        gdb_path: Pfad zum gecachten GDB
        exclude_egid: EGID die nicht geladen werden soll
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            prefetch_tile_buildings(tile_id, gdb_path, exclude_egid)
        )
        logger.debug(f"Prefetch-Task geplant für {tile_id}")
    except RuntimeError:
        # Kein laufender Event-Loop - synchron starten
        logger.debug(f"Kein Event-Loop, starte Prefetch synchron für {tile_id}")
        asyncio.run(prefetch_tile_buildings(tile_id, gdb_path, exclude_egid))


def get_prefetch_status() -> dict:
    """Gibt Status der laufenden Prefetch-Jobs zurück."""
    with _prefetch_lock:
        return {
            "in_progress": list(_prefetch_in_progress),
            "count": len(_prefetch_in_progress)
        }
