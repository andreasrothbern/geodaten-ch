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
# NEU 14.01.2026 22:30: Erweiterte Thread-Metriken für Parallelitäts-Analyse
_import_metrics: Dict[str, Any] = {
    "tile_id": None,
    "timestamp": None,
    # Phase 1: Download
    "download_ms": None,
    "file_size_mb": None,
    # Phase 2: Entpacken
    "unzip_ms": None,
    # Phase 3: Parsing pro Layer - mit Start/End für Parallelitäts-Analyse
    "parse_building_solid_ms": None,
    "parse_building_solid_count": None,
    "parse_building_solid_start_ms": None,  # NEU: Relativ zum Gesamt-Start
    "parse_building_solid_end_ms": None,    # NEU: Relativ zum Gesamt-Start
    "parse_roof_solid_ms": None,
    "parse_roof_solid_count": None,
    "parse_roof_solid_start_ms": None,      # NEU
    "parse_roof_solid_end_ms": None,        # NEU
    "parse_wall_ms": None,
    "parse_wall_count": None,
    "parse_wall_start_ms": None,            # NEU
    "parse_wall_end_ms": None,              # NEU
    # Phase 4: DB-Write
    "db_write_buildings_ms": None,
    "db_write_roofs_ms": None,
    "db_write_walls_ms": None,
    # Gesamt
    "total_ms": None,
    "ms_per_building": None,
    # NEU: Parallelitäts-Analyse
    "parallel_efficiency": None,  # 1.0 = perfekt parallel, 0.0 = sequentiell
}

# Tracking: Welche Tiles werden gerade geprefetcht (verhindert Duplikate)
_prefetch_in_progress: Set[str] = set()
_prefetch_lock = Lock()


