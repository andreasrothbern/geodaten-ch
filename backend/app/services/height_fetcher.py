"""
On-Demand Height Fetcher Service
=================================

Fetches building heights from swissBUILDINGS3D on demand.
Uses the STAC API to find tiles based on coordinates, downloads and imports them.
"""

import asyncio
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
    bulk_insert_heights,
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
        # IMPORTANT: Use 2023+ to get tiles with EGID (BE/JU got EGID in June 2024)
        url = f"{STAC_API_BASE}/collections/{COLLECTION_ID}/items"
        params = {
            "bbox": bbox,
            "limit": 20,
            "datetime": "2023-01-01T00:00:00Z/2025-12-31T23:59:59Z"  # 2023+ tiles have EGID
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


def parse_gdb_for_heights(gdb_path: Path) -> Tuple[list, Dict[str, Any]]:
    """
    Parse a GDB file and extract EGID + height pairs.

    Args:
        gdb_path: Path to the GDB directory

    Returns:
        Tuple of (list of (egid, height) tuples, debug_info dict)
    """
    try:
        import geopandas as gpd
        import fiona
    except ImportError:
        raise ImportError("geopandas/fiona is required for GDB parsing")

    heights = []
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
            if 'building' in layer.lower() or 'solid' in layer.lower():
                target_layer = layer
                break

        if not target_layer and layers:
            target_layer = layers[0]

        if not target_layer:
            print("No suitable layer found in GDB")
            return heights, debug_info

        print(f"Using layer: {target_layer}")

        # Read without geometry for speed
        gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona', ignore_geometry=True)
        debug_info["columns"] = list(gdf.columns)
        debug_info["total_rows"] = len(gdf)
        print(f"Columns: {list(gdf.columns)}")
        print(f"Total rows: {len(gdf)}")

        for _, row in gdf.iterrows():
            egid = row.get('EGID')
            height = row.get('GESAMTHOEHE')

            if egid is None:
                debug_info["null_egid_count"] += 1
                continue
            if height is None:
                debug_info["null_height_count"] += 1
                continue

            try:
                egid_int = int(egid)
                height_float = float(height)
                if egid_int > 0 and height_float > 0:
                    heights.append((egid_int, round(height_float, 2)))
                    # Collect sample EGIDs
                    if len(debug_info["sample_egids"]) < 10:
                        debug_info["sample_egids"].append(egid_int)
            except (ValueError, TypeError):
                pass

        print(f"Found {len(heights)} valid heights, sample EGIDs: {debug_info['sample_egids']}")

    except Exception as e:
        print(f"Error parsing GDB: {e}")
        debug_info["error"] = str(e)

    return heights, debug_info


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

    # Check if we already have the height
    if egid:
        existing = get_building_height(egid)
        if existing:
            return {
                "status": "already_exists",
                "egid": egid,
                "height_m": existing[0],
                "source": existing[1],
                "imported_count": 0
            }

    # Find the tile for these coordinates
    tile_info = await find_tile_for_coordinates(e, n)

    if not tile_info:
        return {
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
        heights, debug_info = parse_gdb_for_heights(data_path)

        if not heights:
            return {
                "status": "no_heights_found",
                "tile_id": tile_info["id"],
                "message": "Tile downloaded but no building heights found",
                "imported_count": 0,
                "debug": debug_info
            }

        # Import into database
        source = f"swissBUILDINGS3D_3.0_ondemand_{tile_info['id']}"
        bulk_insert_heights(heights, source)

        # Log the import
        log_import(
            source_file=f"ondemand_{tile_info['id']}",
            canton="ondemand",
            records=len(heights),
            version="3.0"
        )

        # Look up the requested EGID
        result = {
            "status": "success",
            "tile_id": tile_info["id"],
            "imported_count": len(heights),
            "source": source,
            "debug": debug_info
        }

        if egid:
            height = get_building_height(egid)
            if height:
                result["egid"] = egid
                result["height_m"] = height[0]
                result["height_source"] = height[1]
            else:
                result["egid"] = egid
                result["height_found"] = False
                result["message"] = f"EGID {egid} not found in imported tile"
                # Show sample EGIDs that were found
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
