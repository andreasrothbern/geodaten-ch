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
# NEU 14.01.2026: Erweiterte Metriken für vollständige Baseline-Messung
_parsing_metrics: Dict[str, Any] = {
    "last_tile": None,
    "last_building_count": 0,
    "last_parse_time_ms": 0,
    "last_method": None,
}

# Umfassende Timing-Metriken für alle Phasen
# NEU 14.01.2026: Für vollständige Baseline-Messung (BATCH_IMPORT.md)
_import_metrics: Dict[str, Any] = {
    "tile_id": None,
    "timestamp": None,
    # Phase 1: Download
    "download_ms": None,
    "file_size_mb": None,
    # Phase 2: Entpacken
    "unzip_ms": None,
    # Phase 3: Parsing pro Layer
    "parse_building_solid_ms": None,
    "parse_building_solid_count": None,
    "parse_roof_solid_ms": None,
    "parse_roof_solid_count": None,
    "parse_wall_ms": None,
    "parse_wall_count": None,
    # Phase 4: DB-Write
    "db_write_buildings_ms": None,
    "db_write_roofs_ms": None,
    "db_write_walls_ms": None,
    # Gesamt
    "total_ms": None,
    "ms_per_building": None,
}

# Tracking: Welche Tiles werden gerade geprefetcht (verhindert Duplikate)
_prefetch_in_progress: Set[str] = set()
_prefetch_lock = Lock()


