"""
Batch Import API Router
=======================

API-Endpunkte für den Batch-Import von swissBUILDINGS3D Tiles.
NEU 13.01.2026: Ersetzt direkten Script-Aufruf um DuckDB-Locking zu vermeiden.

Verwendung:
    POST /api/v1/batch/import/region/solothurn   - Region importieren
    POST /api/v1/batch/import/tile/1047-34       - Einzelnes Tile importieren
    GET  /api/v1/batch/import/status             - Import-Status abrufen
    GET  /api/v1/batch/import/regions            - Verfügbare Regionen
"""

import asyncio
import logging
import time
import tempfile
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.tile_cache import get_tile_cache
from app.services.tile_prefetch import reset_import_metrics
from app.services.building_3d_service import get_building_3d_service
from app.services.parquet_writer import import_tile_with_parquet_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/batch", tags=["Batch Import"])

# ============================================================================
# Regionen-Definitionen (identisch mit import_tiles.py)
# ============================================================================
#
# NEU 15.01.2026 02:15 - OVERLAP-WARNUNG:
# Die Regionen sind hierarchisch - größere enthalten kleinere!
#
# KEINE Überlappung:
#   - solothurn, basel_klein, zurich, basel
#
# MIT Überlappung (Vorsicht bei Statistiken!):
#   - bern_region > bern (bern ist Teilmenge von bern_region)
#
# Warum INSERT OR REPLACE?
#   Bei erneutem Import eines Tiles werden Gebäude NICHT dupliziert,
#   sondern überschrieben. Deshalb: Nach "bern" + "bern_region" sind
#   es NICHT doppelt so viele Gebäude!

REGIONS = {
    # ============================================
    # PRODUKTIONS-REGIONEN (mit Überlappung)
    # ============================================
    "bern": {
        "name": "Stadt Bern",
        "bbox": (2596000, 1197000, 2604000, 1203000),
        "expected_tiles": 11,
        "description": "Stadtzentrum Bern. ACHTUNG: Ist Teilmenge von bern_region!"
    },
    "bern_region": {
        "name": "Region Bern",
        "bbox": (2590000, 1190000, 2610000, 1210000),
        "expected_tiles": 100,
        "description": "Großraum Bern. ENTHÄLT: bern (Stadt)"
    },

    # ============================================
    # PRODUKTIONS-REGIONEN (ohne Überlappung)
    # ============================================
    "zurich": {
        "name": "Stadt Zürich",
        "bbox": (2676000, 1243000, 2690000, 1255000),
        "expected_tiles": 50
    },
    "basel": {
        "name": "Stadt Basel",
        "bbox": (2608000, 1264000, 2616000, 1272000),
        "expected_tiles": 16
    },

    # ============================================
    # KLEINE REGIONEN (ohne Überlappung, ideal für schnelle Imports)
    # ============================================
    "solothurn": {
        "name": "Solothurn Zentrum",
        "bbox": (2607000, 1228000, 2609000, 1230000),
        "expected_tiles": 2,
        "description": "Stadtzentrum Solothurn. KEINE Überlappung mit anderen Regionen."
    },
    "basel_klein": {
        "name": "Basel Klein (1 Tile)",
        "bbox": (2610000, 1266000, 2611000, 1267000),
        "expected_tiles": 1,
        "description": "Kleiner Ausschnitt Basel. KEINE Überlappung mit anderen Regionen."
    }
}

STAC_API_BASE = "https://data.geo.admin.ch/api/stac/v0.9"
COLLECTION_ID = "ch.swisstopo.swissbuildings3d_3_0"

# ============================================================================
# Import Status (In-Memory)
# ============================================================================

