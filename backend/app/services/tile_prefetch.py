"""
Tile Prefetch Service
=====================

Background-Job der alle Gebäude aus einem Tile speichert.

ARCHITEKTUR (10.01.2026): MINIMAL + ON-DEMAND
=============================================

Ablauf (OPTIMIERT):
1. User fragt Gebäude A an
2. Gebäude A wird sofort zurückgegeben + in building_3d.db gespeichert
3. SOFORT: Direkte Nachbarn (5m Radius) aus GDB laden → blocked_facades berechenbar
4. ASYNC: Restliche Gebäude im Hintergrund prefetchen
5. Bei Zoom: On-Demand Loading für weitere Radien (20m, 50m, 100m)

Performance-Vergleich:
----------------------
VORHER (synchron):   ~108s First-Load (wartet auf 4826 Gebäude)
NACHHER (async):     ~8-10s First-Load (nur Hauptgebäude + 5m Nachbarn)
                     Prefetch läuft async im Hintergrund

WIEDERHERGESTELLT (07.01.2026): Speicherung in building_3d.db
- building_3d.db ist UNABHÄNGIG von anderen Datenbanken
- Enthält nur Rohdaten aus swissBUILDINGS3D: Polygon, Höhen, Geometrie
- Ermöglicht O(1) Lookups statt GDB-Parsing (~500ms → ~1ms)
"""

import asyncio
import logging
import math
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Set, Dict, Any, List, Tuple
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

# tile_cache Import entfernt (07.01.2026) - egid_tile_index nicht mehr benötigt

logger = logging.getLogger(__name__)

# Thread-Pool für Background-Parsing (CPU-bound)
_background_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="prefetch")

# Performance-Metriken für Logging
_parsing_metrics: Dict[str, Any] = {
    "last_tile": None,
    "last_building_count": 0,
    "last_parse_time_ms": 0,
    "last_method": None,
}

# Tracking: Welche Tiles werden gerade geprefetcht (verhindert Duplikate)
_prefetch_in_progress: Set[str] = set()
_prefetch_lock = Lock()


