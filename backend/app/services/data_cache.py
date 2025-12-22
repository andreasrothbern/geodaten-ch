"""
Address Data Cache Service

Caches all computed data for an address to avoid repeated API calls.
Data is computed once on first request, then reused for:
- Tab switching (Gerüstbau, Ausmass, Material, Schulaufgaben)
- Document generation
- SVG visualization
"""

import time
import hashlib
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Cache TTL in seconds (30 minutes)
CACHE_TTL = 1800

# In-memory cache
_address_cache: Dict[str, Dict[str, Any]] = {}


@dataclass
class CachedAddressData:
    """Complete cached data for an address"""
    # Metadata
    address_input: str
    address_matched: str
    cached_at: float

    # Coordinates
    lv95_e: float
    lv95_n: float

    # Building info
    egid: Optional[int] = None
    floors: Optional[int] = None
    area_m2: Optional[float] = None
    building_category: Optional[str] = None
    construction_year: Optional[int] = None

    # Dimensions
    length_m: float = 10.0
    width_m: float = 10.0
    eave_height_m: float = 8.0
    ridge_height_m: Optional[float] = None
    perimeter_m: float = 40.0

    # Heights from swissBUILDINGS3D
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None

    # Geometry (polygon sides)
    sides: list = field(default_factory=list)
    polygon_coordinates: list = field(default_factory=list)

    # Computed data
    scaffolding_data: Optional[Dict[str, Any]] = None
    ausmass_data: Optional[Dict[str, Any]] = None
    material_data: Optional[Dict[str, Any]] = None

    # 3D viewer URL
    viewer_3d_url: Optional[str] = None


def get_cache_key(address: str) -> str:
    """Generate cache key from address"""
    normalized = address.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()


def get_cached_data(address: str) -> Optional[CachedAddressData]:
    """Get cached data for address if available and not expired"""
    cache_key = get_cache_key(address)

    if cache_key not in _address_cache:
        return None

    cached = _address_cache[cache_key]

    # Check TTL
    if time.time() - cached.get('cached_at', 0) > CACHE_TTL:
        del _address_cache[cache_key]
        return None

    return CachedAddressData(**cached)


def set_cached_data(data: CachedAddressData) -> None:
    """Store data in cache"""
    cache_key = get_cache_key(data.address_input)
    _address_cache[cache_key] = asdict(data)


def clear_cache(address: Optional[str] = None) -> int:
    """Clear cache for specific address or all"""
    global _address_cache

    if address:
        cache_key = get_cache_key(address)
        if cache_key in _address_cache:
            del _address_cache[cache_key]
            return 1
        return 0
    else:
        count = len(_address_cache)
        _address_cache = {}
        return count


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return {
        "entries": len(_address_cache),
        "addresses": [v.get('address_matched', 'unknown') for v in _address_cache.values()],
        "ttl_seconds": CACHE_TTL
    }


async def fetch_and_cache_complete_data(
    address: str,
    swisstopo_service,
    geodienste_service,
    force_refresh: bool = False
) -> CachedAddressData:
    """
    Fetch all data for an address and cache it.
    Returns cached data if available (unless force_refresh).
    """
    import time

    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = get_cached_data(address)
        if cached:
            return cached

    # Fetch fresh data
    # 1. Geocode address
    geo = await swisstopo_service.geocode(address)
    if not geo:
        raise ValueError(f"Adresse nicht gefunden: {address}")

    # 2. Find building
    buildings = await swisstopo_service.identify_buildings(
        geo.coordinates.lv95_e,
        geo.coordinates.lv95_n,
        tolerance=15
    )
    building = buildings[0] if buildings else None

    # 3. Get building geometry
    geometry = await geodienste_service.get_building_geometry(
        x=geo.coordinates.lv95_e,
        y=geo.coordinates.lv95_n,
        tolerance=50,
        egid=building.egid if building else None
    )

    # 4. Calculate dimensions
    if geometry and geometry.sides:
        side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
        length_m = side_lengths[0] if side_lengths else 10.0
        width_m = side_lengths[1] if len(side_lengths) > 1 else length_m
        perimeter = sum(s['length_m'] for s in geometry.sides)
        sides = geometry.sides
        polygon_coords = geometry.polygon_lv95 if hasattr(geometry, 'polygon_lv95') else []
    elif building and building.area_m2:
        import math
        side = math.sqrt(building.area_m2)
        length_m = width_m = round(side, 1)
        perimeter = 4 * side
        sides = []
        polygon_coords = []
    else:
        length_m = width_m = 10.0
        perimeter = 40.0
        sides = []
        polygon_coords = []

    # 5. Get heights
    eave_height_m = (building.floors or 3) * 2.8
    ridge_height_m = None
    traufhoehe_m = None
    firsthoehe_m = None
    gebaeudehoehe_m = None

    if building and building.egid:
        from app.services.height_db import get_building_heights_detailed
        heights = get_building_heights_detailed(building.egid)
        if heights:
            traufhoehe_m = heights.get("traufhoehe_m")
            firsthoehe_m = heights.get("firsthoehe_m")
            gebaeudehoehe_m = heights.get("gebaeudehoehe_m")

            if traufhoehe_m:
                eave_height_m = traufhoehe_m
            if firsthoehe_m:
                ridge_height_m = firsthoehe_m
            elif gebaeudehoehe_m and not traufhoehe_m:
                eave_height_m = gebaeudehoehe_m * 0.85
                ridge_height_m = gebaeudehoehe_m

    # Default ridge height for gable roof
    if ridge_height_m is None:
        ridge_height_m = eave_height_m + 3.5

    # 6. Build 3D viewer URL (new format since 2024)
    viewer_3d_url = None
    if geo:
        # LV95 coordinates need 2000000 added to E and 1000000 added to N if < 1000000
        e = geo.coordinates.lv95_e
        n = geo.coordinates.lv95_n
        if e < 2000000:
            e += 2000000
        if n < 1000000:
            n += 1000000
        # 3D view automatically shows buildings - no layers parameter needed
        viewer_3d_url = (
            f"https://map.geo.admin.ch/#/map?lang=de"
            f"&bgLayer=ch.swisstopo.pixelkarte-farbe"
            f"&center={e:.0f},{n:.0f}&z=12&3d=true"
        )

    # Create cached data object
    cached_data = CachedAddressData(
        address_input=address,
        address_matched=geo.matched_address,
        cached_at=time.time(),
        lv95_e=geo.coordinates.lv95_e,
        lv95_n=geo.coordinates.lv95_n,
        egid=building.egid if building else None,
        floors=building.floors if building else None,
        area_m2=building.area_m2 if building else None,
        building_category=building.building_category if building else None,
        construction_year=building.construction_year if building else None,
        length_m=round(length_m, 1),
        width_m=round(width_m, 1),
        eave_height_m=round(eave_height_m, 1),
        ridge_height_m=round(ridge_height_m, 1) if ridge_height_m else None,
        perimeter_m=round(perimeter, 1),
        traufhoehe_m=traufhoehe_m,
        firsthoehe_m=firsthoehe_m,
        gebaeudehoehe_m=gebaeudehoehe_m,
        sides=sides,
        polygon_coordinates=polygon_coords,
        viewer_3d_url=viewer_3d_url
    )

    # Store in cache
    set_cached_data(cached_data)

    return cached_data