class ImportStatus:
    """Tracks the status of ongoing imports."""

    def __init__(self):
        self.running = False
        self.current_task: Optional[str] = None
        self.progress = {
            "tiles_total": 0,
            "tiles_processed": 0,
            "tiles_failed": 0,
            "buildings_imported": 0,
            "current_tile": None,
            "started_at": None,
            "finished_at": None,
            "errors": []
        }

    def start(self, task_name: str, total_tiles: int):
        self.running = True
        self.current_task = task_name
        self.progress = {
            "tiles_total": total_tiles,
            "tiles_processed": 0,
            "tiles_failed": 0,
            "buildings_imported": 0,
            "current_tile": None,
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "errors": []
        }

    def update(self, tile_id: str, buildings: int = 0, failed: bool = False, error: str = None):
        self.progress["current_tile"] = tile_id
        if failed:
            self.progress["tiles_failed"] += 1
            if error:
                self.progress["errors"].append({"tile": tile_id, "error": error})
        else:
            self.progress["tiles_processed"] += 1
            self.progress["buildings_imported"] += buildings

    def finish(self):
        self.running = False
        self.progress["finished_at"] = datetime.now().isoformat()
        self.progress["current_tile"] = None

    def to_dict(self) -> Dict[str, Any]:
        elapsed = None
        if self.progress["started_at"]:
            start = datetime.fromisoformat(self.progress["started_at"])
            end = datetime.fromisoformat(self.progress["finished_at"]) if self.progress["finished_at"] else datetime.now()
            elapsed = (end - start).total_seconds()

        return {
            "running": self.running,
            "task": self.current_task,
            "elapsed_seconds": elapsed,
            **self.progress
        }

_import_status = ImportStatus()

# ============================================================================
# Response Models
# ============================================================================

class RegionInfo(BaseModel):
    name: str
    bbox: Tuple[float, float, float, float]
    expected_tiles: int
    description: Optional[str] = None

class ImportStartResponse(BaseModel):
    message: str
    task: str
    tiles_to_import: int

class ImportStatusResponse(BaseModel):
    running: bool
    task: Optional[str]
    elapsed_seconds: Optional[float]
    tiles_total: int
    tiles_processed: int
    tiles_failed: int
    buildings_imported: int
    current_tile: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    errors: List[Dict[str, str]]

# ============================================================================
# Helper Functions
# ============================================================================

def lv95_to_wgs84(e: float, n: float) -> Tuple[float, float]:
    """Convert LV95 coordinates to WGS84."""
    y = (e - 2600000) / 1000000
    x = (n - 1200000) / 1000000
    lon = (2.6779094 + 4.728982 * y + 0.791484 * y * x +
           0.1306 * y * x * x - 0.0436 * y * y * y) * 100 / 36
    lat = (16.9023892 + 3.238272 * x - 0.270978 * y * y -
           0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x * x * x) * 100 / 36
    return lon, lat


