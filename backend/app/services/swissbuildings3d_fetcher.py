"""
On-Demand Height Fetcher Service
=================================

Fetches building heights from swissBUILDINGS3D on demand.
Uses the STAC API to find tiles based on coordinates, downloads and imports them.

Optimierung (02.01.2026): Tile-Cache System
- Tiles werden persistent gespeichert statt nach jedem Request gelöscht
- EGID → Tile-ID Index für O(1) Lookups
- ~8-15s → ~1ms für gecachte Gebäude
"""

import asyncio
import math
import tempfile
import zipfile
import urllib.request
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import json

import httpx

from app.services.height_db import (
    init_database,
    get_building_height,
    get_building_heights_detailed,
    get_building_height_by_coordinates,
    bulk_insert_heights,
    bulk_insert_heights_detailed,
    bulk_insert_heights_by_coord,
    log_import,
    get_db_path
)
# Polygon simplification is now handled by polygon_simplifier.py
# Imported where needed (on-the-fly)
from app.services.tile_cache import (
    get_tile_cache,
    lv95_to_tile_id,
)
from app.services.tile_prefetch import schedule_prefetch, schedule_prefetch_with_neighbors

logger = logging.getLogger(__name__)

# STAC API base URL
STAC_API_BASE = "https://data.geo.admin.ch/api/stac/v0.9"
COLLECTION_ID = "ch.swisstopo.swissbuildings3d_3_0"


def ensure_lv95(e: float, n: float) -> Tuple[float, float]:
    """
    Ensure coordinates are in LV95 format.

    Detects LV03 coordinates and converts them to LV95.
    LV03: E ~480'000-850'000, N ~70'000-300'000
    LV95: E ~2'480'000-2'850'000, N ~1'070'000-1'300'000

    Args:
        e: Easting coordinate (LV03 or LV95)
        n: Northing coordinate (LV03 or LV95)

    Returns:
        Tuple of (e, n) in LV95 format
    """
    # LV03 coordinates are typically < 1'000'000
    # LV95 coordinates have 2'000'000 added to E and 1'000'000 added to N
    if e < 1_000_000:
        # This is LV03, convert to LV95
        e = e + 2_000_000
        n = n + 1_000_000

    return e, n


def lv95_to_tile_reference(e: float, n: float) -> str:
    """
    Convert LV95 coordinates to swissBUILDINGS3D tile reference.

    The tiles are based on a 1km grid. The tile reference has format:
    XXXX-YY where XXXX is the main tile and YY is the sub-tile (1-4 x 1-4 grid).

    Args:
        e: LV95 Easting (typically 2480000-2850000)
        n: LV95 Northing (typically 1070000-1300000)

    Returns:
        Tile reference string like "1088-22"
    """
    # Remove the 2 prefix from coordinates for calculation
    e_km = int(e / 1000)  # e.g., 2600123 -> 2600
    n_km = int(n / 1000)  # e.g., 1199456 -> 1199

    # Main tile is based on 4km grid (4 sub-tiles per main tile)
    main_e = (e_km - 2480) // 4  # Offset from western border
    main_n = (n_km - 1070) // 4  # Offset from southern border

    # Sub-tile within the 4km main tile (1-4 in each direction)
    sub_e = ((e_km - 2480) % 4) + 1
    sub_n = ((n_km - 1070) % 4) + 1

    # Main tile number (combining E and N)
    main_tile = 1000 + main_e * 10 + main_n

    # Sub-tile (2 digits: row * 10 + col)
    sub_tile = sub_n * 10 + sub_e

    return f"{main_tile}-{sub_tile}"


async def find_tile_for_coordinates(e: float, n: float) -> Optional[Dict[str, Any]]:
    """
    Find the swissBUILDINGS3D tile containing the given coordinates.

    Uses the STAC API spatial query to find intersecting tiles.

    Args:
        e: LV95 or LV03 Easting (auto-converted)
        n: LV95 or LV03 Northing (auto-converted)

    Returns:
        STAC item dict with tile info and download URL, or None
    """
    # Ensure coordinates are in LV95 format (handle LV03 input)
    e, n = ensure_lv95(e, n)

    # Convert LV95 to WGS84 for STAC API query
    # Approximation formulas from swisstopo (accurate to ~1m)
    # Reference: https://www.swisstopo.admin.ch/en/knowledge-facts/surveying-geodesy/reference-frames/local/lv95.html
    y = (e - 2600000) / 1000000  # Auxiliary value
    x = (n - 1200000) / 1000000  # Auxiliary value

    lon = (2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x * x - 0.0436 * y * y * y) * 100 / 36
    lat = (16.9023892 + 3.238272 * x - 0.270978 * y * y - 0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x * x * x) * 100 / 36

    # Use a small bbox around the point
    bbox = f"{lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Query STAC API for items intersecting the bbox
        # Note: Older tiles (2018-2021) may not have EGID, but we still want them for height data
        url = f"{STAC_API_BASE}/collections/{COLLECTION_ID}/items"
        params = {
            "bbox": bbox,
            "limit": 20
            # Removed datetime filter to include all available tiles
        }

        response = await client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        features = data.get("features", [])

        if not features:
            return None

        # Filter tiles that actually contain the point (not just intersect bbox)
        def tile_contains_point(feature, point_lon, point_lat):
            bbox = feature.get("bbox", [])
            if len(bbox) >= 4:
                # bbox format: [west, south, east, north]
                west, south, east, north = bbox[0], bbox[1], bbox[2], bbox[3]
                return west <= point_lon <= east and south <= point_lat <= north
            return True  # If no bbox, assume it might contain the point

        # Filter to tiles that actually contain our point
        containing_features = [f for f in features if tile_contains_point(f, lon, lat)]

        if not containing_features:
            # Fallback to all intersecting tiles if none actually contain the point
            containing_features = features

        # Sort by datetime descending to get newest tiles first (they have EGID)
        def get_datetime(f):
            dt = f.get("properties", {}).get("datetime", "")
            return dt if dt else "1900-01-01"

        containing_features = sorted(containing_features, key=get_datetime, reverse=True)

        # Find the best matching tile (prefer GDB format, newest first)
        for feature in containing_features:
            assets = feature.get("assets", {})
            feature_id = feature.get("id", "")

            # Skip aggregate datasets (they don't have spatial tiles)
            if feature_id in ["swissbuildings3d_3_0_2023", "swissbuildings3d_3_0_2024", "swissbuildings3d_3_0_2025"]:
                continue

            # Look for GDB asset first
            gdb_asset = None
            for asset_key, asset in assets.items():
                href = asset.get("href", "")
                if ".gdb.zip" in href.lower() or "gdb" in asset_key.lower():
                    gdb_asset = asset
                    break

            if gdb_asset:
                return {
                    "id": feature.get("id"),
                    "download_url": gdb_asset.get("href"),
                    "format": "gdb",
                    "bbox": feature.get("bbox"),
                    "properties": feature.get("properties", {})
                }

        # Fallback to first available asset
        for feature in features:
            feature_id = feature.get("id", "")
            if feature_id in ["swissbuildings3d_3_0_2023", "swissbuildings3d_3_0_2024", "swissbuildings3d_3_0_2025"]:
                continue

            assets = feature.get("assets", {})
            for asset in assets.values():
                href = asset.get("href", "")
                if href.endswith(".zip"):
                    return {
                        "id": feature.get("id"),
                        "download_url": href,
                        "format": "gdb" if ".gdb" in href else "gml",
                        "bbox": feature.get("bbox"),
                        "properties": feature.get("properties", {})
                    }

        return None