def prefetch_tile_buildings(
    tile_id: str,
    gdb_path: Path,
    exclude_egids: Optional[Set[int]] = None
) -> int:
    """
    DEPRECATED 17.01.2026: Diese Sync-Version verursacht OOM-Fehler!

    Nutze stattdessen: prefetch_tile_buildings_async() (Parquet-Pipeline)

    Diese Funktion nutzt bulk_save() welches bei grossen Tiles den
    DuckDB Memory-Limit (512MB) überschreitet.

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
    import warnings
    warnings.warn(
        "prefetch_tile_buildings() ist deprecated und verursacht OOM. "
        "Nutze prefetch_tile_buildings_async() mit Parquet-Pipeline.",
        DeprecationWarning,
        stacklevel=2
    )
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

        # NEU 14.01.2026: Gebäude mit has_3d_layers=1 NICHT überschreiben!
        # Diese haben detaillierte 3D-Geometrie die erhalten bleiben muss.
        egids_with_3d_layers = building_3d_service.get_egids_with_3d_layers(tile_id)
        if egids_with_3d_layers:
            exclude_egids = exclude_egids | egids_with_3d_layers
            logger.debug(f"[PREFETCH] Überspringe {len(egids_with_3d_layers)} Gebäude mit 3D-Layern")

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


async def prefetch_tile_buildings_async(
    tile_id: str,
    gdb_path: Path,
    exclude_egids: Optional[Set[int]] = None
) -> int:
    """
    Async-Version: Nutzt Parquet-Pipeline für maximale Performance.

    NEU 15.01.2026 (C.4): Umgestellt auf Parquet-Pipeline:
    - GDB → Parquet (parallel, streaming, kein RAM-Overhead)
    - Parquet → DuckDB (Bulk-Load, SIMD-optimiert)
    - ~2.88x schneller als Listen-basiertes Parsing

    FIX 21.01.2026: Prüft ob Tile bereits importiert (status='imported'/'cleaned').
    Wenn ja, wird der Import übersprungen um unnötige Re-Downloads zu vermeiden.
    Bei Bedarf kann force_reimport=True übergeben werden (noch nicht implementiert).

    VORHER (Listen): 147s für 4901 Gebäude
    NACHHER (Parquet): 51s für 4901 Gebäude

    Args:
        tile_id: Tile-Referenz (z.B. "1088-22")
        gdb_path: Pfad zum GDB-Verzeichnis
        exclude_egids: Set von EGIDs die nicht gespeichert werden (IGNORIERT bei Parquet-Pipeline)

    Returns:
        Anzahl gespeicherter Gebäude
    """
    print(f"[PREFETCH-ENTRY] prefetch_tile_buildings_async aufgerufen für {tile_id}", flush=True)

    # tile_cache für mark_tile_imported() am Ende
    from app.services.tile_cache import get_tile_cache
    tile_cache = get_tile_cache()

    # FIX 21.01.2026: Prüfe ob Tile bereits importiert wurde
    # Wenn ja, überspringen um unnötige Re-Imports zu vermeiden
    # Status-Werte: 'pending', 'imported', 'cleaned', 'reloaded'
    import_status = tile_cache.get_tile_import_status(tile_id)
    if import_status and import_status != 'pending':
        print(f"[PREFETCH-SKIP] {tile_id} bereits importiert (status={import_status}), überspringe", flush=True)
        return 0

    # Check ob bereits ein Prefetch für dieses Tile läuft
    with _prefetch_lock:
        if tile_id in _prefetch_in_progress:
            print(f"[PREFETCH-SKIP] {tile_id} läuft bereits, überspringe", flush=True)
            return 0
        _prefetch_in_progress.add(tile_id)
    print(f"[PREFETCH-LOCK] {tile_id} in _prefetch_in_progress hinzugefügt", flush=True)

    try:
        # ÄNDERUNG 20.01.2026: Wenn GDB nicht existiert, neu herunterladen
        print(f"[PREFETCH-CHECK] gdb_path={gdb_path}, exists={gdb_path.exists() if gdb_path else 'N/A'}", flush=True)
        if not gdb_path or not gdb_path.exists():
            logger.info(f"[PREFETCH-ASYNC] GDB nicht vorhanden, lade Tile {tile_id} neu...")
            from app.services.tile_cache import get_or_redownload_gdb_path_for_tile
            gdb_path = await asyncio.to_thread(get_or_redownload_gdb_path_for_tile, tile_id)
            if not gdb_path or not gdb_path.exists():
                logger.warning(f"[PREFETCH-ASYNC] Konnte GDB für Tile {tile_id} nicht laden")
                return 0

        print(f"[PREFETCH-PIPELINE] Starte Parquet-Pipeline für {tile_id}", flush=True)
        start_time = time.time()

        # =====================================================================
        # NEU 15.01.2026 (C.4): Parquet-Pipeline nutzen
        # =====================================================================
        from app.services.parquet_writer import import_tile_with_parquet_pipeline
        from app.config import CLEANUP_TILES_AFTER_IMPORT

        # Parquet-Pipeline: GDB → Parquet (parallel) → DuckDB (bulk)
        print(f"[PREFETCH-PIPELINE] Rufe import_tile_with_parquet_pipeline auf für {gdb_path}", flush=True)
        result = await import_tile_with_parquet_pipeline(
            gdb_path=gdb_path,
            tile_id=tile_id,
            cleanup_after=True  # Parquet-Dateien nach Load löschen
        )
        print(f"[PREFETCH-PIPELINE] Pipeline abgeschlossen: {result}", flush=True)

        saved_count = result.get('buildings_count', 0)
        roofs_count = result.get('roofs_count', 0)
        walls_count = result.get('walls_count', 0)
        total_ms = result.get('total_ms', 0)

        # Metriken aktualisieren (für Kompatibilität mit get_import_metrics)
        update_import_metrics(
            tile_id=tile_id,
            parse_building_solid_count=saved_count,
            parse_roof_solid_count=roofs_count,
            parse_wall_count=walls_count,
        )

        # FIX 20.01.2026: Tile als 'imported' markieren BEVOR Cleanup entscheidet
        # So wird das Tile bei erneutem Aufruf nicht nochmal geparst.
        tile_cache.mark_tile_imported(tile_id, saved_count)
        logger.debug(f"[PREFETCH-ASYNC] Tile {tile_id} als 'imported' markiert ({saved_count} Gebäude)")

        # =====================================================================
        # Tile-Cleanup (optional - GDB-Dateien löschen)
        # =====================================================================
        # HINWEIS: mark_tile_cleaned() wird in _cleanup_tile_after_import() aufgerufen
        # und überschreibt 'imported' → 'cleaned'
        if CLEANUP_TILES_AFTER_IMPORT:
            await asyncio.to_thread(_cleanup_tile_after_import, gdb_path, tile_id)

        total_elapsed = time.time() - start_time
        logger.info(
            f"[PREFETCH-ASYNC] Parquet-Pipeline abgeschlossen: {tile_id} | "
            f"{saved_count} Gebäude + {roofs_count} Dächer + {walls_count} Wände | "
            f"Total: {total_elapsed:.1f}s (Pipeline: {total_ms:.0f}ms)"
        )

        return saved_count

    except Exception as e:
        print(f"[PREFETCH-ERROR] Fehler für {tile_id}: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        return 0

    finally:
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

                # OPTIMIERUNG 15.01.2026: geometry_wkb NICHT beim Prefetch speichern
                # Reduziert DB-Grösse von ~557MB auf ~308MB (45% Ersparnis!)
                # Wall-Geometrie wird nur für angefragte Gebäude gespeichert
                # via roof_3d_service.fetch_all_layers_on_demand()
                geometry_wkb = None

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
                f"{parse_time_ms:.0f}ms ({parse_time_ms/max(1,len(walls)):.1f}ms/Wand) | "
                f"geometry_wkb=SKIPPED (on-demand)"
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

                # FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
                # Schätzung aus GELAENDEPUNKT (bei Hanglagen ~1-2m ungenau).
                # Für Hauptgebäude erfolgt exakte Berechnung via Terrain-Sampling.
                # Für Nachbarn reicht diese Schätzung für 3D-Visualisierung.
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
    parse_building_solid_start_ms: float = None,  # NEU 14.01.2026 22:30
    parse_building_solid_end_ms: float = None,    # NEU 14.01.2026 22:30
    parse_roof_solid_ms: float = None,
    parse_roof_solid_count: int = None,
    parse_roof_solid_start_ms: float = None,      # NEU 14.01.2026 22:30
    parse_roof_solid_end_ms: float = None,        # NEU 14.01.2026 22:30
    parse_wall_ms: float = None,
    parse_wall_count: int = None,
    parse_wall_start_ms: float = None,            # NEU 14.01.2026 22:30
    parse_wall_end_ms: float = None,              # NEU 14.01.2026 22:30
    db_write_buildings_ms: float = None,
    db_write_roofs_ms: float = None,
    db_write_walls_ms: float = None,
):
    """
    Aktualisiert die Import-Metriken.

    NEU 14.01.2026: Wird von verschiedenen Stellen aufgerufen (Download, Prefetch).
    Berechnet automatisch total_ms und ms_per_building.

    NEU 14.01.2026 22:30: Erweitert um Start/End-Timestamps für Parallelitäts-Analyse.
    Diese Timestamps sind relativ zum Gesamtstart des Imports (in ms).

    Args:
        tile_id: Tile-ID für die Messung
        download_ms: Download-Zeit in Millisekunden
        file_size_mb: Dateigrösse in MB
        unzip_ms: Entpack-Zeit in Millisekunden
        parse_*_ms: Parse-Zeit pro Layer
        parse_*_count: Anzahl geparster Elemente
        parse_*_start_ms: Thread-Startzeit relativ zum Gesamtstart (für Parallelitäts-Analyse)
        parse_*_end_ms: Thread-Endzeit relativ zum Gesamtstart (für Parallelitäts-Analyse)
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

    # NEU 14.01.2026 22:30: Start/End-Timestamps für Parallelitäts-Analyse
    if parse_building_solid_start_ms is not None:
        _import_metrics["parse_building_solid_start_ms"] = round(parse_building_solid_start_ms, 1)
    if parse_building_solid_end_ms is not None:
        _import_metrics["parse_building_solid_end_ms"] = round(parse_building_solid_end_ms, 1)
    if parse_roof_solid_start_ms is not None:
        _import_metrics["parse_roof_solid_start_ms"] = round(parse_roof_solid_start_ms, 1)
    if parse_roof_solid_end_ms is not None:
        _import_metrics["parse_roof_solid_end_ms"] = round(parse_roof_solid_end_ms, 1)
    if parse_wall_start_ms is not None:
        _import_metrics["parse_wall_start_ms"] = round(parse_wall_start_ms, 1)
    if parse_wall_end_ms is not None:
        _import_metrics["parse_wall_end_ms"] = round(parse_wall_end_ms, 1)

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