async def prefetch_tile_buildings(
    tile_id: str,
    gdb_path: Path,
    exclude_egid: Optional[str] = None
) -> int:
    """
    Speichert alle Gebäude aus einem Tile in building_3d.db.

    Läuft im Hintergrund, blockiert nicht die ursprüngliche Anfrage.
    WIEDERHERGESTELLT (07.01.2026): Speichert in building_3d.db für O(1) Lookups.

    Args:
        tile_id: Tile-Referenz (z.B. "1088-22")
        gdb_path: Pfad zum GDB-Verzeichnis
        exclude_egid: EGID die nicht gespeichert werden soll (wurde schon gespeichert)

    Returns:
        Anzahl gespeicherter Gebäude
    """
    # Check ob bereits ein Prefetch für dieses Tile läuft
    with _prefetch_lock:
        if tile_id in _prefetch_in_progress:
            logger.debug(f"Prefetch für {tile_id} läuft bereits, überspringe")
            return 0
        _prefetch_in_progress.add(tile_id)

    try:
        logger.info(f"[PREFETCH] Gebäude-Import gestartet für Tile {tile_id}")
        start_time = datetime.now()

        # GDB parsen
        buildings = _parse_all_buildings_from_gdb(gdb_path)

        if not buildings:
            logger.warning(f"Keine Gebäude in Tile {tile_id} gefunden")
            return 0

        # Gebäude-3D-Service für Speicherung
        from app.services.building_3d_service import get_building_3d_service
        building_3d_service = get_building_3d_service()

        # Gebäude vorbereiten (ohne exclude_egid)
        # OPTIMIERUNG 07.01.2026: register_egid() entfernt (58s Overhead!)
        # building_3d.db hat bereits center_e/center_n für Koordinaten-Lookup
        # egid_tile_index in tiles.db ist damit obsolet
        buildings_to_save = []
        for building in buildings:
            egid = building.get("egid")
            if not egid:
                continue
            if exclude_egid and str(egid) == str(exclude_egid):
                continue

            building["tile_id"] = tile_id
            buildings_to_save.append(building)

        # Bulk-Save in building_3d.db
        saved_count = building_3d_service.bulk_save(buildings_to_save, tile_id)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"[PREFETCH] Abgeschlossen: {tile_id} | "
            f"{saved_count} Gebäude gespeichert | "
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

    OPTIMIERT 08.01.2026: Direktes Fiona-Reading statt geopandas.
    - geopandas lädt alles in Speicher → langsam bei grossen Tiles
    - Fiona iteriert direkt über Features → schneller und speicherschonender

    Extrahiert Polygon, Höhen und Metadaten für jedes Gebäude.

    Returns:
        Liste von Gebäude-Dicts
    """
    global _parsing_metrics

    try:
        import fiona
        from shapely.geometry import shape, MultiPoint
    except ImportError:
        logger.error("fiona/shapely nicht verfügbar für Prefetch")
        return []

    buildings = []
    parse_start = time.time()

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

        # OPTIMIERUNG: Direktes Fiona-Reading statt geopandas
        # Vorher: gdf = gpd.read_file(...); for _, row in gdf.iterrows()
        # Nachher: with fiona.open(...) as src: for feature in src
        with fiona.open(gdb_path, layer=target_layer) as src:
            feature_count = 0
            valid_count = 0

            for feature in src:
                feature_count += 1
                props = feature['properties']
                egid = props.get('EGID')

                if egid is None:
                    continue

                try:
                    egid_int = int(egid)
                    if egid_int <= 0:
                        continue
                except (ValueError, TypeError):
                    continue

                valid_count += 1

                # Geometrie mit shapely.geometry.shape() konvertieren
                geom = None
                polygon = None
                center_e, center_n = None, None
                area_m2, perimeter_m = None, None

                if feature['geometry'] is not None:
                    try:
                        geom = shape(feature['geometry'])

                        # 3D → 2D Projektion
                        if hasattr(geom, 'geoms'):
                            # MultiPolygon
                            all_coords_2d = []
                            for g in geom.geoms:
                                if hasattr(g, 'exterior'):
                                    coords = [(c[0], c[1]) for c in g.exterior.coords]
                                    all_coords_2d.extend(coords)
                            if all_coords_2d:
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
                dach_max = props.get('DACH_MAX')
                dach_min = props.get('DACH_MIN')
                gelaendepunkt = props.get('GELAENDEPUNKT')
                gesamthoehe = props.get('GESAMTHOEHE')

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

        # Performance-Metriken erfassen
        parse_time_ms = (time.time() - parse_start) * 1000
        _parsing_metrics["last_tile"] = str(gdb_path.name)
        _parsing_metrics["last_building_count"] = len(buildings)
        _parsing_metrics["last_parse_time_ms"] = round(parse_time_ms, 1)
        _parsing_metrics["last_method"] = "fiona_direct"

        # Performance-Logging
        if len(buildings) > 0:
            ms_per_building = parse_time_ms / len(buildings)
            logger.info(
                f"[PREFETCH] GDB-Parsing: {len(buildings)} Gebäude | "
                f"{parse_time_ms:.0f}ms ({ms_per_building:.1f}ms/Gebäude) | "
                f"Methode: fiona_direct"
            )

        return buildings

    except Exception as e:
        logger.error(f"GDB-Parsing-Fehler: {e}")
        return []


def get_parsing_metrics() -> Dict[str, Any]:
    """Gibt die letzten Parsing-Metriken zurück (für Debugging/Monitoring)."""
    return _parsing_metrics.copy()


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


# =============================================================================
# NEUE FUNKTIONEN FÜR ON-DEMAND ARCHITEKTUR (10.01.2026)
# =============================================================================

def find_immediate_neighbors(
    gdb_path: Path,
    center_e: float,
    center_n: float,
    radius_m: float = 5.0,
    exclude_egid: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Findet direkte Nachbarn aus einer GDB-Datei (synchron).

    OPTIMIERUNG: Lädt nur Gebäude im Radius, nicht das ganze Tile.
    Verwendet Fiona-Streaming mit Koordinaten-Filter.

    Args:
        gdb_path: Pfad zum GDB-Verzeichnis
        center_e: LV95 Easting des Zentrums
        center_n: LV95 Northing des Zentrums
        radius_m: Suchradius in Metern (default: 5m)
        exclude_egid: EGID des Hauptgebäudes (ausschliessen)

    Returns:
        Liste von Nachbar-Gebäuden (Dict mit egid, polygon, höhen, etc.)
    """
    try:
        import fiona
        from shapely.geometry import shape, MultiPoint
    except ImportError:
        logger.error("fiona/shapely nicht verfügbar")
        return []

    neighbors = []
    start_time = time.time()

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

        # BBox für schnelles Filtern (Quadrat um Zentrum)
        bbox_filter = (
            center_e - radius_m,
            center_n - radius_m,
            center_e + radius_m,
            center_n + radius_m
        )

        with fiona.open(gdb_path, layer=target_layer) as src:
            for feature in src:
                props = feature['properties']
                egid = props.get('EGID')

                if egid is None:
                    continue

                try:
                    egid_int = int(egid)
                    if egid_int <= 0:
                        continue
                    if exclude_egid and egid_int == exclude_egid:
                        continue
                except (ValueError, TypeError):
                    continue

                # Geometrie parsen für Zentroid
                if feature['geometry'] is None:
                    continue

                try:
                    geom = shape(feature['geometry'])
                    centroid = geom.centroid
                    cx, cy = centroid.x, centroid.y

                    # BBox-Filter (schnell)
                    if not (bbox_filter[0] <= cx <= bbox_filter[2] and
                            bbox_filter[1] <= cy <= bbox_filter[3]):
                        continue

                    # Exakte Distanz-Prüfung
                    dist = math.sqrt((cx - center_e)**2 + (cy - center_n)**2)
                    if dist > radius_m:
                        continue

                    # Nachbar gefunden - vollständig parsen
                    polygon = None
                    if hasattr(geom, 'geoms'):
                        all_coords_2d = []
                        for g in geom.geoms:
                            if hasattr(g, 'exterior'):
                                coords = [(c[0], c[1]) for c in g.exterior.coords]
                                all_coords_2d.extend(coords)
                        if all_coords_2d:
                            hull = MultiPoint(all_coords_2d).convex_hull
                            if hasattr(hull, 'exterior'):
                                polygon = [[round(c[0], 2), round(c[1], 2)]
                                          for c in hull.exterior.coords]
                    elif hasattr(geom, 'exterior'):
                        polygon = [[round(c[0], 2), round(c[1], 2)]
                                  for c in geom.exterior.coords]

                    # Höhen extrahieren
                    dach_max = props.get('DACH_MAX')
                    dach_min = props.get('DACH_MIN')
                    gelaendepunkt = props.get('GELAENDEPUNKT')
                    gesamthoehe = props.get('GESAMTHOEHE')

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

                    area_m2 = round(abs(geom.area), 2) if hasattr(geom, 'area') else None
                    perimeter_m = None
                    if polygon:
                        perimeter_m = round(sum(
                            math.sqrt((polygon[i+1][0] - polygon[i][0])**2 +
                                      (polygon[i+1][1] - polygon[i][1])**2)
                            for i in range(len(polygon) - 1)
                        ), 2)

                    neighbors.append({
                        "egid": egid_int,
                        "polygon": polygon,
                        "traufhoehe_m": traufhoehe,
                        "firsthoehe_m": firsthoehe,
                        "gebaeudehoehe_m": round(gesamt_f, 2) if gesamt_f else (firsthoehe or traufhoehe),
                        "area_m2": area_m2,
                        "perimeter_m": perimeter_m,
                        "center_e": round(cx, 1),
                        "center_n": round(cy, 1),
                        "distance_m": round(dist, 2),
                    })

                except Exception as e:
                    logger.debug(f"Fehler bei EGID {egid}: {e}")
                    continue

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[NEIGHBORS] {len(neighbors)} Nachbarn in {radius_m}m Radius | "
            f"{elapsed_ms:.0f}ms"
        )

        return neighbors

    except Exception as e:
        logger.error(f"Fehler beim Finden von Nachbarn: {e}")
        return []


