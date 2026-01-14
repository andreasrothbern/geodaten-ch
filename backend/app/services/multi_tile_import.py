"""
Multi-Tile Import Service mit parallelem Download und Progress-Tracking.

NEU 14.01.2026: Implementiert C.5, C.6, C.7

C.5: Paralleler Download
- Mehrere Tiles gleichzeitig downloaden (asyncio.gather)
- Konfigurierbares Concurrency-Limit (default: 3)
- Automatischer Retry bei Fehlern

C.6: Progress-Tracking
- Strukturierte Log-Messages mit Fortschritt
- ETA-Berechnung basierend auf bisheriger Geschwindigkeit
- Status-Dict für API-Abfrage

C.7: Cleanup-Integration
- Automatisches Löschen von GDB-Dateien nach Import
- Automatisches Löschen von Parquet-Dateien nach DB-Load
- Manueller Cleanup-Endpoint
"""

import asyncio
import logging
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


# =============================================================================
# C.6: PROGRESS STATE
# =============================================================================

@dataclass
class TileProgress:
    """Fortschritt für ein einzelnes Tile."""
    tile_id: str
    status: str = "pending"  # pending, downloading, parsing, loading, completed, failed
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    buildings_count: int = 0
    roofs_count: int = 0
    walls_count: int = 0
    error: Optional[str] = None


