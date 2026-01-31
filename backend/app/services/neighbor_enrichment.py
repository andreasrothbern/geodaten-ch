"""
Neighbor Enrichment: Stufe 2 der 2-Stufen-Architektur (User-Flow).

NEU 18.01.2026: prefetch_neighbors(e, n, radius_m=NEIGHBOR_SEARCH_RADIUS_M)

Laedt das GANZE Tile mit differenziertem Enrichment:
- Enriched (≤radius_m): Building + Roof + Wall + Terrain-Sampling
- Basic (>radius_m): NUR Building Layer (fuer spaetere Lookups)

Architektur:
    prefetch_neighbors(e, n, radius_m)  # Default aus config.py
        |
        v
    GDB einmal oeffnen, Building Layer parsen
        |
        +-- enriched (≤radius_m): + Roof + Wall + Terrain
        +-- basic (>radius_m): nur Building
        |
        v
    Parquet 1 (enriched, sortiert: 5m zuerst)
    Parquet 2 (basic)
        |
        v
    DuckDB Import (Parquet1 zuerst!)
        |
        v
    Cleanup: Parquets + GDB loeschen

HINWEIS: prefetch_tile() ist NUR fuer Batch-Import (scripts/import_tiles.py),
         NICHT fuer den User-Flow!
"""

import asyncio
import json
import logging
import math
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple, Dict, Any

import fiona
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.ops import unary_union

from app.config import get_building_3d_connection, USE_DUCKDB, NEIGHBOR_SEARCH_RADIUS_M

logger = logging.getLogger(__name__)


# =============================================================================
# MAIN FUNCTION: prefetch_neighbors
# =============================================================================