def download_and_extract_tile(url: str, temp_dir: Path) -> Path:
    """
    Download a tile ZIP and extract it.

    Args:
        url: Download URL for the tile ZIP
        temp_dir: Temporary directory to extract to

    Returns:
        Path to the extracted GDB or GML file
    """
    zip_path = temp_dir / "tile.zip"

    # Download
    urllib.request.urlretrieve(url, zip_path)

    # Extract
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(temp_dir)

    # Find GDB directory
    for f in temp_dir.iterdir():
        if f.is_dir() and f.suffix.lower() == '.gdb':
            return f

    # Find GML file
    for f in temp_dir.glob("*.gml"):
        return f

    raise FileNotFoundError("No GDB or GML found in tile archive")


def parse_gdb_for_heights(gdb_path: Path) -> Tuple[list, list, list, Dict[str, Any]]:
    """
    Parse a GDB file and extract EGID + height data.

    Args:
        gdb_path: Path to the GDB directory

    Returns:
        Tuple of:
        - list of (egid, height) tuples (legacy format)
        - list of dicts with detailed heights (new format, with EGID)
        - list of dicts with coordinate-based heights (without EGID)
        - debug_info dict
    """
    try:
        import geopandas as gpd
        import fiona
    except ImportError:
        raise ImportError("geopandas/fiona is required for GDB parsing")

    heights_legacy = []
    heights_detailed = []
    heights_by_coord = []  # Für Gebäude ohne EGID
    debug_info = {
        "layers": [],
        "columns": [],
        "total_rows": 0,
        "sample_egids": [],
        "null_egid_count": 0,
        "null_height_count": 0,
        "coord_only_count": 0  # Gebäude ohne EGID
    }

    try:
        # List available layers
        layers = fiona.listlayers(gdb_path)
        debug_info["layers"] = layers

        # Try to find the right layer
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
            return heights_legacy, heights_detailed, debug_info

        # Read WITH geometry to calculate heights from 3D coordinates if needed
        gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona')
        debug_info["columns"] = list(gdf.columns)
        debug_info["total_rows"] = len(gdf)

        for _, row in gdf.iterrows():
            egid = row.get('EGID')
            uuid = row.get('UUID')  # swissBUILDINGS3D UUID
            geom = row.get('geometry')

            # Zentroid berechnen für Koordinaten-Lookup
            centroid_e, centroid_n = None, None
            if geom is not None:
                try:
                    centroid = geom.centroid
                    centroid_e = centroid.x
                    centroid_n = centroid.y
                except Exception:
                    pass

            has_egid = egid is not None
            egid_int = None

            if has_egid:
                try:
                    egid_int = int(egid)
                    if egid_int <= 0:
                        has_egid = False
                except (ValueError, TypeError):
                    has_egid = False

            if not has_egid:
                debug_info["null_egid_count"] += 1
                # Weiter verarbeiten für Koordinaten-Lookup (nicht skippen!)

            try:

                # Extract all height values from attributes
                dach_max = row.get('DACH_MAX')
                dach_min = row.get('DACH_MIN')
                gelaendepunkt = row.get('GELAENDEPUNKT')
                gesamthoehe = row.get('GESAMTHOEHE')

                # Convert to floats
                dach_max_f = float(dach_max) if dach_max is not None else None
                dach_min_f = float(dach_min) if dach_min is not None else None
                terrain_f = float(gelaendepunkt) if gelaendepunkt is not None else None
                gesamt_f = float(gesamthoehe) if gesamthoehe is not None else None

                # Calculate relative heights
                traufhoehe = None
                firsthoehe = None
                gebaeudehoehe = gesamt_f

                if terrain_f is not None:
                    if dach_min_f is not None:
                        traufhoehe = round(dach_min_f - terrain_f, 2)
                    if dach_max_f is not None:
                        firsthoehe = round(dach_max_f - terrain_f, 2)

                # If no GESAMTHOEHE, calculate from firsthoehe
                if gebaeudehoehe is None and firsthoehe is not None:
                    gebaeudehoehe = firsthoehe

                # Fallback: Calculate height from 3D geometry (max Z - min Z)
                if gebaeudehoehe is None and firsthoehe is None and traufhoehe is None:
                    geom = row.get('geometry')
                    if geom is not None and hasattr(geom, 'bounds'):
                        try:
                            # Try to get Z values from 3D geometry
                            if hasattr(geom, 'exterior') and hasattr(geom.exterior, 'coords'):
                                z_values = [c[2] for c in geom.exterior.coords if len(c) >= 3]
                                if z_values:
                                    gebaeudehoehe = round(max(z_values) - min(z_values), 2)
                            elif hasattr(geom, 'geoms'):
                                # MultiPolygon or similar
                                z_values = []
                                for g in geom.geoms:
                                    if hasattr(g, 'exterior') and hasattr(g.exterior, 'coords'):
                                        z_values.extend([c[2] for c in g.exterior.coords if len(c) >= 3])
                                if z_values:
                                    gebaeudehoehe = round(max(z_values) - min(z_values), 2)
                                    # Also estimate trauf/first from Z distribution
                                    z_sorted = sorted(set(z_values))
                                    if len(z_sorted) >= 2:
                                        min_z = z_sorted[0]
                                        max_z = z_sorted[-1]
                                        # Traufe is typically the second-highest common Z level
                                        if len(z_sorted) >= 3:
                                            # Estimate traufe as 80% of building height
                                            traufhoehe = round((max_z - min_z) * 0.8, 2)
                                        firsthoehe = gebaeudehoehe
                        except Exception as e:
                            debug_info["geometry_errors"] = debug_info.get("geometry_errors", 0) + 1

                # Validate: at least one valid height
                if gebaeudehoehe is None and firsthoehe is None and traufhoehe is None:
                    debug_info["null_height_count"] += 1
                    continue

                # Select main height (prefer gebaeudehoehe, then firsthoehe, then traufhoehe)
                # Don't use 'or' chain as it fails for 0.0 values
                main_height = None
                if gebaeudehoehe is not None and gebaeudehoehe > 0:
                    main_height = gebaeudehoehe
                elif firsthoehe is not None and firsthoehe > 0:
                    main_height = firsthoehe
                elif traufhoehe is not None and traufhoehe > 0:
                    main_height = traufhoehe

                # Skip if no valid height or NaN
                if main_height is None:
                    debug_info["null_height_count"] += 1
                    continue

                # Check for NaN
                if math.isnan(main_height):
                    debug_info["nan_height_count"] = debug_info.get("nan_height_count", 0) + 1
                    continue

                # Minimum height validation
                if main_height < 2.0:
                    debug_info["rejected_low_height_count"] = debug_info.get("rejected_low_height_count", 0) + 1
                    continue

                # Speichern je nach verfügbaren Identifikatoren
                if has_egid and egid_int:
                    # Legacy format (single height)
                    heights_legacy.append((egid_int, round(main_height, 2)))

                    # Detailed format (all heights)
                    heights_detailed.append({
                        "egid": egid_int,
                        "traufhoehe_m": traufhoehe,
                        "firsthoehe_m": firsthoehe,
                        "gebaeudehoehe_m": round(gebaeudehoehe, 2) if gebaeudehoehe else None,
                        "dach_max_m": round(dach_max_f, 2) if dach_max_f else None,
                        "dach_min_m": round(dach_min_f, 2) if dach_min_f else None,
                        "terrain_m": round(terrain_f, 2) if terrain_f else None
                    })

                    # Collect sample EGIDs
                    if len(debug_info["sample_egids"]) < 10:
                        debug_info["sample_egids"].append(egid_int)

                # Koordinaten-basierter Eintrag (für ALLE Gebäude mit Zentroid)
                if centroid_e is not None and centroid_n is not None:
                    heights_by_coord.append({
                        "lv95_e": round(centroid_e, 1),
                        "lv95_n": round(centroid_n, 1),
                        "uuid": str(uuid) if uuid else None,
                        "traufhoehe_m": traufhoehe,
                        "firsthoehe_m": firsthoehe,
                        "gebaeudehoehe_m": round(gebaeudehoehe, 2) if gebaeudehoehe else None,
                        "dach_max_m": round(dach_max_f, 2) if dach_max_f else None,
                        "dach_min_m": round(dach_min_f, 2) if dach_min_f else None,
                        "terrain_m": round(terrain_f, 2) if terrain_f else None
                    })
                    if not has_egid:
                        debug_info["coord_only_count"] += 1

            except (ValueError, TypeError):
                pass

    except Exception as e:
        debug_info["error"] = str(e)

    return heights_legacy, heights_detailed, heights_by_coord, debug_info