async def prefetch_tile_buildings(
    tile_id: str,
    gdb_path: Path,
    exclude_egids: Optional[Set[int]] = None
) -> int:
    """
    Speichert alle Gebäude aus einem Tile in building_3d.db.

    REFACTORED 11.01.2026: exclude_egid → exclude_egids (Set)
    - Vereint prefetch_tile_buildings + prefetch_tile_buildings_excluding
    - Macht IMMER Roof_solid Parsing

    Args:
        tile_id: Tile-Referenz (z.B. "1088-22")
        gdb_path: Pfad zum GDB-Verzeichnis
        exclude_egids: Set von EGIDs die nicht gespeichert werden (bereits geladen)

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

        # GDB parsen - Building_solid
        buildings = _parse_all_buildings_from_gdb(gdb_path)

        if not buildings:
            logger.warning(f"Keine Gebäude in Tile {tile_id} gefunden")
            return 0

        # Gebäude-3D-Service für Speicherung
        from app.services.building_3d_service import get_building_3d_service
        building_3d_service = get_building_3d_service()

        # Gebäude filtern (exclude bereits geladene)
        exclude_egids = exclude_egids or set()
        buildings_to_save = []
        for building in buildings:
            egid = building.get("egid")
            if not egid:
                continue
            if egid in exclude_egids:
                continue

            building["tile_id"] = tile_id
            buildings_to_save.append(building)

        # NEU 11.01.2026: Roof_solid parsen und Dachform berechnen
        # FIX 11.01.2026 22:30: Roofs VOR bulk_save parsen, damit roof_form in buildings landet!
        roofs = _parse_roof_solid_from_gdb(gdb_path)
        roof_count = 0
        if roofs:
            from app.services.roof_3d_service import get_roof_3d_service
            roof_service = get_roof_3d_service()
            roof_count = roof_service.bulk_save(roofs)

            # Dachform in buildings_to_save eintragen BEVOR bulk_save
            _update_buildings_with_roof_data(buildings_to_save, roofs, building_3d_service)

        # NEU 13.01.2026: Wall-Layer parsen wenn IMPORT_ALL_LAYERS aktiv
        from app.config import IMPORT_ALL_LAYERS, CLEANUP_TILES_AFTER_IMPORT
        wall_count = 0
        if IMPORT_ALL_LAYERS:
            walls = _parse_wall_layer_from_gdb(gdb_path)
            if walls:
                wall_count = _save_walls_bulk(walls)
                logger.info(f"[WALL] {wall_count} Wände für Tile {tile_id} gespeichert")

        # Bulk-Save in building_3d.db (jetzt MIT roof_form!)
        saved_count = building_3d_service.bulk_save(buildings_to_save, tile_id)

        # NEU 13.01.2026: has_3d_layers Flag setzen wenn Walls importiert wurden
        if wall_count > 0:
            _update_has_3d_layers_bulk(buildings_to_save)

        # NEU 13.01.2026: Tile-Cleanup nach Import
        if CLEANUP_TILES_AFTER_IMPORT:
            _cleanup_tile_after_import(gdb_path, tile_id)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"[PREFETCH] Abgeschlossen: {tile_id} | "
            f"{saved_count} Gebäude + {roof_count} Dächer + {wall_count} Wände | "
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


def _parse_wall_layer_from_gdb(gdb_path: Path) -> list:
    """
    Parsed Wall Layer für Fassaden-Höhen.

    NEU 13.01.2026: All-Layer-Import - Wall-Geometrie wird beim Prefetch gespeichert.
    Ermöglicht WallFacadeMatcher für präzise Fassaden-Höhen.

    Returns:
        Liste von Wall-Dicts mit egid, gebaeudeeinheit, z_min, z_max, geometry_wkb
    """
    try:
        import fiona
        from shapely.geometry import shape
    except ImportError:
        logger.error("fiona/shapely nicht verfügbar für Wall-Parsing")
        return []

    walls = []
    parse_start = time.time()

    try:
        layers = fiona.listlayers(gdb_path)

        # Wall Layer finden
        target_layer = None
        for layer in layers:
            if 'wall' in layer.lower() and 'solid' not in layer.lower():
                target_layer = layer
                break
            if 'wall' in layer.lower():
                target_layer = layer

        if not target_layer:
            logger.debug(f"Kein Wall Layer in {gdb_path}")
            return []

        with fiona.open(gdb_path, layer=target_layer) as src:
            valid_count = 0

            for feature in src:
                props = feature['properties']
                gebaeudeeinheit = props.get('GEBAEUDEEINHEIT')
                egid = props.get('EGID')

                if not gebaeudeeinheit:
                    continue

                valid_count += 1

                # Geometrie parsen und als WKB speichern
                geometry_wkb = None
                if feature['geometry'] is not None:
                    try:
                        geom = shape(feature['geometry'])
                        geometry_wkb = geom.wkb
                    except Exception as e:
                        logger.debug(f"Wall-Geometrie-Fehler: {e}")
                        continue

                # z_min und z_max berechnen
                # Wall-Layer hat GELAENDEPUNKT (Terrain) und GESAMTHOEHE (Wandhöhe)
                gelaendepunkt = props.get('GELAENDEPUNKT')
                gesamthoehe = props.get('GESAMTHOEHE')

                z_min = float(gelaendepunkt) if gelaendepunkt is not None else None
                z_max = (z_min + float(gesamthoehe)) if z_min is not None and gesamthoehe is not None else None

                walls.append({
                    "gebaeudeeinheit": gebaeudeeinheit,
                    "egid": str(egid) if egid else None,
                    "z_min": z_min,
                    "z_max": z_max,
                    "geometry_wkb": geometry_wkb,
                })

        parse_time_ms = (time.time() - parse_start) * 1000
        if valid_count > 0:
            logger.info(
                f"[WALL] Wall-Layer geparst: {len(walls)} Wände | "
                f"{parse_time_ms:.0f}ms ({parse_time_ms/max(1,len(walls)):.1f}ms/Wand)"
            )

        # NEU 14.01.2026: Import-Metriken für Baseline-Messung aktualisieren
        update_import_metrics(
            parse_wall_ms=parse_time_ms,
            parse_wall_count=len(walls)
        )

        return walls

    except Exception as e:
        logger.error(f"Wall-Layer-Parsing-Fehler: {e}")
        return []


def _parse_roof_solid_from_gdb(gdb_path: Path) -> list:
    """
    Parsed Roof_solid Layer für Dachform-Berechnung.

    NEU 11.01.2026: Extrahiert Z-Levels und berechnet Dachform.
    Geometrie wird NICHT gespeichert (On-Demand für komplexe Gebäude).

    Returns:
        Liste von Dach-Dicts mit gebaeudeeinheit, roof_form, z_levels, etc.
    """
    try:
        import fiona
        from shapely.geometry import shape
    except ImportError:
        logger.error("fiona/shapely nicht verfügbar für Roof-Parsing")
        return []

    from app.services.roof_form_detector import analyze_roof

    roofs = []
    parse_start = time.time()

    try:
        layers = fiona.listlayers(gdb_path)

        # Roof_solid Layer finden
        target_layer = None
        for layer in layers:
            if 'roof' in layer.lower() and 'solid' in layer.lower():
                target_layer = layer
                break

        if not target_layer:
            logger.debug(f"Kein Roof_solid Layer in {gdb_path}")
            return []

        with fiona.open(gdb_path, layer=target_layer) as src:
            valid_count = 0

            for feature in src:
                props = feature['properties']
                gebaeudeeinheit = props.get('GEBAEUDEEINHEIT')

                if not gebaeudeeinheit:
                    continue

                valid_count += 1

                # Geometrie parsen für Z-Level-Analyse
                geom = None
                if feature['geometry'] is not None:
                    try:
                        geom = shape(feature['geometry'])
                    except Exception as e:
                        logger.debug(f"Geometrie-Fehler: {e}")
                        continue

                # Dachform analysieren
                roof_analysis = analyze_roof(geom)

                # OPTIMIERUNG 12.01.2026: geometry_wkb NICHT beim Prefetch speichern
                # Reduziert DB-Grösse von ~280MB auf ~50MB (84% Ersparnis!)
                # Bei komplexen Dächern: On-demand aus GDB nachladen via get_roof_geometry()
                geometry_wkb = None

                roofs.append({
                    "gebaeudeeinheit": gebaeudeeinheit,
                    "egid": props.get('EGID'),
                    "dach_min": props.get('DACH_MIN'),
                    "dach_max": props.get('DACH_MAX'),
                    "roof_form": roof_analysis.get('roof_form'),
                    "roof_angle_deg": roof_analysis.get('angle_deg'),
                    "roof_orientation": roof_analysis.get('orientation'),
                    "roof_form_confidence": roof_analysis.get('confidence'),
                    "z_levels": roof_analysis.get('z_levels'),
                    "calculation_method": "z_level_analysis",
                    "has_full_geometry": 0,  # Immer 0 beim Prefetch (on-demand)
                    "geometry_wkb": None,    # Wird on-demand nachgeladen
                })

        parse_time_ms = (time.time() - parse_start) * 1000
        if valid_count > 0:
            logger.info(
                f"[ROOF] Roof_solid geparst: {len(roofs)} Dächer | "
                f"{parse_time_ms:.0f}ms ({parse_time_ms/len(roofs):.1f}ms/Dach) | "
                f"geometry_wkb=SKIPPED (on-demand)"
            )

        # NEU 14.01.2026: Import-Metriken für Baseline-Messung aktualisieren
        update_import_metrics(
            parse_roof_solid_ms=parse_time_ms,
            parse_roof_solid_count=len(roofs)
        )

        return roofs

    except Exception as e:
        logger.error(f"Roof_solid-Parsing-Fehler: {e}")
        return []


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

                # NEU 11.01.2026: Erweiterte Attribute für 3D-Layer
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
                    # Erweiterte Attribute aus swissBUILDINGS3D 3.0
                    "objektart": props.get('OBJEKTART'),
                    "name_komplett": props.get('NAME_KOMPLETT'),
                    "gebaeude_nutzung": props.get('GEBAEUDE_NUTZUNG'),
                    "gebaeudeeinheit": props.get('GEBAEUDEEINHEIT'),
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

        # NEU 14.01.2026: Import-Metriken für Baseline-Messung aktualisieren
        update_import_metrics(
            parse_building_solid_ms=parse_time_ms,
            parse_building_solid_count=len(buildings)
        )

        return buildings

    except Exception as e:
        logger.error(f"GDB-Parsing-Fehler: {e}")
        return []


def get_parsing_metrics() -> Dict[str, Any]:
    """Gibt die letzten Parsing-Metriken zurück (für Debugging/Monitoring)."""
    return _parsing_metrics.copy()


def get_import_metrics() -> Dict[str, Any]:
    """
    Gibt die vollständigen Import-Metriken zurück.

    NEU 14.01.2026: Für vollständige Baseline-Messung (BATCH_IMPORT.md).
    Enthält Timing für alle Phasen: Download, Unzip, Parse, DB-Write.

    Returns:
        Dict mit allen Metriken. None-Werte bedeuten "nicht gemessen".
    """
    return _import_metrics.copy()


def update_import_metrics(
    tile_id: str = None,
    download_ms: float = None,
    file_size_mb: float = None,
    unzip_ms: float = None,
    parse_building_solid_ms: float = None,
    parse_building_solid_count: int = None,
    parse_roof_solid_ms: float = None,
    parse_roof_solid_count: int = None,
    parse_wall_ms: float = None,
    parse_wall_count: int = None,
    db_write_buildings_ms: float = None,
    db_write_roofs_ms: float = None,
    db_write_walls_ms: float = None,
):
    """
    Aktualisiert die Import-Metriken.

    NEU 14.01.2026: Wird von verschiedenen Stellen aufgerufen (Download, Prefetch).
    Berechnet automatisch total_ms und ms_per_building.

    Args:
        tile_id: Tile-ID für die Messung
        download_ms: Download-Zeit in Millisekunden
        file_size_mb: Dateigrösse in MB
        unzip_ms: Entpack-Zeit in Millisekunden
        parse_*_ms: Parse-Zeit pro Layer
        parse_*_count: Anzahl geparster Elemente
        db_write_*_ms: DB-Schreib-Zeit pro Tabelle
    """
    global _import_metrics
    from datetime import datetime

    if tile_id is not None:
        _import_metrics["tile_id"] = tile_id
        _import_metrics["timestamp"] = datetime.now().isoformat()

    if download_ms is not None:
        _import_metrics["download_ms"] = round(download_ms, 1)
    if file_size_mb is not None:
        _import_metrics["file_size_mb"] = round(file_size_mb, 2)
    if unzip_ms is not None:
        _import_metrics["unzip_ms"] = round(unzip_ms, 1)

    if parse_building_solid_ms is not None:
        _import_metrics["parse_building_solid_ms"] = round(parse_building_solid_ms, 1)
    if parse_building_solid_count is not None:
        _import_metrics["parse_building_solid_count"] = parse_building_solid_count
    if parse_roof_solid_ms is not None:
        _import_metrics["parse_roof_solid_ms"] = round(parse_roof_solid_ms, 1)
    if parse_roof_solid_count is not None:
        _import_metrics["parse_roof_solid_count"] = parse_roof_solid_count
    if parse_wall_ms is not None:
        _import_metrics["parse_wall_ms"] = round(parse_wall_ms, 1)
    if parse_wall_count is not None:
        _import_metrics["parse_wall_count"] = parse_wall_count

    if db_write_buildings_ms is not None:
        _import_metrics["db_write_buildings_ms"] = round(db_write_buildings_ms, 1)
    if db_write_roofs_ms is not None:
        _import_metrics["db_write_roofs_ms"] = round(db_write_roofs_ms, 1)
    if db_write_walls_ms is not None:
        _import_metrics["db_write_walls_ms"] = round(db_write_walls_ms, 1)

    # Automatisch Gesamtzeit und ms/Gebäude berechnen
    total = 0
    for key in ["download_ms", "unzip_ms", "parse_building_solid_ms",
                "parse_roof_solid_ms", "parse_wall_ms",
                "db_write_buildings_ms", "db_write_roofs_ms", "db_write_walls_ms"]:
        val = _import_metrics.get(key)
        if val is not None:
            total += val

    if total > 0:
        _import_metrics["total_ms"] = round(total, 1)

    building_count = _import_metrics.get("parse_building_solid_count")
    if building_count and building_count > 0 and total > 0:
        _import_metrics["ms_per_building"] = round(total / building_count, 2)


def reset_import_metrics():
    """
    Setzt alle Import-Metriken zurück.

    NEU 14.01.2026: Vor einem neuen Tile-Import aufrufen.
    """
    global _import_metrics
    for key in _import_metrics:
        _import_metrics[key] = None


def _update_buildings_with_roof_data(
    buildings: List[Dict[str, Any]],
    roofs: List[Dict[str, Any]],
    building_service
) -> int:
    """
    Aktualisiert buildings_3d mit Dachform aus Roof_solid.

    NEU 11.01.2026: Verknüpft über gebaeudeeinheit oder EGID.
    Speichert roof_form, roof_form_confidence, roof_orientation direkt in buildings_3d
    für schnellen Zugriff ohne Join.

    Args:
        buildings: Liste der Building-Dicts
        roofs: Liste der Roof-Dicts
        building_service: Building3DService für Updates

    Returns:
        Anzahl aktualisierter Gebäude
    """
    if not roofs:
        return 0

    # Index für schnelles Lookup
    roof_by_gebaeudeeinheit = {
        r['gebaeudeeinheit']: r for r in roofs if r.get('gebaeudeeinheit')
    }
    roof_by_egid = {
        str(r['egid']): r for r in roofs if r.get('egid')
    }

    updated = 0
    for building in buildings:
        roof = None

        # Zuerst nach gebaeudeeinheit suchen
        gebaeudeeinheit = building.get('gebaeudeeinheit')
        if gebaeudeeinheit and gebaeudeeinheit in roof_by_gebaeudeeinheit:
            roof = roof_by_gebaeudeeinheit[gebaeudeeinheit]

        # Fallback: nach EGID suchen
        if not roof:
            egid = str(building.get('egid', ''))
            if egid and egid in roof_by_egid:
                roof = roof_by_egid[egid]

        if roof:
            building['roof_form'] = roof.get('roof_form')
            building['roof_form_confidence'] = roof.get('roof_form_confidence')
            building['roof_orientation'] = roof.get('roof_orientation')
            updated += 1

    if updated > 0:
        logger.info(f"[ROOF] {updated} Gebäude mit Dachform-Daten aktualisiert")

    return updated


def schedule_prefetch(tile_id: str, gdb_path: Path, exclude_egid: Optional[str] = None):
    """
    Plant einen Prefetch-Job im Hintergrund.

    Fire-and-forget: Kehrt sofort zurück, Job läuft async.
    REFACTORED 11.01.2026: Konvertiert exclude_egid zu exclude_egids Set.

    Args:
        tile_id: Tile-Referenz
        gdb_path: Pfad zum gecachten GDB
        exclude_egid: EGID die nicht geladen werden soll (Rückwärtskompatibilität)
    """
    # Konvertiere zu Set für neue API
    exclude_egids = {int(exclude_egid)} if exclude_egid else None
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            prefetch_tile_buildings(tile_id, gdb_path, exclude_egids)
        )
        logger.debug(f"Prefetch-Task geplant für {tile_id}")
    except RuntimeError:
        # Kein laufender Event-Loop - synchron starten
        logger.debug(f"Kein Event-Loop, starte Prefetch synchron für {tile_id}")
        asyncio.run(prefetch_tile_buildings(tile_id, gdb_path, exclude_egids))


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

                    # NEU 11.01.2026: Erweiterte Attribute für 3D-Layer
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
                        # Erweiterte Attribute aus swissBUILDINGS3D 3.0
                        "objektart": props.get('OBJEKTART'),
                        "name_komplett": props.get('NAME_KOMPLETT'),
                        "gebaeude_nutzung": props.get('GEBAEUDE_NUTZUNG'),
                        "gebaeudeeinheit": props.get('GEBAEUDEEINHEIT'),
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

    # FIX 12.01.2026: exclude_egids NICHT mehr setzen!
    # Prefetch soll alle Gebäude MIT roof_form speichern, inkl. main_egid und Nachbarn.
    # INSERT OR REPLACE aktualisiert bestehende Einträge mit roof_form.

    # 2. ASYNC: Background-Prefetch für ALLE Gebäude (keine Ausschlüsse mehr)
    # REFACTORED 11.01.2026 21:50: Nutzt jetzt prefetch_tile_buildings (vereint)
    def _background_prefetch():
        """Läuft in separatem Thread."""
        try:
            asyncio.run(prefetch_tile_buildings(
                tile_id=tile_id,
                gdb_path=gdb_path,
                exclude_egids=None  # FIX 12.01.2026: Keine Ausschlüsse mehr
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


# ENTFERNT 11.01.2026 21:50: prefetch_tile_buildings_excluding()
# → Zusammengeführt mit prefetch_tile_buildings() (Zeile 59)
# → exclude_egids Parameter übernommen, Roof_solid Parsing funktioniert jetzt


# =============================================================================
# NEU 13.01.2026: ALL-LAYER-IMPORT HILFSFUNKTIONEN
# =============================================================================

def _save_walls_bulk(walls: List[Dict[str, Any]]) -> int:
    """
    Speichert Wall-Daten in building_walls Tabelle.

    NEU 13.01.2026 19:20: Schema aus building_3d_schema.py verwenden.
    gebaeudeeinheit ist PRIMARY KEY (kein auto-increment id).

    Args:
        walls: Liste von Wall-Dicts aus _parse_wall_layer_from_gdb()

    Returns:
        Anzahl gespeicherter Walls
    """
    if not walls:
        return 0

    start_time = time.time()

    from app.config import get_building_3d_connection, USE_DUCKDB

    conn = get_building_3d_connection()

    try:
        if USE_DUCKDB:
            # FIX 14.01.2026: DuckDB-kompatible Syntax
            for w in walls:
                try:
                    conn.execute("""
                        INSERT INTO building_walls
                        (gebaeudeeinheit, egid, z_min, z_max, geometry_wkb)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (gebaeudeeinheit) DO UPDATE SET
                            egid = excluded.egid,
                            z_min = excluded.z_min,
                            z_max = excluded.z_max,
                            geometry_wkb = excluded.geometry_wkb
                    """, [w['gebaeudeeinheit'], w['egid'], w['z_min'], w['z_max'], w['geometry_wkb']])
                except Exception as e:
                    logger.debug(f"Wall INSERT Fehler für {w['gebaeudeeinheit']}: {e}")
        else:
            # SQLite: executemany mit INSERT OR REPLACE
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO building_walls
                (gebaeudeeinheit, egid, z_min, z_max, geometry_wkb)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (w['gebaeudeeinheit'], w['egid'], w['z_min'], w['z_max'], w['geometry_wkb'])
                for w in walls
            ])
            conn.commit()

        # NEU 14.01.2026: Import-Metriken für Baseline-Messung aktualisieren
        duration_ms = (time.time() - start_time) * 1000
        update_import_metrics(db_write_walls_ms=duration_ms)

        return len(walls)

    except Exception as e:
        logger.error(f"Fehler beim Speichern der Walls: {e}")
        return 0

    finally:
        conn.close()


def _update_has_3d_layers_bulk(buildings: List[Dict[str, Any]]) -> int:
    """
    Setzt has_3d_layers Flag für alle Gebäude im Batch.

    NEU 13.01.2026: Nach Wall-Import das Flag setzen.

    Args:
        buildings: Liste von Building-Dicts mit egid

    Returns:
        Anzahl aktualisierter Gebäude
    """
    if not buildings:
        return 0

    from app.config import get_building_3d_connection, USE_DUCKDB

    egids = [b['egid'] for b in buildings if b.get('egid')]
    if not egids:
        return 0

    conn = get_building_3d_connection()

    try:
        if USE_DUCKDB:
            # FIX 14.01.2026: DuckDB-kompatible Syntax (VALUES + JOIN)
            values_clause = ', '.join([f"({egid})" for egid in egids])
            conn.execute(f"""
                UPDATE buildings_3d
                SET has_3d_layers = 1
                FROM (VALUES {values_clause}) AS t(egid)
                WHERE buildings_3d.egid = t.egid
            """)
        else:
            # SQLite: Standard-Placeholder
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in egids])
            cursor.execute(f"""
                UPDATE buildings_3d
                SET has_3d_layers = 1
                WHERE egid IN ({placeholders})
            """, egids)
            conn.commit()

        logger.info(f"[3D-FLAG] has_3d_layers=1 für {len(egids)} Gebäude gesetzt")
        return len(egids)

    except Exception as e:
        logger.error(f"Fehler beim Setzen von has_3d_layers: {e}")
        return 0

    finally:
        conn.close()


def _cleanup_tile_after_import(gdb_path: Path, tile_id: str):
    """
    Löscht Tile-Verzeichnis nach erfolgreichem Import.

    NEU 13.01.2026: Spart Speicher (~70-80%).

    Args:
        gdb_path: Pfad zum GDB-Verzeichnis
        tile_id: Tile-ID für Logging
    """
    import shutil

    try:
        # gdb_path ist z.B. tiles/2600-1199/swissBUILDINGS3D.gdb
        # Wir wollen das Parent-Verzeichnis löschen: tiles/2600-1199/
        tile_dir = gdb_path.parent if gdb_path.is_dir() else gdb_path.parent

        # Sicherheitscheck: Nur tiles/ Unterverzeichnisse löschen
        if 'tiles' not in str(tile_dir):
            logger.warning(f"[CLEANUP] Skipped: {tile_dir} ist kein tiles-Verzeichnis")
            return

        if tile_dir.exists():
            shutil.rmtree(tile_dir)
            logger.info(f"[CLEANUP] Tile-Verzeichnis gelöscht: {tile_dir}")

        # tiles.db aktualisieren: local_path auf NULL setzen
        from app.services.tile_cache import get_tile_cache
        tile_cache = get_tile_cache()
        tile_cache.mark_tile_cleaned(tile_id)

    except Exception as e:
        logger.error(f"[CLEANUP] Fehler beim Löschen von {gdb_path}: {e}")