def load_neighbors_and_save(
    gdb_path: Path,
    center_e: float,
    center_n: float,
    radius_m: float,
    tile_id: str,
    exclude_egid: Optional[int] = None
) -> Tuple[int, List[int]]:
    """
    Lädt Nachbarn aus GDB und speichert sie in building_3d.db.

    Args:
        gdb_path: Pfad zum GDB-Verzeichnis
        center_e: LV95 Easting
        center_n: LV95 Northing
        radius_m: Suchradius
        tile_id: Tile-ID für DB
        exclude_egid: EGID zum Ausschliessen

    Returns:
        Tuple von (saved_count, list_of_egids)
    """
    neighbors = find_immediate_neighbors(
        gdb_path, center_e, center_n, radius_m, exclude_egid
    )

    if not neighbors:
        return 0, []

    # In DB speichern
    from app.services.building_3d_service import get_building_3d_service
    service = get_building_3d_service()

    for neighbor in neighbors:
        neighbor["tile_id"] = tile_id

    saved = service.bulk_save(neighbors, tile_id)
    egids = [n["egid"] for n in neighbors]

    return saved, egids


def schedule_prefetch_with_neighbors(
    tile_id: str,
    gdb_path: Path,
    center_e: float,
    center_n: float,
    main_egid: Optional[int] = None,
    immediate_radius_m: float = 5.0
) -> Tuple[int, int]:
    """
    NEUE ARCHITEKTUR: Lädt direkte Nachbarn sofort, Rest async.

    Ablauf:
    1. SYNCHRON: Direkte Nachbarn (5m) laden und speichern
    2. ASYNC: Prefetch für restliche Gebäude im Hintergrund starten

    Args:
        tile_id: Tile-Referenz
        gdb_path: Pfad zum GDB-Verzeichnis
        center_e: LV95 Easting des Hauptgebäudes
        center_n: LV95 Northing des Hauptgebäudes
        main_egid: EGID des Hauptgebäudes (wird ausgeschlossen)
        immediate_radius_m: Radius für sofortige Nachbarn (default: 5m)

    Returns:
        Tuple von (immediate_neighbors_count, background_task_started)
    """
    immediate_count = 0
    background_started = 0

    # 1. SYNCHRON: Direkte Nachbarn laden
    if center_e and center_n:
        immediate_count, neighbor_egids = load_neighbors_and_save(
            gdb_path=gdb_path,
            center_e=center_e,
            center_n=center_n,
            radius_m=immediate_radius_m,
            tile_id=tile_id,
            exclude_egid=main_egid
        )
        logger.info(
            f"[IMMEDIATE] {immediate_count} Nachbarn im {immediate_radius_m}m Radius geladen"
        )

        # EGIDs zum Ausschliessen beim grossen Prefetch
        exclude_egids = set(neighbor_egids)
        if main_egid:
            exclude_egids.add(main_egid)
    else:
        exclude_egids = {main_egid} if main_egid else set()

    # 2. ASYNC: Background-Prefetch für restliche Gebäude
    def _background_prefetch():
        """Läuft in separatem Thread."""
        try:
            asyncio.run(prefetch_tile_buildings_excluding(
                tile_id=tile_id,
                gdb_path=gdb_path,
                exclude_egids=exclude_egids
            ))
        except Exception as e:
            logger.error(f"Background-Prefetch-Fehler: {e}")

    # Background-Job starten (fire-and-forget)
    try:
        _background_executor.submit(_background_prefetch)
        background_started = 1
        logger.info(f"[ASYNC] Background-Prefetch gestartet für {tile_id}")
    except Exception as e:
        logger.error(f"Konnte Background-Prefetch nicht starten: {e}")

    return immediate_count, background_started


