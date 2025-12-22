"""
On-Demand Height Fetcher Service
=================================

Fetches building heights from swissBUILDINGS3D on demand.
Uses the STAC API to find tiles based on coordinates, downloads and imports them.
"""

import asyncio
import math
import tempfile
import zipfile
import urllib.request
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import json

import httpx

from app.services.height_db import (
    init_database,
    get_building_height,
    get_building_heights_detailed,
    bulk_insert_heights,
    bulk_insert_heights_detailed,
    log_import,
    get_db_path
)

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
        e: LV95 Easting
        n: LV95 Northing

    Returns:
        STAC item dict with tile info and download URL, or None
    """
    # Convert LV95 to WGS84 for STAC API query
    # Approximation formulas from swisstopo (accurate to ~1m)
    # Reference: https://www.swisstopo.admin.ch/en/knowledge-facts/surveying-geodesy/reference-frames/local/lv95.html
    y = (e - 2600000) / 1000000  # Auxiliary value
    x = (n - 1200000) / 1000000  # Auxiliary value

    lon = (2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x * x - 0.0436 * y * y * y) * 100 / 36
    lat = (16.9023892 + 3.238272 * x - 0.270978 * y * y - 0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x * x * x) * 100 / 36

    print(f"Converted LV95 ({e}, {n}) to WGS84 ({lon:.4f}, {lat:.4f})")

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
            print(f"No tiles found for bbox {bbox}")
            return None

        # Sort by datetime descending to get newest tiles first (they have EGID)
        def get_datetime(f):
            dt = f.get("properties", {}).get("datetime", "")
            return dt if dt else "1900-01-01"

        features = sorted(features, key=get_datetime, reverse=True)
        print(f"Found {len(features)} tiles, sorted by date. First: {features[0].get('id')}")

        # Find the best matching tile (prefer GDB format, newest first)
        for feature in features:
            assets = feature.get("assets", {})
            feature_id = feature.get("id", "")

            # Skip aggregate datasets (they don't have spatial tiles)
            if feature_id in ["swissbuildings3d_3_0_2023", "swissbuildings3d_3_0_2024", "swissbuildings3d_3_0_2025"]:
                print(f"Skipping aggregate dataset: {feature_id}")
                continue

            # Look for GDB asset first
            gdb_asset = None
            for asset_key, asset in assets.items():
                href = asset.get("href", "")
                if ".gdb.zip" in href.lower() or "gdb" in asset_key.lower():
                    gdb_asset = asset
                    break

            if gdb_asset:
                print(f"Selected tile: {feature_id}, URL: {gdb_asset.get('href')}")
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


def parse_gdb_for_heights(gdb_path: Path) -> Tuple[list, list, Dict[str, Any]]:
    """
    Parse a GDB file and extract EGID + height data.

    Args:
        gdb_path: Path to the GDB directory

    Returns:
        Tuple of:
        - list of (egid, height) tuples (legacy format)
        - list of dicts with detailed heights (new format)
        - debug_info dict
    """
    try:
        import geopandas as gpd
        import fiona
    except ImportError:
        raise ImportError("geopandas/fiona is required for GDB parsing")

    heights_legacy = []
    heights_detailed = []
    debug_info = {
        "layers": [],
        "columns": [],
        "total_rows": 0,
        "sample_egids": [],
        "null_egid_count": 0,
        "null_height_count": 0
    }

    try:
        # List available layers
        layers = fiona.listlayers(gdb_path)
        debug_info["layers"] = layers
        print(f"GDB layers: {layers}")

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
            print("No suitable layer found in GDB")
            return heights_legacy, heights_detailed, debug_info

        print(f"Using layer: {target_layer}")

        # Read WITH geometry to calculate heights from 3D coordinates if needed
        gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona')
        debug_info["columns"] = list(gdf.columns)
        debug_info["total_rows"] = len(gdf)
        print(f"Columns: {list(gdf.columns)}")
        print(f"Total rows: {len(gdf)}")

        for _, row in gdf.iterrows():
            egid = row.get('EGID')

            if egid is None:
                debug_info["null_egid_count"] += 1
                continue

            try:
                egid_int = int(egid)
                if egid_int <= 0:
                    continue

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

            except (ValueError, TypeError):
                pass

        print(f"Found {len(heights_legacy)} valid heights, sample EGIDs: {debug_info['sample_egids']}")

    except Exception as e:
        print(f"Error parsing GDB: {e}")
        debug_info["error"] = str(e)

    return heights_legacy, heights_detailed, debug_info


async def fetch_height_for_coordinates(
    e: float,
    n: float,
    egid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch building heights for a location on demand.

    This will:
    1. Find the tile containing the coordinates
    2. Download and parse the tile
    3. Import all heights from the tile into the database
    4. Return the height for the specific EGID if provided

    Args:
        e: LV95 Easting
        n: LV95 Northing
        egid: Optional EGID to look up after import

    Returns:
        Dict with status, count of imported buildings, and optional height
    """
    # Convert LV03 to LV95 if needed
    e, n = ensure_lv95(e, n)

    # Initialize database if needed
    if not get_db_path().exists():
        init_database()

    # Check if we already have COMPLETE detailed heights
    if egid:
        existing_detailed = get_building_heights_detailed(egid)
        if existing_detailed:
            # Check if heights are complete (has trauf or first, not just gebaeudehoehe)
            has_gebaeudehoehe = existing_detailed.get("gebaeudehoehe_m") is not None
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
                    "imported_count": 0
                }
            # Incomplete data - continue to fetch fresh data
            print(f"EGID {egid} has incomplete heights, refreshing from swissBUILDINGS3D")
        else:
            # No detailed heights, check legacy
            existing = get_building_height(egid)
            if existing:
                # Legacy data exists but we want detailed - continue to refresh
                print(f"EGID {egid} has only legacy height, refreshing for detailed data")

    # Find the tile for these coordinates
    tile_info = await find_tile_for_coordinates(e, n)

    if not tile_info:
        return {
            "success": False,
            "status": "no_tile_found",
            "message": f"No swissBUILDINGS3D tile found for coordinates E={e}, N={n}",
            "imported_count": 0
        }

    # Download and parse the tile
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Download
        data_path = download_and_extract_tile(tile_info["download_url"], temp_dir)

        # Parse
        heights_legacy, heights_detailed, debug_info = parse_gdb_for_heights(data_path)

        if not heights_legacy:
            return {
                "success": False,
                "status": "no_heights_found",
                "tile_id": tile_info["id"],
                "message": "Tile downloaded but no building heights found",
                "imported_count": 0,
                "debug": debug_info
            }

        # Import into database (both legacy and detailed)
        source = f"swissBUILDINGS3D_3.0_ondemand_{tile_info['id']}"
        bulk_insert_heights(heights_legacy, source)
        if heights_detailed:
            # Debug: Log what we're storing for the requested EGID
            if egid:
                for h in heights_detailed:
                    if h.get("egid") == egid:
                        print(f"[DEBUG height_fetcher] Storing for EGID {egid}: trauf={h.get('traufhoehe_m')}, first={h.get('firsthoehe_m')}, gebaeude={h.get('gebaeudehoehe_m')}")
                        break
            bulk_insert_heights_detailed(heights_detailed, source)

        # Log the import
        log_import(
            source_file=f"ondemand_{tile_info['id']}",
            canton="ondemand",
            records=len(heights_legacy),
            version="3.0"
        )

        # Look up the requested EGID
        result = {
            "success": True,
            "status": "success",
            "tile_id": tile_info["id"],
            "imported_count": len(heights_legacy),
            "source": source,
            "debug": debug_info
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
                    result["egid"] = egid
                    result["height_found"] = False
                    result["message"] = f"EGID {egid} not found in imported tile"
                    result["sample_egids_in_tile"] = debug_info.get("sample_egids", [])

        return result

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


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
