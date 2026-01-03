"""
Tile Prefetch Service
=====================

Background-Job der alle Gebäude in einem Tile vorab lädt.

Ablauf:
1. User fragt Gebäude A an
2. Gebäude A wird sofort zurückgegeben
3. Im Hintergrund: Dieser Job parsed ALLE Gebäude im Tile
4. Speichert sie in building_geodata.db
5. Nächste Anfrage im selben Tile: ~1ms statt ~50ms

Verwendet asyncio.create_task() für fire-and-forget Background-Ausführung.
"""

import asyncio
import logging
import math
from pathlib import Path
from datetime import datetime
from typing import Optional, Set
from threading import Lock

from app.services.geodata_service import get_geodata_service, BuildingGeodata
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
    Lädt alle Gebäude aus einem Tile in die Geodata-DB.

    Läuft im Hintergrund, blockiert nicht die ursprüngliche Anfrage.

    Args:
        tile_id: Tile-Referenz (z.B. "1088-22")
        gdb_path: Pfad zum GDB-Verzeichnis
        exclude_egid: EGID die nicht geladen werden soll (wurde schon geladen)

    Returns:
        Anzahl geladener Gebäude
    """
    # Check ob bereits ein Prefetch für dieses Tile läuft
    with _prefetch_lock:
        if tile_id in _prefetch_in_progress:
            logger.debug(f"Prefetch für {tile_id} läuft bereits, überspringe")
            return 0
        _prefetch_in_progress.add(tile_id)

    try:
        logger.info(f"🔄 Prefetch gestartet für Tile {tile_id}")
        start_time = datetime.now()

        # GDB parsen
        buildings = _parse_all_buildings_from_gdb(gdb_path)

        if not buildings:
            logger.warning(f"Keine Gebäude in Tile {tile_id} gefunden")
            return 0

        # Geodata-Service für Speicherung
        geodata_service = get_geodata_service()
        tile_cache = get_tile_cache()

        saved_count = 0
        skipped_count = 0

        for building in buildings:
            egid = building.get("egid")

            # Skip wenn kein EGID oder explizit ausgeschlossen
            if not egid:
                continue
            if exclude_egid and str(egid) == str(exclude_egid):
                skipped_count += 1
                continue

            # Prüfen ob schon in DB
            existing = geodata_service.get_by_egid(str(egid))
            if existing and existing.polygon:
                skipped_count += 1
                continue

            # In DB speichern
            try:
                geodata = BuildingGeodata(
                    egid=str(egid),
                    polygon=building.get("polygon"),
                    traufhoehe_m=building.get("traufhoehe_m"),
                    firsthoehe_m=building.get("firsthoehe_m"),
                    gebaeudehoehe_m=building.get("gebaeudehoehe_m"),
                    area_m2=building.get("area_m2"),
                    perimeter_m=building.get("perimeter_m"),
                    center_e=building.get("center_e"),
                    center_n=building.get("center_n"),
                    coord_e=building.get("coord_e"),
                    coord_n=building.get("coord_n"),
                    fetched_at=datetime.utcnow().isoformat()
                )
                geodata_service.save(geodata)
                saved_count += 1

                # EGID im Tile-Index registrieren
                tile_cache.register_egid(
                    egid=egid,
                    tile_id=tile_id,
                    e=building.get("coord_e"),
                    n=building.get("coord_n")
                )

            except Exception as e:
                logger.warning(f"Fehler beim Speichern EGID {egid}: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"✅ Prefetch abgeschlossen: {tile_id} | "
            f"{saved_count} gespeichert, {skipped_count} übersprungen | "
            f"{elapsed:.1f}s"
        )

        return saved_count

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
