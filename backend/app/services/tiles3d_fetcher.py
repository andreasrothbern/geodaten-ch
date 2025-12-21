"""
3D Tiles Height Fetcher
=======================

Fetches building heights directly from swissBUILDINGS3D 3D Tiles.
Uses coordinate-based lookup - no EGID required!

Workflow:
1. Convert WGS84 coordinates to tile x/y
2. Load tileset index to find available tiles
3. Download the b3dm tile (or nearest neighbor)
4. Parse BatchTable for buildings
5. Find nearest building by coordinates
6. Return height
"""

import struct
import json
import gzip
import math
import urllib.request
from typing import Optional, Dict, Any, List, Tuple, Set
from dataclasses import dataclass

# 3D Tiles Configuration
TILES_BASE_URL = "https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/20251121"
TILESET_JSON_URL = f"{TILES_BASE_URL}/tileset.json"
SUB_TILESETS = ["tileset9.json", "tileset10.json", "tileset11.json", "tileset12.json", "tileset21.json", "tileset29.json"]
ZOOM_LEVEL = 11  # Fixed zoom level for swissBUILDINGS3D

# Cached tileset index
_tile_index: Optional[Set[str]] = None


@dataclass
class Building3D:
    """Gebäude aus 3D Tiles"""
    height_m: float
    latitude: float
    longitude: float
    uuid: str
    objektart: Optional[str] = None
    distance_m: Optional[float] = None


def wgs84_to_tile(lat: float, lon: float, zoom: int = ZOOM_LEVEL) -> Tuple[int, int]:
    """
    Convert WGS84 coordinates to tile x/y at given zoom level.

    Uses Web Mercator (Slippy Map) tile scheme.
    """
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_wgs84(x: int, y: int, zoom: int = ZOOM_LEVEL) -> Tuple[float, float]:
    """
    Convert tile coordinates back to WGS84 (center of tile).
    """
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


@dataclass
class TileInfo:
    """Tile with bounding volume."""
    uri: str
    west: float  # longitude min (degrees)
    south: float  # latitude min (degrees)
    east: float  # longitude max (degrees)
    north: float  # latitude max (degrees)
    center_lat: float
    center_lon: float


# Cached tile index with bounding volumes
_tile_index_with_bounds: Optional[List[TileInfo]] = None