def _calculate_parallel_efficiency():
    """
    Berechnet die Parallelitäts-Effizienz basierend auf Thread-Timing.

    NEU 14.01.2026 22:30: Analysiert ob die Layer-Parser wirklich parallel liefen.

    Formel:
    - sequential_time = Summe aller individuellen Parse-Zeiten
    - actual_time = Max(End-Zeit) - Min(Start-Zeit) = tatsächlich verstrichene Zeit
    - perfect_parallel_time = Max(einzelne Parse-Zeit) = theoretisch beste parallele Zeit

    - efficiency = (sequential - actual) / (sequential - perfect)
      - 0.0 = komplett sequentiell (actual = sequential)
      - 1.0 = perfekt parallel (actual = perfect)

    Visualisierung der Metriken:
    ```
    t=0ms    Building ████████████████████████████ t=128000ms
    t=0ms    Roof     ████████                     t=20000ms
    t=0ms    Wall     ████████████                 t=30000ms
             |<------ actual_time = 128000ms ----->|
    ```

    Updates:
        _import_metrics["parallel_efficiency"] = berechneter Wert (0.0-1.0)
    """
    global _import_metrics

    # Sammle alle verfügbaren End-Zeiten
    end_times = []
    start_times = []
    parse_durations = []

    # Building_solid
    building_end = _import_metrics.get("parse_building_solid_end_ms")
    building_start = _import_metrics.get("parse_building_solid_start_ms")
    building_ms = _import_metrics.get("parse_building_solid_ms")
    if building_end is not None:
        end_times.append(building_end)
    if building_start is not None:
        start_times.append(building_start)
    if building_ms is not None:
        parse_durations.append(building_ms)

    # Roof_solid
    roof_end = _import_metrics.get("parse_roof_solid_end_ms")
    roof_start = _import_metrics.get("parse_roof_solid_start_ms")
    roof_ms = _import_metrics.get("parse_roof_solid_ms")
    if roof_end is not None:
        end_times.append(roof_end)
    if roof_start is not None:
        start_times.append(roof_start)
    if roof_ms is not None:
        parse_durations.append(roof_ms)

    # Wall
    wall_end = _import_metrics.get("parse_wall_end_ms")
    wall_start = _import_metrics.get("parse_wall_start_ms")
    wall_ms = _import_metrics.get("parse_wall_ms")
    if wall_end is not None:
        end_times.append(wall_end)
    if wall_start is not None:
        start_times.append(wall_start)
    if wall_ms is not None:
        parse_durations.append(wall_ms)

    # Mindestens 2 Threads müssen gemessen worden sein
    if len(end_times) < 2 or len(parse_durations) < 2:
        logger.debug("[PARALLEL] Nicht genug Metriken für Effizienz-Berechnung")
        return

    # Berechnung
    actual_time = max(end_times) - min(start_times) if start_times else max(end_times)
    sequential_time = sum(parse_durations)
    perfect_parallel_time = max(parse_durations)

    # Vermeide Division durch Null
    if sequential_time <= perfect_parallel_time:
        # Keine Parallelisierungsmöglichkeit (nur 1 Task oder alle gleich lang)
        efficiency = 1.0
    elif actual_time <= 0:
        efficiency = 0.0
    else:
        # Effizienz berechnen
        efficiency = (sequential_time - actual_time) / (sequential_time - perfect_parallel_time)
        efficiency = max(0.0, min(1.0, efficiency))  # Clamp auf [0, 1]

    _import_metrics["parallel_efficiency"] = round(efficiency, 3)

    # Logging für Debugging
    logger.info(
        f"[PARALLEL] Effizienz: {efficiency:.1%} | "
        f"Sequentiell: {sequential_time:.0f}ms, Parallel: {actual_time:.0f}ms, "
        f"Optimal: {perfect_parallel_time:.0f}ms"
    )

    # Detailliertes Thread-Timing für Analyse
    if building_start is not None and building_end is not None:
        logger.debug(f"  Building: {building_start:.0f}ms → {building_end:.0f}ms ({building_ms:.0f}ms)")
    if roof_start is not None and roof_end is not None:
        logger.debug(f"  Roof:     {roof_start:.0f}ms → {roof_end:.0f}ms ({roof_ms:.0f}ms)")
    if wall_start is not None and wall_end is not None:
        logger.debug(f"  Wall:     {wall_start:.0f}ms → {wall_end:.0f}ms ({wall_ms:.0f}ms)")


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
    DEPRECATED 17.01.2026: Nutzt sync prefetch_tile_buildings → OOM!

    Nutze stattdessen: schedule_prefetch_with_neighbors() (async, Parquet-Pipeline)

    Plant einen Prefetch-Job im Hintergrund.

    Fire-and-forget: Kehrt sofort zurück, Job läuft in ThreadPool.
    REFACTORED 11.01.2026: Konvertiert exclude_egid zu exclude_egids Set.

    Args:
        tile_id: Tile-Referenz
        gdb_path: Pfad zum gecachten GDB
        exclude_egid: EGID die nicht geladen werden soll (Rückwärtskompatibilität)
    """
    import warnings
    warnings.warn(
        "schedule_prefetch() ist deprecated. "
        "Nutze schedule_prefetch_with_neighbors() (async, Parquet-Pipeline).",
        DeprecationWarning,
        stacklevel=2
    )
    # Konvertiere zu Set für neue API
    exclude_egids = {int(exclude_egid)} if exclude_egid else None

    # FIX 14.01.2026: prefetch_tile_buildings ist sync → in ThreadPool ausführen
    def _run_prefetch():
        prefetch_tile_buildings(tile_id, gdb_path, exclude_egids)

    try:
        _background_executor.submit(_run_prefetch)
        logger.debug(f"Prefetch-Task geplant für {tile_id}")
    except Exception as e:
        logger.error(f"Konnte Prefetch nicht starten: {e}")


def get_prefetch_status() -> dict:
    """Gibt Status der laufenden Prefetch-Jobs zurück."""
    with _prefetch_lock:
        return {
            "in_progress": list(_prefetch_in_progress),
            "count": len(_prefetch_in_progress)
        }


def _find_neighbors_from_db(
    center_e: float,
    center_n: float,
    radius_m: float = 5.0,
    exclude_egid: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Findet Nachbarn aus building_3d.db statt aus GDB.

    NEU 20.01.2026: Fallback wenn GDB bereits gelöscht wurde (CLEANUP_TILES_AFTER_IMPORT=true).
    Die Daten sind in building_3d.db verfügbar weil prefetch_tile_buildings_async()
    ALLE Gebäude speichert BEVOR das Cleanup passiert.

    Args:
        center_e: LV95 Easting des Zentrums
        center_n: LV95 Northing des Zentrums
        radius_m: Suchradius in Metern
        exclude_egid: EGID des Hauptgebäudes (ausschliessen)

    Returns:
        Liste von Nachbar-Gebäuden (Dict mit egid, polygon, höhen, etc.)
    """
    from app.services.building_3d_service import get_building_3d_service
    import json

    start_time = time.time()
    service = get_building_3d_service()

    # SQL-Query für Nachbarn im Radius
    sql = """
        SELECT egid, polygon, center_e, center_n,
               traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
               sqrt((center_e - ?) * (center_e - ?) +
                    (center_n - ?) * (center_n - ?)) as distance_m
        FROM buildings_3d
        WHERE center_e BETWEEN ? AND ?
          AND center_n BETWEEN ? AND ?
    """
    params = [
        center_e, center_e, center_n, center_n,  # für Distanz-Berechnung
        center_e - radius_m, center_e + radius_m,  # BBox E
        center_n - radius_m, center_n + radius_m   # BBox N
    ]

    if exclude_egid:
        sql += " AND egid != ?"
        params.append(exclude_egid)

    sql += " ORDER BY distance_m ASC LIMIT 50"

    neighbors = []
    try:
        with service._get_connection() as conn:
            if hasattr(conn, 'execute'):
                # DuckDB
                result = conn.execute(sql, params).fetchall()
                columns = ['egid', 'polygon', 'center_e', 'center_n',
                          'traufhoehe_m', 'firsthoehe_m', 'gebaeudehoehe_m', 'distance_m']
                rows = [dict(zip(columns, row)) for row in result]
            else:
                # SQLite
                cursor = conn.cursor()
                cursor.execute(sql, params)
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for row in rows:
            dist = row.get('distance_m', 0)
            if dist > radius_m:
                continue

            # Polygon parsen (JSON-String → Liste)
            polygon_raw = row.get('polygon')
            if polygon_raw and isinstance(polygon_raw, str):
                try:
                    row['polygon'] = json.loads(polygon_raw)
                except json.JSONDecodeError:
                    row['polygon'] = None

            neighbors.append({
                'egid': row.get('egid'),
                'polygon': row.get('polygon'),
                'center_e': row.get('center_e'),
                'center_n': row.get('center_n'),
                'traufhoehe_m': row.get('traufhoehe_m'),
                'firsthoehe_m': row.get('firsthoehe_m'),
                'gebaeudehoehe_m': row.get('gebaeudehoehe_m'),
                'distance_m': dist
            })

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[NEIGHBORS-DB] {len(neighbors)} Nachbarn in {radius_m}m Radius aus DB ({elapsed:.0f}ms)")

    except Exception as e:
        logger.error(f"[NEIGHBORS-DB] Fehler beim Laden aus DB: {e}")

    return neighbors


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

    FIX 20.01.2026: Prüft ob GDB-Pfad existiert bevor er geöffnet wird.
    Bei 'cleaned' Tiles existiert das GDB nicht mehr.

    Args:
        gdb_path: Pfad zum GDB-Verzeichnis
        center_e: LV95 Easting des Zentrums
        center_n: LV95 Northing des Zentrums
        radius_m: Suchradius in Metern (default: 5m)
        exclude_egid: EGID des Hauptgebäudes (ausschliessen)

    Returns:
        Liste von Nachbar-Gebäuden (Dict mit egid, polygon, höhen, etc.)
    """
    # FIX 20.01.2026: Wenn GDB nicht existiert, Nachbarn aus DB holen
    # Das Tile wurde bereits importiert (status='cleaned') - Daten sind in building_3d.db
    if not gdb_path or not gdb_path.exists():
        logger.info(f"[NEIGHBORS] GDB existiert nicht - hole Nachbarn aus building_3d.db")
        return _find_neighbors_from_db(center_e, center_n, radius_m, exclude_egid)

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
                    # FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
                    # Schätzung aus GELAENDEPUNKT (wie in _parse_all_buildings_from_gdb)
                    dach_max = props.get('DACH_MAX')
                    dach_min = props.get('DACH_MIN')
                    gelaendepunkt = props.get('GELAENDEPUNKT')
                    gesamthoehe = props.get('GESAMTHOEHE')

                    terrain_f = float(gelaendepunkt) if gelaendepunkt is not None else None
                    dach_max_f = float(dach_max) if dach_max is not None else None
                    dach_min_f = float(dach_min) if dach_min is not None else None
                    gesamt_f = float(gesamthoehe) if gesamthoehe is not None else None

                    # FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
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


async def schedule_prefetch_with_neighbors(
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
    1. ASYNC: Direkte Nachbarn (5m) laden und speichern (in Thread)
    2. ASYNC: Prefetch für restliche Gebäude im Hintergrund (Parquet-Pipeline)

    REFACTORED 17.01.2026: Umgestellt auf async + Parquet-Pipeline
    - Vorher: Sync prefetch_tile_buildings() im Thread → OOM bei grossen Tiles
    - Nachher: Async prefetch_tile_buildings_async() mit Parquet → kein RAM-Overhead

    FIX 20.01.2026: Prüft ZUERST ob Tile bereits importiert wurde oder GDB existiert!
    Wenn Tile bereits importiert, werden Nachbarn aus building_3d.db geholt statt GDB.

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

    # FIX 21.01.2026: Import-Status-Prüfung ist WIEDER aktiv!
    # prefetch_tile_buildings_async() prüft selbst ob Tile schon importiert wurde.
    # Nur wenn status nicht 'imported'/'cleaned' → Import ausführen.
    gdb_exists = gdb_path.exists() if gdb_path else False

    # 1. Direkte Nachbarn laden (in Thread um Event-Loop nicht zu blockieren)
    if center_e and center_n and gdb_exists:
        try:
            immediate_count, neighbor_egids = await asyncio.to_thread(
                load_neighbors_and_save,
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
        except Exception as e:
            logger.warning(f"[IMMEDIATE] Fehler beim Laden der Nachbarn aus GDB: {e}")
            # Nicht kritisch - Nachbarn können später aus DB geholt werden

    # 2. Background-Prefetch mit Parquet-Pipeline (async, fire-and-forget)
    # REFACTORED 17.01.2026: Nutzt jetzt prefetch_tile_buildings_async (Parquet)
    # statt sync prefetch_tile_buildings (DuckDB bulk_save → OOM!)
    # FIX 20.01.2026: prefetch_tile_buildings_async() prüft selbst ob Tile bereits importiert
    try:
        asyncio.create_task(
            prefetch_tile_buildings_async(
                tile_id=tile_id,
                gdb_path=gdb_path,
                exclude_egids=None
            )
        )
        background_started = 1
        logger.info(f"[ASYNC] Parquet-Pipeline Background-Prefetch gestartet für {tile_id}")
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