async def discover_tiles_from_stac(bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
    """Query STAC API for tiles in a bounding box."""
    lon_min, lat_min = lv95_to_wgs84(bbox[0], bbox[1])
    lon_max, lat_max = lv95_to_wgs84(bbox[2], bbox[3])
    bbox_wgs84 = f"{lon_min},{lat_min},{lon_max},{lat_max}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        url = f"{STAC_API_BASE}/collections/{COLLECTION_ID}/items"
        params = {"bbox": bbox_wgs84, "limit": 500}

        response = await client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("features", [])


def _is_valid_tile_id(tile_id: str) -> bool:
    """
    Check if tile_id has valid format (xxxx-yy).
    FIX 13.01.2026: Filter out year-releases like '2023', '2024', '2025' which are full Switzerland datasets.
    """
    import re
    # Valid format: 4 digits, hyphen, 1-2 digits (e.g., "1047-34", "1332-21")
    return bool(re.match(r'^\d{4}-\d{1,2}$', tile_id))


async def get_stac_tiles_for_region(region_name: str) -> List[Tuple[str, str]]:
    """
    Get all tiles for a region via STAC API.
    FIX 13.01.2026: Only returns actual tiles, not year-releases. Prefers newest version per tile.
    """
    if region_name not in REGIONS:
        raise ValueError(f"Unknown region: {region_name}")

    region = REGIONS[region_name]
    bbox = region["bbox"]

    items = await discover_tiles_from_stac(bbox)

    # Collect tiles with version info, keyed by tile_id
    tile_versions: Dict[str, Tuple[str, str, str]] = {}  # tile_id -> (version, item_id, url)

    for item in items:
        item_id = item.get("id", "")
        # Extract tile_id and version from item_id
        # Format: swissbuildings3d_3_0_YYYY_tile-id or swissbuildings3d_3_0_YYYY (year-release)
        parts = item_id.split("_")
        if len(parts) >= 4:
            version = parts[3]  # Year like "2024"
            tile_id = parts[-1] if len(parts) > 4 else version  # tile-id or year for releases
        else:
            continue

        # Skip year-releases (not real tiles)
        if not _is_valid_tile_id(tile_id):
            logger.debug(f"Skipping year-release: {item_id}")
            continue

        download_url = None
        assets = item.get("assets", {})

        for asset_name, asset in assets.items():
            if "gdb" in asset_name.lower():
                download_url = asset.get("href")
                break

        if not download_url:
            for asset in assets.values():
                href = asset.get("href", "")
                if href.endswith(".zip"):
                    download_url = href
                    break

        if download_url:
            # Keep newest version per tile
            if tile_id not in tile_versions or version > tile_versions[tile_id][0]:
                tile_versions[tile_id] = (version, item_id, download_url)

    tiles = [(tile_id, data[2]) for tile_id, data in tile_versions.items()]
    logger.info(f"Found {len(tiles)} tiles for region {region_name}")
    return tiles


def _download_tile(tile_id: str, download_url: str) -> Path:
    """
    Download and cache a tile (synchronous). Returns path to GDB.

    REFACTORED 14.01.2026: Separated from import to allow async prefetch_tile_buildings().
    """
    import urllib.request

    tile_cache = get_tile_cache()

    # Check cache first
    cached_path = tile_cache.get_tile_path(tile_id)
    if cached_path and cached_path.exists():
        logger.info(f"Tile {tile_id} from cache: {cached_path}")
        return cached_path

    # Download
    logger.info(f"Downloading tile {tile_id}...")
    download_start = time.time()
    temp_dir = Path(tempfile.mkdtemp())
    try:
        zip_path = temp_dir / "tile.zip"
        urllib.request.urlretrieve(download_url, zip_path)
        download_ms = (time.time() - download_start) * 1000
        file_size_mb = zip_path.stat().st_size / (1024 * 1024)

        # Update metrics for download
        from app.services.tile_prefetch import update_import_metrics
        update_import_metrics(
            tile_id=tile_id,
            download_ms=download_ms,
            file_size_mb=file_size_mb
        )
        logger.info(f"  Downloaded: {file_size_mb:.1f}MB in {download_ms:.0f}ms")

        # Unzip
        unzip_start = time.time()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_dir)
        unzip_ms = (time.time() - unzip_start) * 1000
        update_import_metrics(unzip_ms=unzip_ms)
        logger.info(f"  Unzipped in {unzip_ms:.0f}ms")

        gdb_path = None
        for item in temp_dir.iterdir():
            if item.is_dir() and item.suffix.lower() == '.gdb':
                gdb_path = item
                break

        if not gdb_path:
            raise FileNotFoundError(f"No GDB found in {tile_id}")

        # Cache the tile
        cached_path = tile_cache.store_tile(
            tile_id=tile_id,
            gdb_path=gdb_path,
            download_url=download_url
        )
        return cached_path

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def download_and_import_tile(tile_id: str, download_url: str) -> dict:
    """
    Download and import a single tile with ALL layers via Parquet-Pipeline.

    REFACTORED 15.01.2026: Uses Parquet-Pipeline for 2.88x speedup:
    - GDB → Parquet (streaming, parallel)
    - Parquet → DuckDB (bulk-load, SIMD-optimiert)
    - Building_solid → buildings_3d
    - Roof_solid → building_roofs
    - Wall → building_walls

    Returns dict with counts: {buildings_count, roofs_count, walls_count}
    """
    # Reset metrics for this tile
    reset_import_metrics()

    # 1. Download (sync, in thread pool)
    gdb_path = await asyncio.to_thread(_download_tile, tile_id, download_url)

    # 2. Import via Parquet-Pipeline (2.88x faster than direct inserts)
    # NEU 15.01.2026: Streaming Parquet + DuckDB Bulk-Load
    logger.info(f"Importing tile {tile_id} via Parquet-Pipeline...")
    result = await import_tile_with_parquet_pipeline(gdb_path, tile_id, cleanup_after=True)

    logger.info(
        f"Tile {tile_id} complete: {result['buildings_count']} buildings, "
        f"{result['roofs_count']} roofs, {result['walls_count']} walls "
        f"({result['total_ms']:.0f}ms)"
    )
    return result