def load_tile_index() -> List[TileInfo]:
    """
    Load the index of available tiles with their bounding volumes.
    Uses the tileset JSON files to get actual geographic bounds.
    """
    global _tile_index_with_bounds
    if _tile_index_with_bounds is not None:
        return _tile_index_with_bounds

    def find_tiles_with_bounds(node: dict, tiles: List[TileInfo], depth: int = 0):
        if depth > 15:
            return
        if 'content' in node and 'uri' in node['content']:
            uri = node['content']['uri']
            if uri.endswith('.b3dm'):
                # Get bounding volume (in radians)
                bv = node.get('boundingVolume', {}).get('region', [])
                if len(bv) >= 4:
                    # Convert radians to degrees
                    west = math.degrees(bv[0])
                    south = math.degrees(bv[1])
                    east = math.degrees(bv[2])
                    north = math.degrees(bv[3])
                    tiles.append(TileInfo(
                        uri=uri,
                        west=west, south=south, east=east, north=north,
                        center_lat=(south + north) / 2,
                        center_lon=(west + east) / 2
                    ))
        if 'children' in node:
            for child in node['children']:
                find_tiles_with_bounds(child, tiles, depth + 1)

    all_tiles = []
    for tileset_name in SUB_TILESETS:
        try:
            url = f"{TILES_BASE_URL}/{tileset_name}"
            req = urllib.request.Request(url, headers={'User-Agent': 'geodaten-ch/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.load(response)
                find_tiles_with_bounds(data['root'], all_tiles)
        except Exception as e:
            print(f"Error loading {tileset_name}: {e}")
            continue

    _tile_index_with_bounds = all_tiles
    print(f"Loaded tile index with {len(_tile_index_with_bounds)} tiles")
    return _tile_index_with_bounds


def find_tiles_containing_point(lat: float, lon: float) -> List[TileInfo]:
    """
    Find tiles whose bounding volume contains the given point.
    """
    tile_index = load_tile_index()
    containing = []

    for tile in tile_index:
        if tile.west <= lon <= tile.east and tile.south <= lat <= tile.north:
            containing.append(tile)

    return containing


def find_tiles_near_point(lat: float, lon: float, max_tiles: int = 20) -> List[TileInfo]:
    """
    Find tiles nearest to the given point.
    Returns tiles sorted by distance from point to tile center.
    """
    tile_index = load_tile_index()

    # Calculate distance to each tile
    tiles_with_dist = []
    for tile in tile_index:
        # Use simple Euclidean distance in degrees (good enough for sorting)
        dist = ((tile.center_lat - lat) ** 2 + (tile.center_lon - lon) ** 2) ** 0.5
        tiles_with_dist.append((dist, tile))

    # Sort by distance
    tiles_with_dist.sort(key=lambda x: x[0])

    return [t[1] for t in tiles_with_dist[:max_tiles]]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in meters using Haversine formula.
    """
    R = 6371000  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def download_tile_by_uri(uri: str) -> Optional[bytes]:
    """
    Download a 3D tile from swisstopo by URI.

    Args:
        uri: Tile URI like "11/1891/425.b3dm"

    Returns raw bytes or None if tile doesn't exist.
    """
    url = f"{TILES_BASE_URL}/{uri}"

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'geodaten-ch/1.0',
            'Accept-Encoding': 'gzip'
        })

        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()

            # Decompress if gzipped
            if data[:2] == b'\x1f\x8b':
                data = gzip.decompress(data)

            return data

    except urllib.error.HTTPError as e:
        if e.code == 404 or e.code == 403:
            return None
        raise
    except Exception as e:
        print(f"Error downloading tile {uri}: {e}")
        return None


def parse_b3dm(data: bytes) -> Dict[str, Any]:
    """
    Parse b3dm file and extract BatchTable with building attributes.
    """
    if len(data) < 28:
        raise ValueError("Data too short for b3dm")

    # Verify magic
    magic = data[0:4].decode('ascii')
    if magic != 'b3dm':
        raise ValueError(f"Invalid magic: {magic}")

    # Parse header
    feature_table_json_length = struct.unpack('<I', data[12:16])[0]
    feature_table_binary_length = struct.unpack('<I', data[16:20])[0]
    batch_table_json_length = struct.unpack('<I', data[20:24])[0]

    offset = 28

    # Feature Table
    feature_table = {}
    if feature_table_json_length > 0:
        ft_json = data[offset:offset + feature_table_json_length]
        feature_table = json.loads(ft_json.decode('utf-8').rstrip('\x00'))
    offset += feature_table_json_length + feature_table_binary_length

    # Batch Table (contains building attributes)
    batch_table = {}
    if batch_table_json_length > 0:
        bt_json = data[offset:offset + batch_table_json_length]
        batch_table = json.loads(bt_json.decode('utf-8').rstrip('\x00'))

    return {
        'batch_length': feature_table.get('BATCH_LENGTH', 0),
        'batch_table': batch_table
    }


def extract_buildings(parsed: Dict[str, Any]) -> List[Building3D]:
    """
    Extract building information from parsed b3dm data.
    """
    batch_table = parsed.get('batch_table', {})
    batch_length = parsed.get('batch_length', 0)

    if batch_length == 0:
        return []

    heights = batch_table.get('Height', [])
    latitudes = batch_table.get('Latitude', [])
    longitudes = batch_table.get('Longitude', [])
    uuids = batch_table.get('UUID', [])
    objektarten = batch_table.get('OBJEKTART', [])

    buildings = []
    for i in range(min(batch_length, len(heights), len(latitudes), len(longitudes))):
        # Skip invalid entries
        height = heights[i] if i < len(heights) else 0
        lat = latitudes[i] if i < len(latitudes) else 0
        lon = longitudes[i] if i < len(longitudes) else 0

        if height <= 0 or lat == 0 or lon == 0:
            continue

        buildings.append(Building3D(
            height_m=round(height, 2),
            latitude=lat,
            longitude=lon,
            uuid=uuids[i] if i < len(uuids) else '',
            objektart=objektarten[i] if i < len(objektarten) else None
        ))

    return buildings


def find_nearest_building(
    buildings: List[Building3D],
    target_lat: float,
    target_lon: float,
    max_distance_m: float = 50.0
) -> Optional[Building3D]:
    """
    Find the building nearest to target coordinates.

    Args:
        buildings: List of buildings from tile
        target_lat: Target latitude (WGS84)
        target_lon: Target longitude (WGS84)
        max_distance_m: Maximum distance to consider (default 50m)

    Returns:
        Nearest building or None if none within max_distance
    """
    nearest = None
    min_distance = float('inf')

    for building in buildings:
        distance = haversine_distance(
            target_lat, target_lon,
            building.latitude, building.longitude
        )

        if distance < min_distance and distance <= max_distance_m:
            min_distance = distance
            nearest = building
            nearest.distance_m = round(distance, 1)

    return nearest


async def fetch_height_from_3d_tiles(
    lat: float,
    lon: float,
    max_distance_m: float = 100.0
) -> Dict[str, Any]:
    """
    Fetch building height from 3D Tiles at given coordinates.

    Args:
        lat: Latitude (WGS84)
        lon: Longitude (WGS84)
        max_distance_m: Maximum search radius

    Returns:
        Dict with height info or error
    """
    # First try to find tiles that contain the point
    containing_tiles = find_tiles_containing_point(lat, lon)

    # If none contain the point, find nearest tiles
    if not containing_tiles:
        nearby_tiles = find_tiles_near_point(lat, lon, max_tiles=10)
        if not nearby_tiles:
            return {
                "status": "no_tiles",
                "message": f"No 3D Tiles available near coordinates ({lat}, {lon})",
                "searched_coordinates": {"lat": lat, "lon": lon}
            }
        tiles_to_search = nearby_tiles
    else:
        # Also include some nearby tiles in case building is at tile edge
        nearby_tiles = find_tiles_near_point(lat, lon, max_tiles=5)
        tiles_to_search = containing_tiles + [t for t in nearby_tiles if t not in containing_tiles]

    # Search through tiles
    all_buildings = []
    tiles_searched = []

    for tile_info in tiles_to_search[:10]:  # Check up to 10 tiles
        tiles_searched.append(tile_info.uri)

        # Download tile
        data = download_tile_by_uri(tile_info.uri)

        if data is None:
            continue

        try:
            # Parse tile
            parsed = parse_b3dm(data)
            buildings = extract_buildings(parsed)

            if buildings:
                all_buildings.extend(buildings)

        except Exception as e:
            print(f"Error parsing tile {tile_info.uri}: {e}")
            continue

    if not all_buildings:
        return {
            "status": "no_buildings",
            "message": f"No buildings found in nearby tiles",
            "searched_coordinates": {"lat": lat, "lon": lon},
            "tiles_searched": tiles_searched
        }

    # Find nearest building across all tiles
    nearest = find_nearest_building(all_buildings, lat, lon, max_distance_m)

    if nearest:
        return {
            "status": "success",
            "height_m": nearest.height_m,
            "source": "3d_tiles",
            "building": {
                "uuid": nearest.uuid,
                "objektart": nearest.objektart,
                "latitude": nearest.latitude,
                "longitude": nearest.longitude,
                "distance_m": nearest.distance_m
            },
            "search_info": {
                "tiles_searched": len(tiles_searched),
                "buildings_found": len(all_buildings)
            }
        }

    return {
        "status": "not_found",
        "message": f"No building found within {max_distance_m}m of coordinates ({lat}, {lon})",
        "searched_coordinates": {"lat": lat, "lon": lon},
        "tiles_searched": tiles_searched,
        "buildings_in_area": len(all_buildings)
    }


def lv95_to_wgs84(e: float, n: float) -> Tuple[float, float]:
    """
    Convert LV95 coordinates to WGS84.

    Uses official swisstopo approximation formulas.
    """
    # Handle LV03 input (add prefix if needed)
    if e < 1_000_000:
        e = e + 2_000_000
        n = n + 1_000_000

    # Auxiliary values
    y = (e - 2_600_000) / 1_000_000
    x = (n - 1_200_000) / 1_000_000

    # Calculate WGS84
    lon = (2.6779094 + 4.728982 * y + 0.791484 * y * x +
           0.1306 * y * x * x - 0.0436 * y * y * y) * 100 / 36

    lat = (16.9023892 + 3.238272 * x - 0.270978 * y * y -
           0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x * x * x) * 100 / 36

    return lat, lon


# Convenience function for LV95 input
async def fetch_height_from_3d_tiles_lv95(
    e: float,
    n: float,
    max_distance_m: float = 50.0
) -> Dict[str, Any]:
    """
    Fetch height using LV95 coordinates (converts to WGS84 internally).
    """
    lat, lon = lv95_to_wgs84(e, n)
    result = await fetch_height_from_3d_tiles(lat, lon, max_distance_m)
    result["input_lv95"] = {"e": e, "n": n}
    result["converted_wgs84"] = {"lat": round(lat, 6), "lon": round(lon, 6)}
    return result


# Test function
if __name__ == "__main__":
    import asyncio

    async def test():
        # Test with Bern coordinates
        print("=== Test: Bern Bundesplatz ===")
        result = await fetch_height_from_3d_tiles(46.9466, 7.4448)
        print(json.dumps(result, indent=2))

        print("\n=== Test: Basel Marktplatz ===")
        result = await fetch_height_from_3d_tiles(47.5576, 7.5880)
        print(json.dumps(result, indent=2))

        print("\n=== Test: LV95 Coordinates (Bern) ===")
        result = await fetch_height_from_3d_tiles_lv95(2600000, 1199000)
        print(json.dumps(result, indent=2))

    asyncio.run(test())