async def fetch_height_for_coordinates(
    e: float,
    n: float,
    egid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch building heights for a location on demand.

    This will:
    1. Find the tile containing the coordinates (or use cache)
    2. Download and parse the tile (if not cached)
    3. Import all heights from the tile into the database
    4. Return the height for the specific EGID if provided

    Optimierung: Verwendet Tile-Cache für persistente Speicherung.

    Args:
        e: LV95 Easting
        n: LV95 Northing
        egid: Optional EGID to look up after import

    Returns:
        Dict with status, count of imported buildings, and optional height
    """
    # Convert LV03 to LV95 if needed
    e, n = ensure_lv95(e, n)

    # Initialize database (creates tables if they don't exist)
    init_database()

    # Check if we already have COMPLETE detailed heights
    if egid:
        existing_detailed = get_building_heights_detailed(egid)
        if existing_detailed:
            # Check if heights are complete (has trauf or first, not just gebaeudehoehe)
            has_trauf_first = (existing_detailed.get("traufhoehe_m") is not None or
                              existing_detailed.get("firsthoehe_m") is not None)

            if has_trauf_first:
                # Complete data - no need to refresh
                return {
                    "success": True,
                    "status": "already_exists",
                    "egid": egid,
                    "height_m": existing_detailed.get("gebaeudehoehe_m") or existing_detailed.get("firsthoehe_m"),
                    "heights": existing_detailed,
                    "source": existing_detailed.get("source"),
                    "imported_count": 0,
                    "cache_hit": True
                }

    # Tile-Cache initialisieren
    tile_cache = get_tile_cache()

    # Tile-ID berechnen (KEIN API-Call!)
    tile_id = lv95_to_tile_id(e, n)

    # Cache-Lookup
    cached_path = tile_cache.get_tile_path(tile_id)
    data_path = None

    if cached_path and cached_path.exists():
        # Cache-Hit
        logger.info(f"Tile-Cache HIT (heights): {tile_id}")
        data_path = cached_path
        cache_hit = True
    else:
        # Cache-Miss: Download
        logger.info(f"Tile-Cache MISS (heights): {tile_id}")
        tile_info = await find_tile_for_coordinates(e, n)

        if not tile_info:
            return {
                "success": False,
                "status": "no_tile_found",
                "message": f"No swissBUILDINGS3D tile found for coordinates E={e}, N={n}",
                "imported_count": 0
            }

        # Download in temporäres Verzeichnis
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Download & Extract
            data_path = download_and_extract_tile(tile_info["download_url"], temp_dir)

            # Im Cache speichern
            bbox = tile_info.get("bbox")
            cached_path = tile_cache.store_tile(
                tile_id=tile_id,
                gdb_path=data_path,
                download_url=tile_info["download_url"],
                bbox=tuple(bbox) if bbox and len(bbox) >= 4 else None
            )
            data_path = cached_path

            # EGID-Registrierung erfolgt via schedule_prefetch() → building_3d.db

        finally:
            # Temporäres Verzeichnis löschen (Cache hat Kopie)
            shutil.rmtree(temp_dir, ignore_errors=True)

        cache_hit = False

    # Parse (aus Cache oder frisch heruntergeladen)
    heights_legacy, heights_detailed, heights_by_coord, debug_info = parse_gdb_for_heights(data_path)

    if not heights_legacy and not heights_by_coord:
        return {
            "success": False,
            "status": "no_heights_found",
            "tile_id": tile_id,
            "message": "Tile downloaded but no building heights found",
            "imported_count": 0,
            "debug": debug_info,
            "cache_hit": cache_hit
        }

    # Import into database (legacy, detailed, and coordinate-based)
    source = f"swissBUILDINGS3D_3.0_ondemand_{tile_id}"
    if heights_legacy:
        bulk_insert_heights(heights_legacy, source)
    if heights_detailed:
        bulk_insert_heights_detailed(heights_detailed, source)
    if heights_by_coord:
        bulk_insert_heights_by_coord(heights_by_coord, source)

    # Log the import
    log_import(
        source_file=f"ondemand_{tile_id}",
        canton="ondemand",
        records=len(heights_legacy),
        version="3.0"
    )

    # Look up the requested EGID
    result = {
        "success": True,
        "status": "success",
        "tile_id": tile_id,
        "imported_count": len(heights_legacy),
        "imported_coord_count": len(heights_by_coord),
        "source": source,
        "debug": debug_info,
        "cache_hit": cache_hit
    }

    if egid:
        # Try detailed heights first
        heights_detail = get_building_heights_detailed(egid)
        if heights_detail:
            result["egid"] = egid
            result["height_m"] = heights_detail.get("gebaeudehoehe_m") or heights_detail.get("firsthoehe_m")
            result["heights"] = heights_detail
            result["height_source"] = heights_detail.get("source")
        else:
            # Fallback to legacy
            height = get_building_height(egid)
            if height:
                result["egid"] = egid
                result["height_m"] = height[0]
                result["height_source"] = height[1]
            else:
                # EGID nicht gefunden - versuche Koordinaten-Lookup
                coord_height = get_building_height_by_coordinates(e, n, tolerance_m=30.0)
                if coord_height:
                    result["egid"] = egid
                    result["height_m"] = coord_height.get("gebaeudehoehe_m") or coord_height.get("firsthoehe_m")
                    result["heights"] = coord_height
                    result["height_source"] = coord_height.get("source")
                    result["lookup_method"] = "coordinate_fallback"
                    result["coord_match_distance_m"] = coord_height.get("distance_m")
                else:
                    result["egid"] = egid
                    result["height_found"] = False
                    result["message"] = f"EGID {egid} not found in imported tile (coord lookup also failed)"
                    result["sample_egids_in_tile"] = debug_info.get("sample_egids", [])

    return result


async def fetch_heights_for_area(
    e: float,
    n: float,
    radius_m: int = 500
) -> Dict[str, Any]:
    """
    Fetch building heights for an area around coordinates.

    This fetches all tiles that might intersect with the given radius.
    Useful for pre-loading heights for a neighborhood.

    Args:
        e: LV95 Easting (center)
        n: LV95 Northing (center)
        radius_m: Radius in meters

    Returns:
        Dict with status and count of imported buildings
    """
    # For now, just fetch the single tile
    # In the future, could expand to fetch multiple tiles for larger areas
    return await fetch_height_for_coordinates(e, n)


async def fetch_building_polygon_for_coordinates(
    e: float,
    n: float,
    tolerance_m: float = 30.0,
    simplify_epsilon: Optional[float] = None,
    skip_prefetch: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Fetch building polygon from swissBUILDINGS3D for given coordinates.

    This replaces geodienste.ch WFS and works for ALL Swiss cantons.

    3-STUFEN LOOKUP:
    1. building_3d.db - Vorverarbeitete Daten (~1ms)
    2. Tile-Cache GDB - Rohdatei parsen (~100-500ms)
    3. STAC Download - Neu laden (~5-10s)

    Args:
        e: LV95 Easting
        n: LV95 Northing
        skip_prefetch: Falls True, wird der Background-Prefetch übersprungen.
                       Nützlich für Address Parser (nur EGID brauchen, Prefetch später).
        tolerance_m: Search radius around the point

    Returns:
        Dict with polygon, sides, perimeter, area, heights or None
    """
    # Ensure coordinates are in LV95 format
    e, n = ensure_lv95(e, n)

    # ========================================
    # STUFE 1: building_3d.db (~1ms)
    # ========================================
    try:
        from app.services.building_3d_service import get_building_3d_service
        building_3d = get_building_3d_service()
        cached_building = building_3d.get_by_coordinates(e, n, tolerance_m)

        if cached_building and cached_building.get('polygon'):
            logger.info(f"[3-STUFEN] Stufe 1 HIT: EGID {cached_building.get('egid')} aus building_3d.db (~1ms)")

            polygon = cached_building['polygon']
            sides = _calculate_polygon_sides(polygon, simplify_epsilon)

            return {
                "egid": cached_building.get('egid'),
                "polygon": polygon,
                "sides": sides,
                "perimeter_m": cached_building.get('perimeter_m'),
                "area_m2": cached_building.get('area_m2'),
                "traufhoehe_m": cached_building.get('traufhoehe_m'),
                "firsthoehe_m": cached_building.get('firsthoehe_m'),
                "gebaeudehoehe_m": cached_building.get('gebaeudehoehe_m'),
                "tile_id": cached_building.get('tile_id'),
                "source": "swissBUILDINGS3D_3.0",
                "cache_hit": True,
                "lookup_level": 1
            }
    except Exception as ex:
        logger.debug(f"[3-STUFEN] Stufe 1 MISS: {ex}")

    # ========================================
    # STUFE 2: Tile-Cache GDB (~100-500ms)
    # ========================================
    tile_cache = get_tile_cache()
    tile_id = lv95_to_tile_id(e, n)
    cached_path = tile_cache.get_tile_path(tile_id)

    if cached_path and cached_path.exists():
        logger.info(f"[3-STUFEN] Stufe 2: Tile {tile_id} - GDB parsen...")
        result = parse_gdb_for_building_polygon(
            cached_path, e, n, tolerance_m, simplify_epsilon
        )

        if result:
            result["tile_id"] = tile_id
            result["source"] = "swissBUILDINGS3D_3.0"
            result["cache_hit"] = True
            result["lookup_level"] = 2

            # In building_3d.db speichern für Stufe 1 beim nächsten Mal
            _save_to_building_3d(result, tile_id)

            # FIX 10.01.2026: Prefetch auch bei Stufe 2 starten
            # (falls building_3d.db noch nicht alle Gebäude enthält)
            # FIX 11.01.2026: skip_prefetch für Address Parser (nur EGID brauchen)
            if not skip_prefetch:
                main_egid = result.get("egid")
                center_e = result.get("coord_e") or e
                center_n = result.get("coord_n") or n

                schedule_prefetch_with_neighbors(
                    tile_id=tile_id,
                    gdb_path=cached_path,
                    center_e=center_e,
                    center_n=center_n,
                    main_egid=int(main_egid) if main_egid else None,
                    immediate_radius_m=5.0
                )

        return result

    # Cache-Miss: Tile herunterladen
    logger.info(f"Tile-Cache MISS: {tile_id} - downloading...")

    # STAC API nur für Download-URL (Tile-ID ist schon bekannt)
    tile_info = await find_tile_for_coordinates(e, n)

    if not tile_info:
        return None

    # Download in temporäres Verzeichnis
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Download & Extract
        data_path = download_and_extract_tile(tile_info["download_url"], temp_dir)

        # Im Cache speichern (kopiert GDB in /app/data/tiles/)
        bbox = tile_info.get("bbox")
        cached_path = tile_cache.store_tile(
            tile_id=tile_id,
            gdb_path=data_path,
            download_url=tile_info["download_url"],
            bbox=tuple(bbox) if bbox and len(bbox) >= 4 else None
        )

        logger.info(f"Tile cached: {tile_id} -> {cached_path}")

        # EGIDs registrieren - ENTFERNT 07.01.2026 (schedule_prefetch ersetzt dies)

        # Parse with polygon extraction
        result = parse_gdb_for_building_polygon(
            cached_path, e, n, tolerance_m, simplify_epsilon
        )

        if result:
            result["tile_id"] = tile_id
            result["source"] = "swissBUILDINGS3D_3.0"
            result["cache_hit"] = False

            # 🔄 NEUE ARCHITEKTUR (10.01.2026): MINIMAL + ON-DEMAND
            # 1. SOFORT: Direkte Nachbarn (5m) laden für blocked_facades
            # 2. ASYNC: Restliche Gebäude im Hintergrund prefetchen
            # FIX 11.01.2026: skip_prefetch für Address Parser (nur EGID brauchen)
            if not skip_prefetch:
                main_egid = result.get("egid")
                center_e = result.get("coord_e") or e
                center_n = result.get("coord_n") or n

                immediate_count, background_started = schedule_prefetch_with_neighbors(
                    tile_id=tile_id,
                    gdb_path=cached_path,
                    center_e=center_e,
                    center_n=center_n,
                    main_egid=int(main_egid) if main_egid else None,
                    immediate_radius_m=5.0  # 5m Radius für blocked_facades
                )

                result["immediate_neighbors_loaded"] = immediate_count
                result["background_prefetch_started"] = bool(background_started)
            else:
                result["immediate_neighbors_loaded"] = 0
                result["background_prefetch_started"] = False

        return result

    except Exception as ex:
        logger.error(f"[EGID-LOOKUP] GDB-Fehler: {ex}")
        return None

    finally:
        # Temporäres Verzeichnis löschen (Cache hat Kopie)
        shutil.rmtree(temp_dir, ignore_errors=True)


def parse_gdb_for_building_polygon(
    gdb_path: Path,
    target_e: float,
    target_n: float,
    tolerance_m: float = 30.0,
    simplify_epsilon: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Parse GDB and find the building polygon closest to target coordinates.

    Args:
        gdb_path: Path to GDB directory
        target_e: Target LV95 Easting
        target_n: Target LV95 Northing
        tolerance_m: Maximum distance to consider a match
        simplify_epsilon: Optional Douglas-Peucker epsilon for polygon simplification

    Returns:
        Dict with polygon, sides, heights, etc. or None
    """
    try:
        import geopandas as gpd
        import fiona
        from shapely.geometry import Point
        from shapely.ops import transform
    except ImportError:
        raise ImportError("geopandas/fiona/shapely required for polygon parsing")

    try:
        # List available layers
        layers = fiona.listlayers(gdb_path)

        # Find building layer
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
            return None

        # Read with geometry
        gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona')

        # Create target point
        target_point = Point(target_e, target_n)

        # BUG-015 FIX 11.01.2026: Point-in-Polygon hat Priorität!
        # Bei Reihenhäusern liegt der Hauseingang (Geocoding-Koordinate) oft
        # näher am Nachbar-Zentrum als am eigenen Gebäude-Zentrum.
        #
        # Strategie:
        # 1. ERST: Point-in-Polygon Check (Punkt liegt IM Gebäude)
        # 2. FALLBACK: Nächstes Zentrum (wie bisher, wenn kein Polygon-Match)

        point_in_polygon_match = None
        best_distance_match = None
        best_distance = float('inf')

        for _, row in gdf.iterrows():
            geom = row.get('geometry')
            if geom is None:
                continue

            try:
                # Get 2D footprint (project to XY plane)
                # swissBUILDINGS3D has 3D geometries - we need the 2D footprint
                if hasattr(geom, 'geoms'):
                    # MultiPolygon - find the largest/main polygon
                    all_coords_2d = []
                    for g in geom.geoms:
                        if hasattr(g, 'exterior'):
                            coords = [(c[0], c[1]) for c in g.exterior.coords]
                            all_coords_2d.extend(coords)
                    if not all_coords_2d:
                        continue
                    # Use convex hull of all points as approximation
                    from shapely.geometry import MultiPoint, Polygon
                    hull = MultiPoint(all_coords_2d).convex_hull
                    footprint = hull
                elif hasattr(geom, 'exterior'):
                    # Single Polygon
                    coords_2d = [(c[0], c[1]) for c in geom.exterior.coords]
                    from shapely.geometry import Polygon
                    footprint = Polygon(coords_2d)
                else:
                    continue

                # BUG-015 FIX: Point-in-Polygon Check ZUERST
                if footprint.contains(target_point):
                    egid = row.get('EGID', 'unknown')
                    logger.info(f"[BUG-015 FIX] Point-in-Polygon Match: ({target_e:.1f}, {target_n:.1f}) → EGID {egid}")
                    point_in_polygon_match = {
                        "geometry": footprint,
                        "row": row
                    }
                    break  # Gefunden! Keine weitere Suche nötig.

                # Fallback: Distance-basierte Suche (wie bisher)
                distance = footprint.centroid.distance(target_point)

                if distance < tolerance_m and distance < best_distance:
                    best_distance = distance
                    best_distance_match = {
                        "geometry": footprint,
                        "row": row
                    }

            except Exception:
                continue

        # Priorität: Point-in-Polygon > Distance
        best_match = point_in_polygon_match or best_distance_match

        if best_match and not point_in_polygon_match and best_distance_match:
            egid = best_distance_match["row"].get('EGID', 'unknown')
            logger.warning(
                f"[BUG-015] Kein Polygon-Match für ({target_e:.1f}, {target_n:.1f}). "
                f"Fallback auf nächstes Zentrum: EGID {egid} (dist={best_distance:.1f}m)"
            )

        if not best_match:
            return None

        # Extract polygon coordinates
        footprint = best_match["geometry"]
        row = best_match["row"]

        # Get exterior coordinates as list
        if hasattr(footprint, 'exterior'):
            polygon_coords = list(footprint.exterior.coords)
        elif hasattr(footprint, 'coords'):
            polygon_coords = list(footprint.coords)
        else:
            return None

        # Round coordinates - this is the ORIGINAL polygon
        polygon_coords = [[round(c[0], 2), round(c[1], 2)] for c in polygon_coords]
        polygon_point_count = len(polygon_coords)

        # On-the-fly simplification for sides calculation (not stored)
        # The original polygon is always returned
        from app.services.polygon_simplifier import simplify_building_polygon
        simplification = simplify_building_polygon(
            polygon_coords,
            epsilon=simplify_epsilon,  # None = dynamic epsilon based on building size
            use_dynamic_epsilon=(simplify_epsilon is None)
        )

        # Use simplified polygon for sides (better for scaffolding planning)
        sides = simplification.sides
        perimeter = simplification.perimeter_m

        # Area from original geometry
        area = abs(footprint.area) if hasattr(footprint, 'area') else 0

        # Extract heights from row
        dach_max = row.get('DACH_MAX')
        dach_min = row.get('DACH_MIN')
        gelaendepunkt = row.get('GELAENDEPUNKT')
        gesamthoehe = row.get('GESAMTHOEHE')
        egid = row.get('EGID')

        # Calculate heights
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

        return {
            # Polygon is ALWAYS the original from swissBUILDINGS3D
            "polygon": polygon_coords,
            "polygon_point_count": polygon_point_count,
            # Sides are calculated from on-the-fly simplified polygon
            "sides": sides,
            "sides_from_simplified": True,  # Flag: sides are from simplified polygon
            "polygon_simplified_point_count": simplification.simplified_point_count,
            "perimeter_m": round(perimeter, 2),
            "area_m2": round(area, 2),
            "egid": int(egid) if egid else None,
            "traufhoehe_m": traufhoehe,
            "firsthoehe_m": firsthoehe,
            "gebaeudehoehe_m": round(gesamt_f, 2) if gesamt_f else (firsthoehe or traufhoehe),
            "terrain_m": round(terrain_f, 2) if terrain_f else None,
            "match_distance_m": round(best_distance, 2)
        }

    except Exception as e:
        import logging
        logging.error(f"Error parsing GDB for polygon: {e}")
        return None


def _calculate_polygon_sides(polygon: List[List[float]], simplify_epsilon: Optional[float] = None) -> List[Dict]:
    """
    Berechnet Fassaden-Seiten aus Polygon.

    Args:
        polygon: Liste von [e, n] Koordinaten
        simplify_epsilon: Optional Vereinfachungs-Toleranz

    Returns:
        Liste von Seiten-Dicts mit Länge, Azimut, Richtung
    """
    if not polygon or len(polygon) < 3:
        return []

    try:
        from app.services.polygon_simplifier import simplify_building_polygon
        simplification = simplify_building_polygon(
            polygon,
            epsilon=simplify_epsilon,
            use_dynamic_epsilon=(simplify_epsilon is None)
        )
        return simplification.sides
    except Exception as e:
        logger.warning(f"Polygon-Sides Berechnung fehlgeschlagen: {e}")
        return []


def _save_to_building_3d(result: Dict[str, Any], tile_id: str = None):
    """
    Speichert Gebäude in building_3d.db für Stufe 1 Lookup.

    Args:
        result: Dict mit Polygon, Höhen, etc. aus GDB-Parsing
        tile_id: Tile-Referenz
    """
    try:
        from app.services.building_3d_service import get_building_3d_service
        building_3d = get_building_3d_service()

        egid = result.get('egid')
        if not egid:
            return

        # Zentroid berechnen
        polygon = result.get('polygon')
        center_e, center_n = None, None
        if polygon and len(polygon) > 0:
            center_e = sum(p[0] for p in polygon) / len(polygon)
            center_n = sum(p[1] for p in polygon) / len(polygon)

        building_3d.save({
            'egid': egid,
            'polygon': polygon,
            'traufhoehe_m': result.get('traufhoehe_m'),
            'firsthoehe_m': result.get('firsthoehe_m'),
            'gebaeudehoehe_m': result.get('gebaeudehoehe_m'),
            'area_m2': result.get('area_m2'),
            'perimeter_m': result.get('perimeter_m'),
            'center_e': center_e,
            'center_n': center_n,
            'tile_id': tile_id,
            'source': 'swissBUILDINGS3D_3.0'
        })

        logger.debug(f"EGID {egid} in building_3d.db gespeichert")

    except Exception as e:
        logger.warning(f"Konnte Gebäude nicht in building_3d.db speichern: {e}")


def _azimuth_to_direction(azimuth: float) -> str:
    """Convert azimuth (0-360) to cardinal/ordinal direction."""
    # Normalize to 0-360
    azimuth = azimuth % 360

    # Define direction ranges (N is centered at 0/360)
    if azimuth >= 337.5 or azimuth < 22.5:
        return "N"
    elif azimuth < 67.5:
        return "NE"
    elif azimuth < 112.5:
        return "E"
    elif azimuth < 157.5:
        return "SE"
    elif azimuth < 202.5:
        return "S"
    elif azimuth < 247.5:
        return "SW"
    elif azimuth < 292.5:
        return "W"
    else:
        return "NW"


async def fetch_building_complex_for_coordinates(
    e: float,
    n: float,
    radius_m: float = 50.0,
    include_main_only: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Fetch ALL buildings within radius from swissBUILDINGS3D.

    Use this for building complexes like churches (main building + tower).

    Optimierung: Verwendet Tile-Cache für persistente Speicherung.

    Args:
        e: LV95 Easting
        n: LV95 Northing
        radius_m: Search radius (default 50m for complexes)
        include_main_only: If True, only return the main (closest) building

    Returns:
        Dict with:
        - main_building: The closest building (always present)
        - adjacent_buildings: List of other buildings within radius
        - combined_polygon: Convex hull of all buildings (optional)
    """
    # Ensure coordinates are in LV95 format
    e, n = ensure_lv95(e, n)

    # Tile-Cache initialisieren
    tile_cache = get_tile_cache()

    # Tile-ID berechnen (KEIN API-Call!)
    tile_id = lv95_to_tile_id(e, n)

    # Cache-Lookup
    cached_path = tile_cache.get_tile_path(tile_id)

    if cached_path and cached_path.exists():
        # Cache-Hit
        logger.info(f"Tile-Cache HIT (complex): {tile_id}")
        result = parse_gdb_for_building_complex(
            cached_path, e, n, radius_m, include_main_only
        )

        if result:
            result["tile_id"] = tile_id
            result["source"] = "swissBUILDINGS3D_3.0"
            result["cache_hit"] = True

        return result

    # Cache-Miss: Download
    logger.info(f"Tile-Cache MISS (complex): {tile_id}")
    tile_info = await find_tile_for_coordinates(e, n)

    if not tile_info:
        return None

    # Download in temporäres Verzeichnis
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Download
        data_path = download_and_extract_tile(tile_info["download_url"], temp_dir)

        # Im Cache speichern
        bbox = tile_info.get("bbox")
        cached_path = tile_cache.store_tile(
            tile_id=tile_id,
            gdb_path=data_path,
            download_url=tile_info["download_url"],
            bbox=tuple(bbox) if bbox and len(bbox) >= 4 else None
        )

        # EGIDs registrieren - ENTFERNT 07.01.2026 (schedule_prefetch ersetzt dies)

        # Parse with multi-building extraction
        result = parse_gdb_for_building_complex(
            cached_path, e, n, radius_m, include_main_only
        )

        if result:
            result["tile_id"] = tile_id
            result["source"] = "swissBUILDINGS3D_3.0"
            result["cache_hit"] = False

        return result

    finally:
        # Temporäres Verzeichnis löschen (Cache hat Kopie)
        shutil.rmtree(temp_dir, ignore_errors=True)


def parse_gdb_for_building_complex(
    gdb_path: Path,
    target_e: float,
    target_n: float,
    radius_m: float = 50.0,
    include_main_only: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Parse GDB and find ALL buildings within radius of target coordinates.

    Args:
        gdb_path: Path to GDB directory
        target_e: Target LV95 Easting
        target_n: Target LV95 Northing
        radius_m: Maximum distance to include buildings
        include_main_only: If True, only return the main building

    Returns:
        Dict with main_building, adjacent_buildings, and optionally combined data
    """
    try:
        import geopandas as gpd
        import fiona
        from shapely.geometry import Point, MultiPolygon
        from shapely.ops import unary_union
    except ImportError:
        raise ImportError("geopandas/fiona/shapely required for polygon parsing")

    try:
        # List available layers
        layers = fiona.listlayers(gdb_path)

        # Find building layer
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
            return None

        # Read with geometry
        gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona')

        # Create target point
        target_point = Point(target_e, target_n)

        # Find ALL buildings within radius
        buildings_found = []

        for _, row in gdf.iterrows():
            geom = row.get('geometry')
            if geom is None:
                continue

            try:
                # Get 2D footprint
                if hasattr(geom, 'geoms'):
                    all_coords_2d = []
                    for g in geom.geoms:
                        if hasattr(g, 'exterior'):
                            coords = [(c[0], c[1]) for c in g.exterior.coords]
                            all_coords_2d.extend(coords)
                    if not all_coords_2d:
                        continue
                    from shapely.geometry import MultiPoint, Polygon
                    hull = MultiPoint(all_coords_2d).convex_hull
                    footprint = hull
                elif hasattr(geom, 'exterior'):
                    coords_2d = [(c[0], c[1]) for c in geom.exterior.coords]
                    from shapely.geometry import Polygon
                    footprint = Polygon(coords_2d)
                else:
                    continue

                # Calculate distance
                distance = footprint.centroid.distance(target_point)

                if distance <= radius_m:
                    # Extract building data
                    building_data = _extract_building_data(footprint, row, distance)
                    buildings_found.append(building_data)

            except Exception:
                continue

        if not buildings_found:
            return None

        # Sort by distance (closest first = main building)
        buildings_found.sort(key=lambda b: b["match_distance_m"])

        main_building = buildings_found[0]
        adjacent_buildings = buildings_found[1:] if len(buildings_found) > 1 else []

        result = {
            "main_building": main_building,
            "adjacent_buildings": adjacent_buildings,
            "total_buildings": len(buildings_found),
            "search_radius_m": radius_m
        }

        # Also provide the main building data at top level for backwards compatibility
        for key, value in main_building.items():
            if key not in result:
                result[key] = value

        # Create combined polygon if multiple buildings
        if adjacent_buildings and not include_main_only:
            try:
                all_polygons = []
                for b in buildings_found:
                    if b.get("polygon"):
                        from shapely.geometry import Polygon
                        coords = [(p[0], p[1]) for p in b["polygon"]]
                        all_polygons.append(Polygon(coords))

                if all_polygons:
                    combined = unary_union(all_polygons)
                    if hasattr(combined, 'exterior'):
                        result["combined_polygon"] = [
                            [round(c[0], 2), round(c[1], 2)]
                            for c in combined.exterior.coords
                        ]
                    elif hasattr(combined, 'convex_hull'):
                        hull = combined.convex_hull
                        if hasattr(hull, 'exterior'):
                            result["combined_polygon"] = [
                                [round(c[0], 2), round(c[1], 2)]
                                for c in hull.exterior.coords
                            ]

                    # Combined stats
                    result["combined_area_m2"] = round(sum(b.get("area_m2", 0) for b in buildings_found), 2)
                    result["combined_perimeter_m"] = round(sum(b.get("perimeter_m", 0) for b in buildings_found), 2)

            except Exception as e:
                import logging
                logging.warning(f"Could not create combined polygon: {e}")

        return result

    except Exception as e:
        import logging
        logging.error(f"Error parsing GDB for building complex: {e}")
        return None


def _extract_building_data(footprint, row, distance: float) -> Dict[str, Any]:
    """Extract building data from footprint and row."""
    # Get exterior coordinates
    if hasattr(footprint, 'exterior'):
        polygon_coords = list(footprint.exterior.coords)
    elif hasattr(footprint, 'coords'):
        polygon_coords = list(footprint.coords)
    else:
        polygon_coords = []

    # Round coordinates - this is the ORIGINAL polygon
    polygon_coords = [[round(c[0], 2), round(c[1], 2)] for c in polygon_coords]
    polygon_point_count = len(polygon_coords)

    # On-the-fly simplification for sides calculation (not stored)
    from app.services.polygon_simplifier import simplify_building_polygon
    simplification = simplify_building_polygon(polygon_coords)

    # Use simplified polygon for sides (better for scaffolding planning)
    sides = simplification.sides
    perimeter = simplification.perimeter_m

    # Area from original geometry
    area = abs(footprint.area) if hasattr(footprint, 'area') else 0

    # Extract heights
    dach_max = row.get('DACH_MAX')
    dach_min = row.get('DACH_MIN')
    gelaendepunkt = row.get('GELAENDEPUNKT')
    gesamthoehe = row.get('GESAMTHOEHE')
    egid = row.get('EGID')

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

    # Classify building type based on height ratio
    building_type = "hauptgebaeude"
    if firsthoehe and traufhoehe:
        height_ratio = firsthoehe / traufhoehe if traufhoehe > 0 else 1
        if height_ratio > 3:
            building_type = "turm"
        elif area < 50:
            building_type = "nebengebaeude"

    return {
        # Polygon is ALWAYS the original from swissBUILDINGS3D
        "polygon": polygon_coords,
        "polygon_point_count": polygon_point_count,
        # Sides are calculated from on-the-fly simplified polygon
        "sides": sides,
        "sides_from_simplified": True,
        "polygon_simplified_point_count": simplification.simplified_point_count,
        "perimeter_m": round(perimeter, 2),
        "area_m2": round(area, 2),
        "egid": int(egid) if egid else None,
        "traufhoehe_m": traufhoehe,
        "firsthoehe_m": firsthoehe,
        "gebaeudehoehe_m": round(gesamt_f, 2) if gesamt_f else (firsthoehe or traufhoehe),
        "terrain_m": round(terrain_f, 2) if terrain_f else None,
        "match_distance_m": round(distance, 2),
        "building_type": building_type
    }