async def run_region_import(region_name: str, max_concurrent: int = 3):
    """
    Background task to import a region with PARALLEL tile downloads.

    NEU 15.01.2026: C.5 Parallel Download implementiert.
    - Downloads laufen parallel (max_concurrent=3)
    - Parquet-Parsing pro Tile läuft parallel (3 Layer gleichzeitig)
    - DuckDB Bulk-Load sequentiell (wegen File-Locking)

    Args:
        region_name: Name der Region (aus REGIONS dict)
        max_concurrent: Max. parallele Downloads (default: 3)
    """
    global _import_status

    try:
        # Get tiles via STAC
        tiles = await get_stac_tiles_for_region(region_name)

        if not tiles:
            logger.error(f"No tiles found for region {region_name}")
            _import_status.finish()
            return

        _import_status.start(f"region:{region_name}", len(tiles))

        building_service = get_building_3d_service()

        # Drop indexes for faster import (only if > 5 tiles)
        if len(tiles) > 5:
            logger.info("Dropping indexes for faster import...")
            building_service.drop_indexes()

        # NEU 15.01.2026: Semaphore für parallelen Download
        semaphore = asyncio.Semaphore(max_concurrent)

        async def import_single_tile(tile_id: str, download_url: str) -> dict:
            """Import a single tile with semaphore control."""
            async with semaphore:
                _import_status.progress["current_tile"] = tile_id
                logger.info(f"[PARALLEL] Starting tile {tile_id}")
                return await download_and_import_tile(tile_id, download_url)

        # Create tasks for all tiles
        tasks = [
            import_single_tile(tile_id, download_url)
            for tile_id, download_url in tiles
        ]

        # Execute all tasks, collect results as they complete
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                _import_status.progress["tiles_processed"] += 1
                _import_status.progress["buildings_imported"] += result.get("buildings_count", 0)
            except Exception as e:
                logger.error(f"Error importing tile: {e}")
                _import_status.progress["tiles_failed"] += 1
                _import_status.progress["errors"].append({"tile": "unknown", "error": str(e)})

        # Recreate indexes
        if len(tiles) > 5:
            logger.info("Creating indexes...")
            building_service.create_indexes()

    except Exception as e:
        logger.error(f"Region import failed: {e}")
        _import_status.progress["errors"].append({"tile": "general", "error": str(e)})

    finally:
        _import_status.finish()