async def prefetch_neighbors(
    e: float,
    n: float,
    radius_m: float = NEIGHBOR_SEARCH_RADIUS_M,
    tile_id: Optional[str] = None,
    gdb_path: Optional[Path] = None,
    exclude_egid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Stufe 2: Laedt das ganze Tile mit differenziertem Enrichment.

    - Enriched (≤radius_m): Building + Roof + Wall + Terrain
    - Basic (>radius_m): NUR Building (fuer spaetere Lookups)

    Die enriched Gebaeude werden nach Distanz sortiert (5m zuerst),
    damit blocked_facades sofort verfuegbar sind.

    Args:
        e: LV95 Easting des Hauptgebaeudes
        n: LV95 Northing des Hauptgebaeudes
        radius_m: Radius fuer Enrichment (default: 100m)
        tile_id: Tile-Referenz (optional, wird aus Koordinaten berechnet)
        gdb_path: Pfad zum GDB-Verzeichnis (optional, wird aus tile_id geladen)
        exclude_egid: EGID des Hauptgebaeudes (wird ausgeschlossen)

    Returns:
        Dict mit Statistiken:
        {
            'enriched_count': int,  # Gebaeude mit vollem Enrichment
            'basic_count': int,     # Gebaeude nur mit Building-Daten
            'total_count': int,     # Gesamt
            'enriched_egids': List[int],
            'elapsed_s': float
        }
    """
    start_time = time.time()
    logger.info(f"[PREFETCH_NEIGHBORS] Start: ({e:.1f}, {n:.1f}) radius={radius_m}m")

    # Tile-ID und GDB-Pfad ermitteln
    if tile_id is None:
        tile_id = _calculate_tile_id(e, n)

    if gdb_path is None:
        gdb_path = await _get_gdb_path_for_coordinates(e, n)
        if gdb_path is None:
            logger.warning("[PREFETCH_NEIGHBORS] Kein GDB-Pfad gefunden")
            return {'enriched_count': 0, 'basic_count': 0, 'total_count': 0, 'enriched_egids': [], 'elapsed_s': 0}

    # 1. Building Layer EINMAL parsen (alle Gebaeude)
    logger.info(f"[PARSE] Building Layer parsen...")
    all_buildings = await asyncio.to_thread(
        _parse_building_layer_all,
        gdb_path=gdb_path,
        tile_id=tile_id,
        exclude_egid=exclude_egid
    )

    if not all_buildings:
        logger.warning("[PREFETCH_NEIGHBORS] Keine Gebaeude im Tile gefunden")
        return {'enriched_count': 0, 'basic_count': 0, 'total_count': 0, 'enriched_egids': [], 'elapsed_s': 0}

    logger.info(f"[PARSE] {len(all_buildings)} Gebaeude im Tile")

    # 2. Nach Distanz aufteilen: enriched (≤radius_m) vs. basic (>radius_m)
    enriched = []
    basic = []

    for b in all_buildings:
        dist = math.sqrt((b['center_e'] - e)**2 + (b['center_n'] - n)**2)
        b['distance_m'] = dist

        if dist <= radius_m:
            enriched.append(b)
        else:
            basic.append(b)

    # 3. Enriched nach Distanz sortieren (5m zuerst fuer blocked_facades)
    enriched.sort(key=lambda b: b['distance_m'])

    logger.info(f"[SPLIT] Enriched: {len(enriched)} (≤{radius_m}m), Basic: {len(basic)} (>{radius_m}m)")

    # 4. Fuer enriched: Roof + Wall Layer parsen
    roofs = []
    walls = []
    if enriched:
        egids_enriched = {b['egid'] for b in enriched}

        logger.info(f"[PARSE] Roof + Wall Layer fuer {len(egids_enriched)} enriched Gebaeude...")
        roofs = await asyncio.to_thread(
            _parse_roof_layer_for_egids, gdb_path, egids_enriched, tile_id
        )
        walls = await asyncio.to_thread(
            _parse_wall_layer_for_egids, gdb_path, egids_enriched, tile_id
        )
        logger.info(f"[PARSE] {len(roofs)} Daecher, {len(walls)} Waende geparst")

    # 5. Parquet-Dateien schreiben
    parquet1_path = None
    parquet2_path = None

    try:
        if enriched:
            parquet1_path = await asyncio.to_thread(
                _write_buildings_parquet, enriched, "enriched"
            )
            logger.info(f"[PARQUET] Enriched: {parquet1_path}")

        if basic:
            parquet2_path = await asyncio.to_thread(
                _write_buildings_parquet, basic, "basic"
            )
            logger.info(f"[PARQUET] Basic: {parquet2_path}")

        # 6. DuckDB Import: Parquet1 (enriched) ZUERST!
        if parquet1_path:
            await asyncio.to_thread(_import_parquet_to_duckdb, parquet1_path, has_3d_layers=True)
            logger.info(f"[DUCKDB] Enriched importiert: {len(enriched)} Gebaeude")

        if parquet2_path:
            await asyncio.to_thread(_import_parquet_to_duckdb, parquet2_path, has_3d_layers=False)
            logger.info(f"[DUCKDB] Basic importiert: {len(basic)} Gebaeude")

        # 7. Roofs + Walls separat speichern (fuer enriched)
        if roofs or walls:
            await asyncio.to_thread(_save_roofs_and_walls, roofs, walls)
            logger.info(f"[DUCKDB] {len(roofs)} Roofs, {len(walls)} Walls gespeichert")

        # 8. Terrain-Sampling NUR fuer enriched
        enriched_egids = [b['egid'] for b in enriched]
        if enriched_egids:
            polygons = {b['egid']: b.get('polygon') for b in enriched}
            terrain_data = await _sample_terrain_for_buildings(enriched_egids, polygons)

            if terrain_data:
                roofs_dict = {r['egid']: r for r in roofs if r.get('egid')}
                await asyncio.to_thread(
                    _update_terrain_and_heights,
                    terrain_data=terrain_data,
                    roofs=roofs_dict
                )

    finally:
        # 9. Cleanup: Parquets loeschen
        if parquet1_path and Path(parquet1_path).exists():
            Path(parquet1_path).unlink()
            logger.debug(f"[CLEANUP] Parquet geloescht: {parquet1_path}")

        if parquet2_path and Path(parquet2_path).exists():
            Path(parquet2_path).unlink()
            logger.debug(f"[CLEANUP] Parquet geloescht: {parquet2_path}")

        # GDB loeschen (mark as cleaned)
        await asyncio.to_thread(_cleanup_gdb, tile_id, gdb_path)

    elapsed = time.time() - start_time
    logger.info(
        f"[PREFETCH_NEIGHBORS] Fertig: {len(enriched)} enriched + {len(basic)} basic = "
        f"{len(all_buildings)} total in {elapsed:.1f}s"
    )

    return {
        'enriched_count': len(enriched),
        'basic_count': len(basic),
        'total_count': len(all_buildings),
        'enriched_egids': enriched_egids,
        'elapsed_s': elapsed
    }


# =============================================================================
# GDB PARSING
# =============================================================================

def _parse_building_layer_all(
    gdb_path: Path,
    tile_id: str,
    exclude_egid: Optional[int] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,  # OPT-006: bbox-Filter
    exclude_egids: Optional[Set[int]] = None  # OPT-006: Multi-EGID exclude
) -> List[Dict]:
    """
    Parsed Building_solid Layer - mit optionalem bbox-Filter.

    Args:
        gdb_path: Pfad zum GDB
        tile_id: Tile-Referenz
        exclude_egid: Einzelne EGID zum Ausschliessen (Legacy)
        bbox: Optional (minx, miny, maxx, maxy) fuer Spatial Filter
        exclude_egids: Set von EGIDs die uebersprungen werden

    Returns:
        Liste von Building-Dicts mit allen Attributen
    """
    buildings = []

    # Merge exclude_egid into exclude_egids Set
    if exclude_egids is None:
        exclude_egids = set()
    if exclude_egid:
        exclude_egids.add(exclude_egid)

    try:
        layers = fiona.listlayers(gdb_path)
        target_layer = None
        for layer in layers:
            if 'building' in layer.lower() and 'solid' in layer.lower():
                target_layer = layer
                break

        if not target_layer:
            logger.warning(f"Kein Building_solid Layer in {gdb_path}")
            return []

        with fiona.open(gdb_path, layer=target_layer) as src:
            # OPT-006 31.01.2026: bbox-Filter fuer 66x Speedup
            if bbox:
                features = src.filter(bbox=bbox)
                logger.debug(f"[PARSE] bbox-Filter aktiv: {bbox}")
            else:
                features = src

            for feature in features:
                try:
                    props = feature.get('properties', {})
                    egid = props.get('EGID')

                    # EGID validieren
                    if egid is None or (isinstance(egid, float) and math.isnan(egid)):
                        continue
                    egid = int(egid)

                    # OPT-006: Skip bereits verarbeitete EGIDs
                    if egid in exclude_egids:
                        continue

                    # Geometrie parsen
                    geom = shape(feature['geometry'])
                    if isinstance(geom, MultiPolygon):
                        geom = unary_union(geom)
                    if not isinstance(geom, Polygon):
                        continue

                    # Zentrum berechnen
                    centroid = geom.centroid
                    geom_e, geom_n = centroid.x, centroid.y

                    # NEU 31.01.2026: Polygon als WKB für DuckDB Spatial
                    from shapely import wkb
                    coords = list(geom.exterior.coords)
                    # 2D Polygon für WKB (Z-Koordinaten entfernen falls vorhanden)
                    polygon_2d = Polygon([(c[0], c[1]) for c in coords])
                    geom_wkb = wkb.dumps(polygon_2d) if polygon_2d.is_valid else None

                    # Hoehen aus Attributen
                    gelaendepunkt = props.get('GELAENDEPUNKT')
                    dach_min = props.get('DACH_MIN')
                    dach_max = props.get('DACH_MAX')
                    gesamthoehe = props.get('GESAMTHOEHE')

                    traufhoehe = None
                    firsthoehe = None
                    if gelaendepunkt and dach_min:
                        traufhoehe = dach_min - gelaendepunkt
                    if gelaendepunkt and dach_max:
                        firsthoehe = dach_max - gelaendepunkt

                    buildings.append({
                        'egid': egid,
                        'geom_wkb': geom_wkb,  # NEU 31.01.2026: WKB statt JSON
                        'traufhoehe_m': traufhoehe,
                        'firsthoehe_m': firsthoehe,
                        'gebaeudehoehe_m': gesamthoehe,
                        'area_m2': geom.area,
                        'perimeter_m': geom.length,
                        'center_e': geom_e,
                        'center_n': geom_n,
                        'tile_id': tile_id,
                        'gebaeudeeinheit': props.get('GEBAEUDEEINHEIT'),
                        'objektart': props.get('OBJEKTART'),
                        'source': 'swissBUILDINGS3D_3.0',
                    })

                except Exception as e:
                    logger.debug(f"Feature-Parsing-Fehler: {e}")
                    continue

    except Exception as e:
        logger.error(f"Building-Layer-Parsing-Fehler: {e}")

    return buildings


def _parse_roof_layer_for_egids(
    gdb_path: Path,
    egids: Set[int],
    tile_id: str
) -> List[Dict]:
    """
    Parsed Roof_solid Layer fuer gegebene EGIDs.
    """
    roofs = []

    try:
        layers = fiona.listlayers(gdb_path)
        target_layer = None
        for layer in layers:
            if 'roof' in layer.lower() and 'solid' in layer.lower():
                target_layer = layer
                break

        if not target_layer:
            return []

        with fiona.open(gdb_path, layer=target_layer) as src:
            for feature in src:
                try:
                    props = feature.get('properties', {})
                    egid = props.get('EGID')

                    if egid is None or (isinstance(egid, float) and math.isnan(egid)):
                        continue
                    egid = int(egid)

                    if egid not in egids:
                        continue

                    roofs.append({
                        'egid': str(egid),
                        'gebaeudeeinheit': props.get('GEBAEUDEEINHEIT'),
                        'dach_min': props.get('DACH_MIN'),
                        'dach_max': props.get('DACH_MAX'),
                        'roof_form': None,
                        'roof_angle_deg': None,
                        'roof_orientation': None,
                        'calculation_method': 'gdb_import',
                        'tile_id': tile_id,
                    })

                except Exception as e:
                    logger.debug(f"Roof-Feature-Fehler: {e}")
                    continue

    except Exception as e:
        logger.error(f"Roof-Layer-Parsing-Fehler: {e}")

    return roofs


def _parse_wall_layer_for_egids(
    gdb_path: Path,
    egids: Set[int],
    tile_id: str
) -> List[Dict]:
    """
    Parsed Wall Layer fuer gegebene EGIDs.
    """
    walls = []

    try:
        layers = fiona.listlayers(gdb_path)
        target_layer = None
        for layer in layers:
            if 'wall' in layer.lower() and 'solid' not in layer.lower():
                target_layer = layer
                break

        if not target_layer:
            return []

        with fiona.open(gdb_path, layer=target_layer) as src:
            for feature in src:
                try:
                    props = feature.get('properties', {})
                    egid = props.get('EGID')

                    if egid is None or (isinstance(egid, float) and math.isnan(egid)):
                        continue
                    egid = int(egid)

                    if egid not in egids:
                        continue

                    # Geometrie als WKB
                    geom = shape(feature['geometry'])
                    geometry_wkb = geom.wkb

                    # Z-Werte aus Geometrie extrahieren
                    z_min, z_max = _extract_z_bounds(geom)

                    walls.append({
                        'egid': str(egid),
                        'gebaeudeeinheit': props.get('GEBAEUDEEINHEIT'),
                        'z_min': z_min,
                        'z_max': z_max,
                        'geometry_wkb': geometry_wkb,
                        'tile_id': tile_id,
                    })

                except Exception as e:
                    logger.debug(f"Wall-Feature-Fehler: {e}")
                    continue

    except Exception as e:
        logger.error(f"Wall-Layer-Parsing-Fehler: {e}")

    return walls


def _extract_z_bounds(geom) -> Tuple[Optional[float], Optional[float]]:
    """
    Extrahiert Z-Min und Z-Max aus einer 3D-Geometrie.
    """
    try:
        coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else []
        if not coords:
            if hasattr(geom, 'geoms'):
                for g in geom.geoms:
                    if hasattr(g, 'exterior'):
                        coords.extend(g.exterior.coords)

        if not coords:
            return None, None

        z_values = [c[2] for c in coords if len(c) > 2]
        if not z_values:
            return None, None

        return min(z_values), max(z_values)

    except Exception:
        return None, None


# =============================================================================
# PARQUET OPERATIONS
# =============================================================================

def _write_buildings_parquet(buildings: List[Dict], prefix: str) -> str:
    """
    Schreibt Buildings in eine Parquet-Datei.

    Args:
        buildings: Liste von Building-Dicts
        prefix: Dateiname-Prefix ("enriched" oder "basic")

    Returns:
        Pfad zur Parquet-Datei
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    # Temporaere Datei erstellen
    temp_dir = tempfile.gettempdir()
    parquet_path = Path(temp_dir) / f"buildings_{prefix}_{int(time.time()*1000)}.parquet"

    # NEU 31.01.2026: geom_wkb (binary) statt polygon (JSON string)
    table = pa.Table.from_pydict({
        'egid': [b['egid'] for b in buildings],
        'geom_wkb': [b.get('geom_wkb') for b in buildings],  # NEU: WKB binary
        'traufhoehe_m': [b.get('traufhoehe_m') for b in buildings],
        'firsthoehe_m': [b.get('firsthoehe_m') for b in buildings],
        'gebaeudehoehe_m': [b.get('gebaeudehoehe_m') for b in buildings],
        'area_m2': [b.get('area_m2') for b in buildings],
        'perimeter_m': [b.get('perimeter_m') for b in buildings],
        'center_e': [b.get('center_e') for b in buildings],
        'center_n': [b.get('center_n') for b in buildings],
        'tile_id': [b.get('tile_id') for b in buildings],
        'gebaeudeeinheit': [b.get('gebaeudeeinheit') for b in buildings],
        'objektart': [b.get('objektart') for b in buildings],
        'source': [b.get('source', 'swissBUILDINGS3D_3.0') for b in buildings],
    })

    # Parquet schreiben
    pq.write_table(table, str(parquet_path))

    return str(parquet_path)


def _import_parquet_to_duckdb(parquet_path: str, has_3d_layers: bool = False) -> int:
    """
    Importiert Parquet-Datei direkt in DuckDB.

    Args:
        parquet_path: Pfad zur Parquet-Datei
        has_3d_layers: True fuer enriched (hat Roof/Wall/Terrain), False fuer basic

    Returns:
        Anzahl importierter Gebaeude
    """
    if not Path(parquet_path).exists():
        return 0

    with get_building_3d_connection() as conn:
        # DuckDB kann Parquet direkt lesen!
        # UPSERT mit has_3d_layers Schutz
        has_3d_value = 1 if has_3d_layers else 0

        # NEU 31.01.2026: geom mit ST_GeomFromWKB statt polygon
        sql = f"""
        INSERT INTO buildings_3d (
            egid, geom, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
            area_m2, perimeter_m, center_e, center_n, tile_id,
            gebaeudeeinheit, objektart, source, has_3d_layers, imported_at
        )
        SELECT
            egid, ST_GeomFromWKB(geom_wkb), traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
            area_m2, perimeter_m, center_e, center_n, tile_id,
            gebaeudeeinheit, objektart, source, {has_3d_value}, now()
        FROM read_parquet('{parquet_path}')
        ON CONFLICT (egid) DO UPDATE SET
            geom = excluded.geom,
            traufhoehe_m = excluded.traufhoehe_m,
            firsthoehe_m = excluded.firsthoehe_m,
            gebaeudehoehe_m = excluded.gebaeudehoehe_m,
            area_m2 = excluded.area_m2,
            perimeter_m = excluded.perimeter_m,
            center_e = excluded.center_e,
            center_n = excluded.center_n,
            tile_id = excluded.tile_id,
            gebaeudeeinheit = excluded.gebaeudeeinheit,
            objektart = excluded.objektart,
            has_3d_layers = CASE
                WHEN buildings_3d.has_3d_layers = 1 THEN 1
                ELSE {has_3d_value}
            END,
            imported_at = now()
        WHERE buildings_3d.has_3d_layers = 0
           OR buildings_3d.has_3d_layers IS NULL
           OR ({has_3d_value} = 1 AND buildings_3d.has_3d_layers = 0)
        """

        result = conn.execute(sql)
        return result.rowcount if hasattr(result, 'rowcount') else 0


def _save_roofs_and_walls(roofs: List[Dict], walls: List[Dict]) -> None:
    """
    Speichert Roof und Wall Daten separat in DuckDB.
    """
    with get_building_3d_connection() as conn:
        # Roofs speichern
        for r in roofs:
            try:
                conn.execute("""
                    INSERT INTO building_roofs (
                        gebaeudeeinheit, egid, dach_min, dach_max, roof_form,
                        roof_angle_deg, roof_orientation, calculation_method, calculated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
                    ON CONFLICT (gebaeudeeinheit) DO UPDATE SET
                        dach_min = excluded.dach_min,
                        dach_max = excluded.dach_max,
                        calculation_method = excluded.calculation_method,
                        calculated_at = current_timestamp
                """, [
                    r.get('gebaeudeeinheit'), r.get('egid'), r.get('dach_min'),
                    r.get('dach_max'), r.get('roof_form'), r.get('roof_angle_deg'),
                    r.get('roof_orientation'), r.get('calculation_method')
                ])
            except Exception as e:
                logger.debug(f"Roof UPSERT Fehler: {e}")

        # Walls speichern
        for w in walls:
            try:
                conn.execute("""
                    INSERT INTO building_walls (
                        gebaeudeeinheit, egid, z_min, z_max, geometry_wkb, created_at
                    ) VALUES (?, ?, ?, ?, ?, current_timestamp)
                    ON CONFLICT (gebaeudeeinheit) DO UPDATE SET
                        z_min = excluded.z_min,
                        z_max = excluded.z_max,
                        geometry_wkb = excluded.geometry_wkb,
                        created_at = current_timestamp
                """, [
                    w.get('gebaeudeeinheit'), w.get('egid'), w.get('z_min'),
                    w.get('z_max'), w.get('geometry_wkb')
                ])
            except Exception as e:
                logger.debug(f"Wall UPSERT Fehler: {e}")


# =============================================================================
# TERRAIN SAMPLING
# =============================================================================

async def _sample_terrain_for_buildings(
    egids: List[int],
    polygons: Dict[int, Any]
) -> Dict[int, Dict]:
    """
    Terrain-Sampling via swissALTI3D fuer alle Gebaeude.

    Sampelt 8 Polygon-Ecken und berechnet terrain_z_min/max/slope_m.
    PARALLELISIERT fuer Performance (NEU 18.01.2026).

    Returns:
        Dict von egid -> terrain_data
    """
    from app.services.terrain import get_terrain_service

    terrain_service = get_terrain_service()

    async def sample_one_building(egid: int) -> Tuple[int, Optional[Dict]]:
        """Sampelt ein Gebaeude - fuer parallele Ausfuehrung."""
        try:
            polygon_json = polygons.get(egid)
            if not polygon_json:
                return egid, None

            # Polygon parsen
            if isinstance(polygon_json, str):
                coords = json.loads(polygon_json)
            else:
                coords = polygon_json

            if not coords or len(coords) < 3:
                return egid, None

            # Max 8 Punkte samplen - PARALLEL pro Gebaeude
            sample_points = coords[:8] if len(coords) > 8 else coords

            async def get_height_safe(point):
                try:
                    return await terrain_service.get_height(point[0], point[1])
                except Exception:
                    return None

            # Alle Punkte eines Gebaeudes parallel samplen
            height_results = await asyncio.gather(
                *[get_height_safe(p) for p in sample_points]
            )
            heights = [h for h in height_results if h is not None]

            if heights:
                terrain_z_min = min(heights)
                terrain_z_max = max(heights)
                terrain_slope_m = terrain_z_max - terrain_z_min

                return egid, {
                    'terrain_z_min': terrain_z_min,
                    'terrain_z_max': terrain_z_max,
                    'terrain_slope_m': terrain_slope_m,
                }

            return egid, None

        except Exception as e:
            logger.debug(f"Terrain-Sampling-Fehler fuer egid={egid}: {e}")
            return egid, None

    # FIX 18.01.2026 - Rate-Limiting ist jetzt in TerrainService (Semaphore 10)
    results = await asyncio.gather(*[sample_one_building(e) for e in egids])

    terrain_data = {egid: data for egid, data in results if data is not None}

    logger.info(f"[TERRAIN] {len(terrain_data)}/{len(egids)} Gebaeude gesampelt (parallel)")
    return terrain_data


def _update_terrain_and_heights(
    terrain_data: Dict[int, Dict],
    roofs: Dict[str, Dict]
) -> int:
    """
    Aktualisiert Terrain-Daten und berechnet korrekte Hoehen.

    traufhoehe = dach_min - terrain_z_min
    firsthoehe = dach_max - terrain_z_min
    """
    updated = 0

    with get_building_3d_connection() as conn:
        for egid, terrain in terrain_data.items():
            try:
                # Dach-Daten holen (falls vorhanden)
                roof = roofs.get(str(egid), {})
                dach_min = roof.get('dach_min')
                dach_max = roof.get('dach_max')

                terrain_z_min = terrain['terrain_z_min']

                # Korrekte Hoehen berechnen
                traufhoehe = None
                firsthoehe = None
                if dach_min and terrain_z_min:
                    traufhoehe = dach_min - terrain_z_min
                if dach_max and terrain_z_min:
                    firsthoehe = dach_max - terrain_z_min

                # DB aktualisieren
                conn.execute("""
                    UPDATE buildings_3d SET
                        terrain_z_min = ?,
                        terrain_z_max = ?,
                        terrain_slope_m = ?,
                        terrain_sampled_at = current_timestamp,
                        traufhoehe_m = COALESCE(?, traufhoehe_m),
                        firsthoehe_m = COALESCE(?, firsthoehe_m)
                    WHERE egid = ?
                """, [
                    terrain['terrain_z_min'],
                    terrain['terrain_z_max'],
                    terrain['terrain_slope_m'],
                    traufhoehe,
                    firsthoehe,
                    egid
                ])
                updated += 1

            except Exception as e:
                logger.debug(f"Terrain-Update-Fehler fuer egid={egid}: {e}")

    logger.info(f"[TERRAIN] {updated} Gebaeude mit Terrain-Daten aktualisiert")
    return updated


# =============================================================================
# CLEANUP
# =============================================================================

def _cleanup_gdb(tile_id: str, gdb_path: Path) -> None:
    """
    Loescht GDB-Verzeichnis und markiert Tile als 'cleaned'.
    """
    from app.services.tile_cache import get_tile_cache
    import shutil

    try:
        # GDB-Verzeichnis loeschen
        if gdb_path and gdb_path.exists():
            shutil.rmtree(gdb_path, ignore_errors=True)
            logger.info(f"[CLEANUP] GDB geloescht: {gdb_path}")

        # Tile als 'cleaned' markieren (via Service-Instanz)
        tile_cache = get_tile_cache()
        tile_cache.mark_tile_cleaned(tile_id)
        logger.info(f"[CLEANUP] Tile {tile_id} als 'cleaned' markiert")

    except Exception as e:
        logger.warning(f"[CLEANUP] Fehler beim Aufraeumen: {e}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _get_gdb_path_for_coordinates(e: float, n: float) -> Optional[Path]:
    """
    Ermittelt GDB-Pfad fuer Koordinaten.
    """
    from app.services.tile_cache import lv95_to_tile_id, get_or_redownload_gdb_path_for_tile

    try:
        tile_id = lv95_to_tile_id(e, n)
        gdb_path = await asyncio.to_thread(get_or_redownload_gdb_path_for_tile, tile_id)
        return Path(gdb_path) if gdb_path else None
    except Exception as e:
        logger.error(f"GDB-Pfad-Ermittlung fehlgeschlagen: {e}")
        return None


def _calculate_tile_id(e: float, n: float) -> str:
    """
    Berechnet Tile-ID aus LV95-Koordinaten.
    """
    from app.services.tile_cache import lv95_to_tile_id
    return lv95_to_tile_id(e, n)


# =============================================================================
# OPT-006 31.01.2026: 3-Stufen Background Prefetch (non-blocking)
# =============================================================================

async def prefetch_3_stages(
    object_egid: int,
    center_e: float,
    center_n: float,
    gdb_path: Path,
    tile_id: str,
    neighbor_radius_m: float = 100.0
) -> Dict[str, Any]:
    """
    DEPRECATED 31.01.2026: Diese Funktion wird nicht mehr verwendet!

    Nutze stattdessen: tile_prefetch.prefetch_and_cleanup()

    Die neue Funktion ist ein schlanker Wrapper um prefetch_tile_buildings_async()
    und wird als asyncio.create_task() Background-Task aufgerufen.

    ---
    Alte Doku (für Referenz):
    3-Stufen Background Prefetch - laeuft NICHT BLOCKIEREND nach User-Antwort.

    Stufe 1: Objekt (bereits durch fetch_building_polygon_for_coordinates erledigt)
    Stufe 2: Nachbarn 100m - bbox-Filter, exclude Objekt
    Stufe 3: Rest des Tiles - kein bbox, exclude alle bisherigen EGIDs
    """
    logger.warning(
        "[DEPRECATED] prefetch_3_stages() wird nicht mehr verwendet! "
        "Nutze tile_prefetch.prefetch_and_cleanup() stattdessen."
    )
    start_time = time.time()
    processed_egids = {object_egid}
    stats = {
        'object_egid': object_egid,
        'neighbors_count': 0,
        'rest_count': 0,
        'total_time_s': 0
    }

    logger.info(f"[PREFETCH_3STAGES] Start: Objekt={object_egid}, Zentrum=({center_e:.1f}, {center_n:.1f})")

    try:
        # =====================================================================
        # STUFE 2: Nachbarn 100m (mit bbox-Filter)
        # =====================================================================
        bbox_neighbors = (
            center_e - neighbor_radius_m,
            center_n - neighbor_radius_m,
            center_e + neighbor_radius_m,
            center_n + neighbor_radius_m
        )

        t1 = time.time()
        neighbors = await asyncio.to_thread(
            _parse_building_layer_all,
            gdb_path=gdb_path,
            tile_id=tile_id,
            bbox=bbox_neighbors,
            exclude_egids=processed_egids
        )
        logger.info(f"[PREFETCH_3STAGES] Stufe 2: {len(neighbors)} Nachbarn in {(time.time()-t1)*1000:.0f}ms")

        if neighbors:
            # Nachbarn nach Distanz sortieren (naechste zuerst)
            for b in neighbors:
                b['distance_m'] = math.sqrt((b['center_e'] - center_e)**2 + (b['center_n'] - center_n)**2)
            neighbors.sort(key=lambda x: x['distance_m'])

            # EGIDs tracken
            neighbor_egids = {b['egid'] for b in neighbors}
            processed_egids.update(neighbor_egids)

            # Roof + Wall fuer Nachbarn laden
            roofs = await asyncio.to_thread(
                _parse_roof_layer_for_egids, gdb_path, neighbor_egids, tile_id
            )
            walls = await asyncio.to_thread(
                _parse_wall_layer_for_egids, gdb_path, neighbor_egids, tile_id
            )

            # Parquet schreiben und importieren
            parquet_neighbors = await asyncio.to_thread(
                _write_buildings_parquet, neighbors, "neighbors"
            )
            if parquet_neighbors:
                await asyncio.to_thread(_import_parquet_to_duckdb, parquet_neighbors, has_3d_layers=True)
                Path(parquet_neighbors).unlink(missing_ok=True)

            if roofs or walls:
                await asyncio.to_thread(_save_roofs_and_walls, roofs, walls)

            stats['neighbors_count'] = len(neighbors)
            logger.info(f"[PREFETCH_3STAGES] Stufe 2 done: {len(neighbors)} Nachbarn gespeichert")

        # =====================================================================
        # STUFE 3: Rest des Tiles (ohne bbox, exclude verarbeitete)
        # =====================================================================
        t2 = time.time()
        rest = await asyncio.to_thread(
            _parse_building_layer_all,
            gdb_path=gdb_path,
            tile_id=tile_id,
            bbox=None,  # Kein bbox = ganzes Tile
            exclude_egids=processed_egids
        )
        logger.info(f"[PREFETCH_3STAGES] Stufe 3: {len(rest)} Rest-Gebaeude in {(time.time()-t2)*1000:.0f}ms")

        if rest:
            # Parquet schreiben und importieren (ohne Roof/Wall fuer Rest)
            parquet_rest = await asyncio.to_thread(
                _write_buildings_parquet, rest, "rest"
            )
            if parquet_rest:
                await asyncio.to_thread(_import_parquet_to_duckdb, parquet_rest, has_3d_layers=False)
                Path(parquet_rest).unlink(missing_ok=True)

            stats['rest_count'] = len(rest)

        # Cleanup: GDB loeschen
        await asyncio.to_thread(_cleanup_gdb, tile_id, gdb_path)

    except Exception as e:
        logger.error(f"[PREFETCH_3STAGES] Fehler: {e}")

    stats['total_time_s'] = time.time() - start_time
    logger.info(
        f"[PREFETCH_3STAGES] Fertig: {stats['neighbors_count']} Nachbarn + "
        f"{stats['rest_count']} Rest in {stats['total_time_s']:.1f}s"
    )

    return stats


def start_background_prefetch(
    object_egid: int,
    center_e: float,
    center_n: float,
    gdb_path: Path,
    tile_id: str,
    neighbor_radius_m: float = 100.0
) -> None:
    """
    DEPRECATED 31.01.2026: Diese Funktion wird nicht mehr verwendet!

    Nutze stattdessen in deinem async Code:
        from tile_prefetch import prefetch_and_cleanup
        asyncio.create_task(prefetch_and_cleanup(tile_id, e, n, skip_egids))

    ---
    Alte Doku (für Referenz):
    Startet den 3-Stufen Prefetch als Fire-and-Forget Background Task.
    """
    logger.warning(
        "[DEPRECATED] start_background_prefetch() wird nicht mehr verwendet! "
        "Nutze asyncio.create_task(tile_prefetch.prefetch_and_cleanup(...)) stattdessen."
    )
    # Funktionalität deaktiviert - tut nichts mehr
    pass