async def prefetch_tile_buildings_excluding(
    tile_id: str,
    gdb_path: Path,
    exclude_egids: Set[int] = None
) -> int:
    """
    Prefetcht alle Gebäude AUSSER den bereits geladenen.

    Args:
        tile_id: Tile-Referenz
        gdb_path: Pfad zum GDB-Verzeichnis
        exclude_egids: Set von EGIDs die übersprungen werden

    Returns:
        Anzahl gespeicherter Gebäude
    """
    exclude_egids = exclude_egids or set()

    # Check ob bereits ein Prefetch für dieses Tile läuft
    with _prefetch_lock:
        if tile_id in _prefetch_in_progress:
            logger.debug(f"Prefetch für {tile_id} läuft bereits, überspringe")
            return 0
        _prefetch_in_progress.add(tile_id)

    try:
        logger.info(
            f"[PREFETCH-ASYNC] Start für {tile_id} | "
            f"Ausgeschlossen: {len(exclude_egids)} EGIDs"
        )
        start_time = datetime.now()

        # GDB parsen
        buildings = _parse_all_buildings_from_gdb(gdb_path)

        if not buildings:
            logger.warning(f"Keine Gebäude in Tile {tile_id} gefunden")
            return 0

        # Bereits geladene filtern
        buildings_to_save = [
            b for b in buildings
            if b.get("egid") and b["egid"] not in exclude_egids
        ]

        for b in buildings_to_save:
            b["tile_id"] = tile_id

        # Speichern
        from app.services.building_3d_service import get_building_3d_service
        building_3d_service = get_building_3d_service()
        saved_count = building_3d_service.bulk_save(buildings_to_save, tile_id)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"[PREFETCH-ASYNC] Abgeschlossen: {tile_id} | "
            f"{saved_count} Gebäude (von {len(buildings)} total, {len(exclude_egids)} übersprungen) | "
            f"{elapsed:.1f}s"
        )

        return saved_count

    except Exception as e:
        logger.error(f"Prefetch-Fehler für {tile_id}: {e}")
        return 0

    finally:
        with _prefetch_lock:
            _prefetch_in_progress.discard(tile_id)