async def run_tile_import(tile_id: str, download_url: Optional[str] = None):
    """Background task to import a single tile."""
    global _import_status

    try:
        _import_status.start(f"tile:{tile_id}", 1)

        if not download_url:
            # Find URL via STAC
            # Use a small bbox around assumed coordinates
            # This is a fallback - ideally URL should be provided
            raise ValueError("download_url required for single tile import")

        _import_status.progress["current_tile"] = tile_id
        result = await download_and_import_tile(tile_id, download_url)
        # NEU 15.01.2026: result ist jetzt ein Dict
        _import_status.progress["tiles_processed"] += 1
        _import_status.progress["buildings_imported"] += result.get("buildings_count", 0)

    except Exception as e:
        logger.error(f"Tile import failed: {e}")
        _import_status.update(tile_id, failed=True, error=str(e))

    finally:
        _import_status.finish()

# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/import/regions", response_model=Dict[str, RegionInfo])
async def list_regions():
    """List all available regions for import."""
    return {
        name: RegionInfo(
            name=region["name"],
            bbox=region["bbox"],
            expected_tiles=region["expected_tiles"],
            description=region.get("description")
        )
        for name, region in REGIONS.items()
    }


@router.get("/import/status", response_model=ImportStatusResponse)
async def get_import_status():
    """Get the current import status."""
    return ImportStatusResponse(**_import_status.to_dict())


@router.post("/import/region/{region_name}", response_model=ImportStartResponse)
async def import_region(region_name: str):
    """
    Start importing all tiles for a region.

    The import runs in the background. Use GET /import/status to monitor progress.
    FIX 13.01.2026: Uses asyncio.create_task() instead of BackgroundTasks for proper async execution.
    """
    if _import_status.running:
        raise HTTPException(
            status_code=409,
            detail=f"Import already running: {_import_status.current_task}"
        )

    if region_name not in REGIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown region: {region_name}. Available: {list(REGIONS.keys())}"
        )

    # Get tile count first
    tiles = await get_stac_tiles_for_region(region_name)

    if not tiles:
        raise HTTPException(
            status_code=404,
            detail=f"No tiles found for region {region_name}"
        )

    # Start background import with asyncio.create_task() - doesn't block event loop
    asyncio.create_task(run_region_import(region_name))

    return ImportStartResponse(
        message=f"Import started for region '{REGIONS[region_name]['name']}'",
        task=f"region:{region_name}",
        tiles_to_import=len(tiles)
    )


@router.post("/import/tile/{tile_id}")
async def import_tile(tile_id: str, download_url: str):
    """
    Import a single tile by ID.

    Requires the download_url parameter with the full URL to the tile ZIP.
    FIX 13.01.2026: Uses asyncio.create_task() for proper async execution.
    """
    if _import_status.running:
        raise HTTPException(
            status_code=409,
            detail=f"Import already running: {_import_status.current_task}"
        )

    asyncio.create_task(run_tile_import(tile_id, download_url))

    return ImportStartResponse(
        message=f"Import started for tile '{tile_id}'",
        task=f"tile:{tile_id}",
        tiles_to_import=1
    )


@router.get("/import/db-stats")
async def get_db_stats():
    """Get current database statistics."""
    building_service = get_building_3d_service()
    tile_cache = get_tile_cache()

    return {
        "buildings": building_service.get_stats(),
        "tiles": tile_cache.get_stats()
    }


@router.get("/import/metrics")
async def get_import_metrics_endpoint():
    """
    Get detailed timing metrics from the last tile import.

    NEU 14.01.2026: Vollständige Baseline-Metriken für Optimierungs-Analyse.

    Returns timing for all phases:
    - download_ms: Download time
    - file_size_mb: ZIP file size
    - unzip_ms: Extraction time
    - parse_building_solid_ms/count: Building_solid layer parsing
    - parse_roof_solid_ms/count: Roof_solid layer parsing
    - parse_wall_ms/count: Wall layer parsing
    - db_write_buildings_ms: DB write time for buildings
    - db_write_roofs_ms: DB write time for roofs
    - db_write_walls_ms: DB write time for walls
    - total_ms: Total import time
    - ms_per_building: Average time per building
    """
    from app.services.tile_prefetch import get_import_metrics
    return get_import_metrics()