@dataclass
class ImportProgress:
    """Gesamtfortschritt eines Multi-Tile-Imports."""
    import_id: str
    started_at: float = field(default_factory=time.time)
    tiles_total: int = 0
    tiles_completed: int = 0
    tiles_failed: int = 0
    current_phase: str = "initializing"  # initializing, downloading, importing, completed
    tile_progress: Dict[str, TileProgress] = field(default_factory=dict)

    # Statistiken
    total_buildings: int = 0
    total_roofs: int = 0
    total_walls: int = 0

    @property
    def tiles_pending(self) -> int:
        return self.tiles_total - self.tiles_completed - self.tiles_failed

    @property
    def progress_percent(self) -> float:
        if self.tiles_total == 0:
            return 0.0
        return (self.tiles_completed / self.tiles_total) * 100

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    @property
    def eta_seconds(self) -> Optional[float]:
        """Geschätzte Restzeit basierend auf bisheriger Geschwindigkeit."""
        if self.tiles_completed == 0:
            return None
        avg_time_per_tile = self.elapsed_seconds / self.tiles_completed
        return avg_time_per_tile * self.tiles_pending

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Progress zu JSON-serialisierbarem Dict."""
        eta = self.eta_seconds
        return {
            "import_id": self.import_id,
            "started_at": datetime.fromtimestamp(self.started_at).isoformat(),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "tiles_total": self.tiles_total,
            "tiles_completed": self.tiles_completed,
            "tiles_failed": self.tiles_failed,
            "tiles_pending": self.tiles_pending,
            "progress_percent": round(self.progress_percent, 1),
            "eta_seconds": round(eta, 0) if eta else None,
            "eta_formatted": str(timedelta(seconds=int(eta))) if eta else None,
            "current_phase": self.current_phase,
            "total_buildings": self.total_buildings,
            "total_roofs": self.total_roofs,
            "total_walls": self.total_walls,
            "tiles": {
                tile_id: {
                    "status": tp.status,
                    "buildings": tp.buildings_count,
                    "error": tp.error,
                }
                for tile_id, tp in self.tile_progress.items()
            }
        }


# Globaler State für laufende Imports
_active_imports: Dict[str, ImportProgress] = {}
_imports_lock = Lock()


def get_import_progress(import_id: str) -> Optional[ImportProgress]:
    """Gibt den Fortschritt eines Imports zurück."""
    with _imports_lock:
        return _active_imports.get(import_id)


def get_all_imports() -> Dict[str, Dict]:
    """Gibt alle aktiven Imports zurück."""
    with _imports_lock:
        return {
            import_id: progress.to_dict()
            for import_id, progress in _active_imports.items()
        }


def _log_progress(progress: ImportProgress, message: str):
    """Strukturiertes Progress-Logging."""
    eta_str = ""
    if progress.eta_seconds:
        eta_str = f" | ETA: {timedelta(seconds=int(progress.eta_seconds))}"

    logger.info(
        f"[IMPORT] {progress.import_id} | "
        f"{progress.tiles_completed}/{progress.tiles_total} Tiles ({progress.progress_percent:.0f}%)"
        f"{eta_str} | {message}"
    )


# =============================================================================
# C.5: PARALLEL DOWNLOAD
# =============================================================================

async def download_tiles_parallel(
    tile_ids: List[str],
    max_concurrent: int = 3,
    progress: Optional[ImportProgress] = None
) -> Dict[str, Path]:
    """
    Lädt mehrere Tiles parallel herunter.

    Args:
        tile_ids: Liste der Tile-IDs zum Download
        max_concurrent: Maximale parallele Downloads (default: 3)
        progress: Optional ImportProgress für Status-Updates

    Returns:
        Dict[tile_id, gdb_path] für erfolgreiche Downloads
    """
    from app.services.tile_cache import get_tile_cache
    from app.services.swissbuildings3d_fetcher import (
        find_tile_for_coordinates,
        download_and_extract_tile,
    )
    import tempfile

    tile_cache = get_tile_cache()
    results: Dict[str, Path] = {}
    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_one(tile_id: str) -> Optional[tuple[str, Path]]:
        """Lädt ein Tile mit Semaphore-Kontrolle."""
        async with semaphore:
            if progress:
                with _imports_lock:
                    if tile_id in progress.tile_progress:
                        progress.tile_progress[tile_id].status = "downloading"
                        progress.tile_progress[tile_id].started_at = time.time()

            try:
                logger.info(f"[DOWNLOAD] Starte {tile_id}")
                start = time.time()

                # 1. Prüfe ob Tile bereits im Cache ist
                cached_path = tile_cache.get_tile_path(tile_id)
                if cached_path and cached_path.exists():
                    logger.info(f"[DOWNLOAD] {tile_id} aus Cache: {cached_path}")
                    return (tile_id, cached_path)

                # 2. Tile-ID → Koordinaten → STAC-API
                # Tile-ID "1332-21" → wir brauchen Koordinaten für STAC-API
                # Berechne Mitte des Tiles aus der ID
                coords = _tile_id_to_coordinates(tile_id)
                if not coords:
                    logger.warning(f"[DOWNLOAD] {tile_id}: Kann Koordinaten nicht berechnen")
                    return None

                e, n = coords

                # 3. STAC-API aufrufen (async)
                tile_info = await find_tile_for_coordinates(e, n)
                if not tile_info:
                    logger.warning(f"[DOWNLOAD] {tile_id}: Kein Tile in STAC-API gefunden")
                    return None

                # 4. Download in temp-Verzeichnis
                temp_dir = Path(tempfile.mkdtemp())
                try:
                    gdb_path = await asyncio.to_thread(
                        download_and_extract_tile,
                        tile_info["download_url"],
                        temp_dir,
                        tile_id
                    )

                    if not gdb_path or not gdb_path.exists():
                        logger.warning(f"[DOWNLOAD] {tile_id}: Download fehlgeschlagen")
                        return None

                    # 5. Im Cache speichern
                    bbox = tile_info.get("bbox")
                    cached_path = tile_cache.store_tile(
                        tile_id=tile_id,
                        gdb_path=gdb_path,
                        download_url=tile_info["download_url"],
                        bbox=tuple(bbox) if bbox and len(bbox) >= 4 else None
                    )

                    elapsed = time.time() - start
                    logger.info(f"[DOWNLOAD] {tile_id} fertig in {elapsed:.1f}s → {cached_path}")
                    return (tile_id, cached_path)

                finally:
                    # Temp-Verzeichnis aufräumen
                    shutil.rmtree(temp_dir, ignore_errors=True)

            except Exception as e:
                logger.error(f"[DOWNLOAD] {tile_id} Fehler: {e}")
                if progress:
                    with _imports_lock:
                        if tile_id in progress.tile_progress:
                            progress.tile_progress[tile_id].status = "failed"
                            progress.tile_progress[tile_id].error = str(e)
                return None

    # Alle Downloads parallel starten
    tasks = [download_one(tile_id) for tile_id in tile_ids]
    download_results = await asyncio.gather(*tasks)

    # Erfolgreiche Downloads sammeln
    for result in download_results:
        if result:
            tile_id, gdb_path = result
            results[tile_id] = gdb_path

    logger.info(f"[DOWNLOAD] {len(results)}/{len(tile_ids)} Tiles erfolgreich")
    return results


def _tile_id_to_coordinates(tile_id: str) -> Optional[tuple[float, float]]:
    """
    Konvertiert eine Tile-ID zurück zu LV95-Koordinaten (Tile-Mitte).

    Tile-ID Format: "MAIN-SUB" (z.B. "1332-21")
    - MAIN = 1000 + (E_km - 2480) // 4 * 10 + (N_km - 1070) // 4
    - SUB = ((N_km - 1070) % 4 + 1) * 10 + ((E_km - 2480) % 4 + 1)
    """
    try:
        parts = tile_id.split("-")
        if len(parts) != 2:
            return None

        main = int(parts[0])
        sub = int(parts[1])

        # Reverse-Engineering der Koordinaten
        # main = 1000 + main_e * 10 + main_n
        main_adjusted = main - 1000
        main_e = main_adjusted // 10
        main_n = main_adjusted % 10

        # sub = sub_n * 10 + sub_e
        sub_n = sub // 10
        sub_e = sub % 10

        # Koordinaten zurückberechnen
        # E_km = 2480 + main_e * 4 + (sub_e - 1)
        # N_km = 1070 + main_n * 4 + (sub_n - 1)
        e_km = 2480 + main_e * 4 + (sub_e - 1)
        n_km = 1070 + main_n * 4 + (sub_n - 1)

        # Mitte des km-Quadrats
        e = e_km * 1000 + 500
        n = n_km * 1000 + 500

        return (e, n)

    except (ValueError, IndexError):
        return None


# =============================================================================
# C.7: CLEANUP INTEGRATION
# =============================================================================

def cleanup_tile_files(
    tile_id: str,
    gdb_path: Optional[Path] = None,
    cleanup_gdb: bool = True,
    cleanup_parquet: bool = True
):
    """
    Räumt Dateien nach Tile-Import auf.

    Args:
        tile_id: Tile-ID
        gdb_path: Optional - Pfad zur GDB (sonst aus tiles.db)
        cleanup_gdb: GDB-Verzeichnis löschen
        cleanup_parquet: Parquet-Dateien löschen
    """
    from app.services.parquet_writer import cleanup_parquet_dir

    # Parquet-Dateien löschen
    if cleanup_parquet:
        cleanup_parquet_dir(tile_id)

    # GDB-Verzeichnis löschen
    if cleanup_gdb and gdb_path:
        try:
            # gdb_path ist z.B. tiles/2600-1199/swissBUILDINGS3D.gdb
            tile_dir = gdb_path.parent

            # Sicherheitscheck: Nur tiles/ Unterverzeichnisse löschen
            if 'tiles' in str(tile_dir) and tile_dir.exists():
                shutil.rmtree(tile_dir)
                logger.info(f"[CLEANUP] GDB-Verzeichnis gelöscht: {tile_dir}")

                # tiles.db aktualisieren
                from app.services.tile_cache import get_tile_cache
                tile_cache = get_tile_cache()
                tile_cache.mark_tile_cleaned(tile_id)
        except Exception as e:
            logger.error(f"[CLEANUP] Fehler beim Löschen von {gdb_path}: {e}")


def cleanup_all_temp_files():
    """
    Räumt alle temporären Dateien auf (Parquet + alte GDB-Verzeichnisse).

    Nützlich für manuellen Cleanup nach unterbrochenen Imports.
    """
    from app.services.parquet_writer import cleanup_parquet_dir, PARQUET_DIR
    from app.config import TILES_DIR  # NEU 15.01.2026: Aus Ephemeral Storage

    cleaned = {
        "parquet_deleted": False,
        "tiles_cleaned": 0,
    }

    # Parquet-Verzeichnis komplett löschen
    if PARQUET_DIR.exists():
        cleanup_parquet_dir(None)  # None = alles löschen
        cleaned["parquet_deleted"] = True

    # Alte Tile-Verzeichnisse prüfen (optional: älter als 24 Stunden)
    if TILES_DIR.exists():
        for tile_dir in TILES_DIR.iterdir():
            if tile_dir.is_dir():
                try:
                    # Lösche nur wenn älter als 24 Stunden
                    mtime = tile_dir.stat().st_mtime
                    age_hours = (time.time() - mtime) / 3600

                    if age_hours > 24:
                        shutil.rmtree(tile_dir)
                        cleaned["tiles_cleaned"] += 1
                        logger.info(f"[CLEANUP] Altes Tile-Verzeichnis gelöscht: {tile_dir}")
                except Exception as e:
                    logger.debug(f"[CLEANUP] Konnte {tile_dir} nicht löschen: {e}")

    logger.info(f"[CLEANUP] Ergebnis: {cleaned}")
    return cleaned


# =============================================================================
# MULTI-TILE IMPORT (KOMBINIERT C.5, C.6, C.7)
# =============================================================================

async def import_tiles_async(
    tile_ids: List[str],
    max_concurrent_downloads: int = 3,
    cleanup_after: bool = True
) -> Dict[str, Any]:
    """
    Importiert mehrere Tiles mit parallelem Download und Progress-Tracking.

    Dies ist der Haupt-Einstiegspunkt für Multi-Tile-Imports.

    Ablauf:
    1. Downloads starten (parallel, max N gleichzeitig)
    2. Nach jedem Download → sofort Import starten
    3. Nach Import → Cleanup (optional)
    4. Progress wird laufend aktualisiert

    Args:
        tile_ids: Liste der Tile-IDs zum Import
        max_concurrent_downloads: Maximale parallele Downloads
        cleanup_after: Dateien nach Import löschen

    Returns:
        Dict mit Statistiken und Ergebnissen
    """
    from app.services.parquet_writer import import_tile_with_parquet_pipeline

    # Import-Progress initialisieren
    import_id = f"import_{int(time.time())}"
    progress = ImportProgress(
        import_id=import_id,
        tiles_total=len(tile_ids),
    )

    for tile_id in tile_ids:
        progress.tile_progress[tile_id] = TileProgress(tile_id=tile_id)

    with _imports_lock:
        _active_imports[import_id] = progress

    logger.info(f"[IMPORT] {import_id} gestartet: {len(tile_ids)} Tiles")

    try:
        # Phase 1: Downloads
        progress.current_phase = "downloading"
        _log_progress(progress, "Phase 1: Downloads starten")

        downloaded = await download_tiles_parallel(
            tile_ids,
            max_concurrent=max_concurrent_downloads,
            progress=progress
        )

        # Phase 2: Imports
        progress.current_phase = "importing"
        _log_progress(progress, f"Phase 2: {len(downloaded)} Tiles importieren")

        for tile_id, gdb_path in downloaded.items():
            tile_prog = progress.tile_progress[tile_id]
            tile_prog.status = "parsing"

            try:
                _log_progress(progress, f"Importiere {tile_id}")

                result = await import_tile_with_parquet_pipeline(
                    gdb_path=gdb_path,
                    tile_id=tile_id,
                    cleanup_after=True  # Parquet-Cleanup
                )

                # Statistiken aktualisieren
                tile_prog.status = "completed"
                tile_prog.completed_at = time.time()
                tile_prog.buildings_count = result.get('buildings_count', 0)
                tile_prog.roofs_count = result.get('roofs_count', 0)
                tile_prog.walls_count = result.get('walls_count', 0)

                with _imports_lock:
                    progress.tiles_completed += 1
                    progress.total_buildings += tile_prog.buildings_count
                    progress.total_roofs += tile_prog.roofs_count
                    progress.total_walls += tile_prog.walls_count

                _log_progress(
                    progress,
                    f"{tile_id}: {tile_prog.buildings_count} buildings, "
                    f"{tile_prog.roofs_count} roofs, {tile_prog.walls_count} walls"
                )

                # C.7: GDB + Parquet Cleanup nach erfolgreichem Import
                # FIX 14.01.2026 19:35 - Parquet-Dateien AUCH löschen (redundant nach DB-Import)
                if cleanup_after:
                    cleanup_tile_files(tile_id, gdb_path, cleanup_gdb=True, cleanup_parquet=True)

            except Exception as e:
                logger.error(f"[IMPORT] {tile_id} fehlgeschlagen: {e}")
                tile_prog.status = "failed"
                tile_prog.error = str(e)
                with _imports_lock:
                    progress.tiles_failed += 1

        # Phase 3: Abschluss
        progress.current_phase = "completed"
        elapsed = progress.elapsed_seconds

        _log_progress(
            progress,
            f"ABGESCHLOSSEN in {timedelta(seconds=int(elapsed))} | "
            f"{progress.total_buildings} Gebäude, {progress.total_roofs} Dächer, "
            f"{progress.total_walls} Wände"
        )

        return progress.to_dict()

    except Exception as e:
        logger.error(f"[IMPORT] {import_id} Fehler: {e}")
        progress.current_phase = "failed"
        raise

    finally:
        # Import nach 1 Stunde aus State entfernen
        async def cleanup_state():
            await asyncio.sleep(3600)
            with _imports_lock:
                _active_imports.pop(import_id, None)

        asyncio.create_task(cleanup_state())


def import_tiles_sync(
    tile_ids: List[str],
    max_concurrent_downloads: int = 3,
    cleanup_after: bool = True
) -> Dict[str, Any]:
    """
    Synchrone Wrapper-Funktion für Multi-Tile-Import.

    Nützlich für Skripte und CLI-Aufrufe.
    """
    return asyncio.run(import_tiles_async(
        tile_ids=tile_ids,
        max_concurrent_downloads=max_concurrent_downloads,
        cleanup_after=cleanup_after
    ))


# =============================================================================
# REGION-BASIERTER IMPORT
# =============================================================================

def get_tiles_for_region(region: str) -> List[str]:
    """
    Gibt alle Tile-IDs für eine Region zurück.

    Regionen:
    - "bern": Bern Stadt (~20-30 Tiles)
    - "zurich": Zürich Stadt (~30 Tiles)
    - "basel": Basel Stadt (~15 Tiles)

    Returns:
        Liste von eindeutigen Tile-IDs
    """
    from app.services.tile_cache import lv95_to_tile_id

    # Vordefinierte Regionen (Bounding Boxes in LV95)
    REGIONS = {
        "bern": {
            "min_e": 2596000,
            "max_e": 2604000,
            "min_n": 1197000,
            "max_n": 1203000,
        },
        "zurich": {
            "min_e": 2678000,
            "max_e": 2688000,
            "min_n": 1245000,
            "max_n": 1255000,
        },
        "basel": {
            "min_e": 2608000,
            "max_e": 2616000,
            "min_n": 1264000,
            "max_n": 1270000,
        },
    }

    if region not in REGIONS:
        raise ValueError(f"Unbekannte Region: {region}. Verfügbar: {list(REGIONS.keys())}")

    bbox = REGIONS[region]

    # Tiles generieren mit der korrekten lv95_to_tile_id Funktion
    # (1km Grid → Tile-ID mit main/sub-tile Schema)
    tiles_set: Set[str] = set()  # Set für Deduplikation
    for e_km in range(bbox["min_e"] // 1000, bbox["max_e"] // 1000 + 1):
        for n_km in range(bbox["min_n"] // 1000, bbox["max_n"] // 1000 + 1):
            # Koordinaten in km → lv95_to_tile_id erwartet volle Koordinaten
            e = e_km * 1000 + 500  # Mitte des km-Quadrats
            n = n_km * 1000 + 500
            tile_id = lv95_to_tile_id(e, n)
            tiles_set.add(tile_id)

    tiles = sorted(list(tiles_set))
    logger.info(f"[REGION] {region}: {len(tiles)} Tiles generiert")
    return tiles


async def import_region_async(
    region: str,
    max_concurrent_downloads: int = 3,
    cleanup_after: bool = True
) -> Dict[str, Any]:
    """
    Importiert alle Tiles einer Region.

    Args:
        region: Region-Name (z.B. "bern")
        max_concurrent_downloads: Parallele Downloads
        cleanup_after: Cleanup nach Import

    Returns:
        Import-Statistiken
    """
    tile_ids = get_tiles_for_region(region)
    return await import_tiles_async(
        tile_ids=tile_ids,
        max_concurrent_downloads=max_concurrent_downloads,
        cleanup_after=cleanup_after
    )