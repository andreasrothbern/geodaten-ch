#!/usr/bin/env python3
"""
Batch Import für swissBUILDINGS3D Tiles
=======================================

Robustes Import-Skript basierend auf den bestehenden Services:
- tile_cache.py: Tile-Metadaten + GDB-Cache
- tile_prefetch.py: GDB-Parsing (Fiona Streaming)
- building_3d_service.py: Bulk-Insert mit Optimierungen
- swissbuildings3d_fetcher.py: STAC API

Verwendung:
    # Status anzeigen
    python -m scripts.batch.import_tiles --status

    # Einzelnes Tile importieren
    python -m scripts.batch.import_tiles --tile 1332-21

    # Region importieren (BBox)
    python -m scripts.batch.import_tiles --region bern

    # Alle Tiles in einer URL-Liste importieren
    python -m scripts.batch.import_tiles --url-file tiles.csv

    # Nur neue/geänderte Tiles (inkrementell)
    python -m scripts.batch.import_tiles --update

    # Mit Parallelisierung
    python -m scripts.batch.import_tiles --region bern --workers 4
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Backend-Verzeichnis zum Path hinzufügen
script_dir = Path(__file__).parent
backend_dir = script_dir.parent.parent
sys.path.insert(0, str(backend_dir))

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Services importieren
from app.services.tile_cache import get_tile_cache, lv95_to_tile_id, TILES_DIR
from app.services.tile_prefetch import _parse_all_buildings_from_gdb
from app.services.building_3d_service import get_building_3d_service

# Regionen-Definitionen (BBox in LV95)
REGIONS = {
    "bern": {
        "name": "Stadt Bern",
        "bbox": (2596000, 1197000, 2604000, 1203000),  # ~8x6 km
        "expected_tiles": 20
    },
    "bern_region": {
        "name": "Region Bern",
        "bbox": (2590000, 1190000, 2610000, 1210000),  # ~20x20 km
        "expected_tiles": 100
    },
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
    "test": {
        "name": "Test (1 Tile Bern)",
        "bbox": (2600000, 1199000, 2601000, 1200000),  # 1x1 km - ACHTUNG: Bern!
        "expected_tiles": 1
    },
    "basel_test": {
        "name": "Basel Test (1 Tile)",
        "bbox": (2610000, 1266000, 2611000, 1267000),  # 1x1 km - Separates Testgebiet
        "expected_tiles": 1
    }
}

# STAC API
STAC_API_BASE = "https://data.geo.admin.ch/api/stac/v0.9"
COLLECTION_ID = "ch.swisstopo.swissbuildings3d_3_0"


class TileImporter:
    """Batch-Importer für swissBUILDINGS3D Tiles."""

    def __init__(self, workers: int = 1, dry_run: bool = False):
        self.workers = workers
        self.dry_run = dry_run
        self.tile_cache = get_tile_cache()
        self.building_service = get_building_3d_service()

        # Statistiken
        self.stats = {
            "tiles_processed": 0,
            "tiles_skipped": 0,
            "tiles_failed": 0,
            "buildings_imported": 0,
            "start_time": None,
            "errors": []
        }

    def get_tiles_for_region(self, region_name: str) -> List[str]:
        """
        Berechnet alle Tile-IDs für eine Region.

        Args:
            region_name: Name der Region (z.B. 'bern')

        Returns:
            Liste von Tile-IDs
        """
        if region_name not in REGIONS:
            raise ValueError(f"Unbekannte Region: {region_name}. Verfügbar: {list(REGIONS.keys())}")

        region = REGIONS[region_name]
        bbox = region["bbox"]

        tiles = set()

        # 1km Raster durchgehen
        e = bbox[0]
        while e < bbox[2]:
            n = bbox[1]
            while n < bbox[3]:
                tile_id = lv95_to_tile_id(e + 500, n + 500)  # Mitte des km-Quadrats
                tiles.add(tile_id)
                n += 1000
            e += 1000

        logger.info(f"Region '{region['name']}': {len(tiles)} Tiles gefunden")
        return sorted(list(tiles))

    def get_tiles_from_url_file(self, url_file: Path) -> List[Tuple[str, str]]:
        """
        Liest Tile-URLs aus einer CSV-Datei.

        Args:
            url_file: Pfad zur CSV-Datei

        Returns:
            Liste von (tile_id, download_url) Tupeln
        """
        tiles = []

        with open(url_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith('http'):
                    continue

                # Tile-ID aus URL extrahieren
                # Format: .../swissbuildings3d_3_0_2021_1332-21/...
                parts = line.split('/')
                for part in parts:
                    if part.startswith('swissbuildings3d'):
                        # z.B. swissbuildings3d_3_0_2021_1332-21
                        tile_part = part.split('_')[-1]  # 1332-21
                        tiles.append((tile_part, line))
                        break

        logger.info(f"URL-Datei: {len(tiles)} Tiles gefunden")
        return tiles

    async def discover_tiles_from_stac(
        self,
        bbox: Tuple[float, float, float, float]
    ) -> List[Dict[str, Any]]:
        """
        Findet alle Tiles in einer BBox via STAC API.

        Args:
            bbox: (west, south, east, north) in LV95

        Returns:
            Liste von STAC Items
        """
        import httpx

        # LV95 → WGS84 konvertieren
        def lv95_to_wgs84(e: float, n: float) -> Tuple[float, float]:
            y = (e - 2600000) / 1000000
            x = (n - 1200000) / 1000000
            lon = (2.6779094 + 4.728982 * y + 0.791484 * y * x +
                   0.1306 * y * x * x - 0.0436 * y * y * y) * 100 / 36
            lat = (16.9023892 + 3.238272 * x - 0.270978 * y * y -
                   0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x * x * x) * 100 / 36
            return lon, lat

        lon_min, lat_min = lv95_to_wgs84(bbox[0], bbox[1])
        lon_max, lat_max = lv95_to_wgs84(bbox[2], bbox[3])

        bbox_wgs84 = f"{lon_min},{lat_min},{lon_max},{lat_max}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{STAC_API_BASE}/collections/{COLLECTION_ID}/items"
            params = {"bbox": bbox_wgs84, "limit": 500}

            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            items = data.get("features", [])

            logger.info(f"STAC API: {len(items)} Tiles in BBox gefunden")
            return items

    async def download_tile(self, tile_id: str, download_url: str = None) -> Optional[Path]:
        """
        Lädt ein Tile herunter und cached es.

        Args:
            tile_id: Tile-Referenz (z.B. "1332-21")
            download_url: Optionale Download-URL (sonst STAC Discovery)

        Returns:
            Pfad zum gecachten GDB oder None bei Fehler
        """
        import tempfile
        import zipfile
        import urllib.request
        import shutil

        # Prüfen ob bereits gecacht
        cached_path = self.tile_cache.get_tile_path(tile_id)
        if cached_path and cached_path.exists():
            logger.debug(f"Tile {tile_id} bereits im Cache")
            return cached_path

        if self.dry_run:
            logger.info(f"[DRY-RUN] Würde Tile {tile_id} herunterladen")
            return None

        # Download-URL finden falls nicht angegeben
        if not download_url:
            download_url = await self._find_download_url(tile_id)
            if not download_url:
                logger.warning(f"Keine Download-URL für Tile {tile_id} gefunden")
                return None

        logger.info(f"Downloading Tile {tile_id}...")

        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Download
            zip_path = temp_dir / "tile.zip"
            urllib.request.urlretrieve(download_url, zip_path)

            # Entpacken
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)

            # GDB finden
            gdb_path = None
            for item in temp_dir.iterdir():
                if item.is_dir() and item.suffix.lower() == '.gdb':
                    gdb_path = item
                    break

            if not gdb_path:
                raise FileNotFoundError(f"Keine GDB in {tile_id} gefunden")

            # Im Cache speichern
            cached_path = self.tile_cache.store_tile(
                tile_id=tile_id,
                gdb_path=gdb_path,
                download_url=download_url
            )

            logger.info(f"Tile {tile_id} gecacht: {cached_path}")
            return cached_path

        except Exception as e:
            logger.error(f"Download-Fehler für {tile_id}: {e}")
            self.stats["errors"].append((tile_id, str(e)))
            return None

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _find_download_url(self, tile_id: str) -> Optional[str]:
        """Findet Download-URL für ein Tile via STAC API."""
        import httpx

        # Tile-ID zu Koordinaten (Mitte des Tiles)
        # Format: 1332-21 → main=1332, sub=21
        parts = tile_id.split('-')
        if len(parts) != 2:
            return None

        try:
            main = int(parts[0])
            sub = int(parts[1])
        except ValueError:
            return None

        # Koordinaten berechnen (Rückrechnung)
        main_e = (main - 1000) // 10
        main_n = (main - 1000) % 10
        sub_e = sub % 10
        sub_n = sub // 10

        e = 2480000 + main_e * 4000 + (sub_e - 1) * 1000 + 500
        n = 1070000 + main_n * 4000 + (sub_n - 1) * 1000 + 500

        # STAC Query
        items = await self.discover_tiles_from_stac((e - 500, n - 500, e + 500, n + 500))

        for item in items:
            assets = item.get("assets", {})
            for asset_name, asset in assets.items():
                if "gdb" in asset_name.lower() or "geodatabase" in asset_name.lower():
                    return asset.get("href")

            # Fallback: Erster Download-Link
            for asset in assets.values():
                href = asset.get("href", "")
                if href.endswith(".zip"):
                    return href

        return None

    def import_tile(self, tile_id: str, gdb_path: Path) -> int:
        """
        Importiert alle Gebäude aus einem Tile.

        Args:
            tile_id: Tile-Referenz
            gdb_path: Pfad zum GDB-Verzeichnis

        Returns:
            Anzahl importierter Gebäude
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Würde Tile {tile_id} importieren")
            return 0

        logger.info(f"Parsing Tile {tile_id}...")
        start = time.time()

        # GDB parsen (nutzt Fiona Streaming)
        buildings = _parse_all_buildings_from_gdb(gdb_path)

        parse_time = time.time() - start
        logger.info(f"  Parsed: {len(buildings)} Gebäude in {parse_time:.1f}s")

        if not buildings:
            return 0

        # Tile-ID setzen
        for b in buildings:
            b["tile_id"] = tile_id

        # Bulk-Save
        start = time.time()
        saved = self.building_service.bulk_save(buildings, tile_id)
        save_time = time.time() - start

        logger.info(f"  Saved: {saved} Gebäude in {save_time:.1f}s")

        return saved

    async def process_tile(self, tile_id: str, download_url: str = None) -> Tuple[str, int, str]:
        """
        Verarbeitet ein einzelnes Tile (Download + Import).

        Returns:
            (tile_id, building_count, status)
        """
        try:
            # Download
            gdb_path = await self.download_tile(tile_id, download_url)
            if not gdb_path:
                return (tile_id, 0, "skipped")

            # Import
            count = self.import_tile(tile_id, gdb_path)
            return (tile_id, count, "ok")

        except Exception as e:
            logger.error(f"Fehler bei Tile {tile_id}: {e}")
            self.stats["errors"].append((tile_id, str(e)))
            return (tile_id, 0, "error")

    async def run_import(
        self,
        tile_ids: List[str] = None,
        tile_urls: List[Tuple[str, str]] = None,
        region: str = None
    ):
        """
        Führt den Batch-Import aus.

        Args:
            tile_ids: Liste von Tile-IDs
            tile_urls: Liste von (tile_id, url) Tupeln
            region: Region-Name
        """
        self.stats["start_time"] = datetime.now()

        # Tiles sammeln
        if region:
            tile_ids = self.get_tiles_for_region(region)
            tile_urls = [(tid, None) for tid in tile_ids]
        elif tile_ids:
            tile_urls = [(tid, None) for tid in tile_ids]
        elif not tile_urls:
            logger.error("Keine Tiles angegeben")
            return

        total = len(tile_urls)
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH IMPORT: {total} Tiles")
        logger.info(f"Workers: {self.workers}")
        logger.info(f"Dry-Run: {self.dry_run}")
        logger.info(f"{'='*60}\n")

        # Index vor Import droppen (schneller)
        if not self.dry_run and total > 5:
            logger.info("Dropping indexes for faster import...")
            self.building_service.drop_indexes()

        # Import durchführen
        if self.workers > 1:
            # Parallel
            await self._run_parallel(tile_urls)
        else:
            # Sequentiell
            await self._run_sequential(tile_urls)

        # Index nach Import erstellen
        if not self.dry_run and total > 5:
            logger.info("Creating indexes...")
            self.building_service.create_indexes()

        # Zusammenfassung
        self._print_summary()

    async def _run_sequential(self, tile_urls: List[Tuple[str, str]]):
        """Sequentieller Import."""
        for i, (tile_id, url) in enumerate(tile_urls, 1):
            logger.info(f"\n[{i}/{len(tile_urls)}] {tile_id}")

            tile_id, count, status = await self.process_tile(tile_id, url)

            if status == "ok":
                self.stats["tiles_processed"] += 1
                self.stats["buildings_imported"] += count
            elif status == "skipped":
                self.stats["tiles_skipped"] += 1
            else:
                self.stats["tiles_failed"] += 1

    async def _run_parallel(self, tile_urls: List[Tuple[str, str]]):
        """Paralleler Import mit asyncio."""
        semaphore = asyncio.Semaphore(self.workers)

        async def process_with_semaphore(tile_id: str, url: str, index: int):
            async with semaphore:
                logger.info(f"[{index}/{len(tile_urls)}] Processing {tile_id}")
                return await self.process_tile(tile_id, url)

        tasks = [
            process_with_semaphore(tid, url, i)
            for i, (tid, url) in enumerate(tile_urls, 1)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self.stats["tiles_failed"] += 1
                self.stats["errors"].append(("unknown", str(result)))
            else:
                tile_id, count, status = result
                if status == "ok":
                    self.stats["tiles_processed"] += 1
                    self.stats["buildings_imported"] += count
                elif status == "skipped":
                    self.stats["tiles_skipped"] += 1
                else:
                    self.stats["tiles_failed"] += 1

    def _print_summary(self):
        """Druckt Zusammenfassung."""
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()

        print(f"\n{'='*60}")
        print("IMPORT ABGESCHLOSSEN")
        print(f"{'='*60}")
        print(f"  Tiles verarbeitet: {self.stats['tiles_processed']}")
        print(f"  Tiles übersprungen: {self.stats['tiles_skipped']}")
        print(f"  Tiles fehlgeschlagen: {self.stats['tiles_failed']}")
        print(f"  Gebäude importiert: {self.stats['buildings_imported']:,}")
        print(f"  Dauer: {elapsed/60:.1f} Minuten")

        if self.stats['buildings_imported'] > 0 and elapsed > 0:
            rate = self.stats['buildings_imported'] / elapsed
            print(f"  Rate: {rate:.0f} Gebäude/Sekunde")

        if self.stats["errors"]:
            print(f"\n  Fehler ({len(self.stats['errors'])}):")
            for tile_id, error in self.stats["errors"][:5]:
                print(f"    - {tile_id}: {error}")
            if len(self.stats["errors"]) > 5:
                print(f"    ... und {len(self.stats['errors']) - 5} weitere")

        # DB-Statistiken
        stats = self.building_service.get_stats()
        print(f"\n  Datenbank enthält jetzt:")
        print(f"    {stats['total_buildings']:,} Gebäude")
        print(f"    {stats['total_tiles']} Tiles")
        print(f"{'='*60}\n")


def show_status():
    """Zeigt aktuellen Status der Datenbanken."""
    tile_cache = get_tile_cache()
    building_service = get_building_3d_service()

    cache_stats = tile_cache.get_stats()
    building_stats = building_service.get_stats()

    print(f"\n{'='*60}")
    print("DATENBANK-STATUS")
    print(f"{'='*60}")

    print(f"\ntiles.db:")
    print(f"  Tiles gecacht: {cache_stats['tile_count']}")
    print(f"  Gesamtgrösse: {cache_stats['total_size_mb']:.1f} MB")
    print(f"  Pfad: {cache_stats['db_path']}")

    print(f"\nbuilding_3d.db:")
    print(f"  Gebäude: {building_stats['total_buildings']:,}")
    print(f"  Tiles: {building_stats['total_tiles']}")
    print(f"  Pfad: {building_stats['db_path']}")

    if building_stats['top_tiles']:
        print(f"\n  Top 5 Tiles:")
        for tile in building_stats['top_tiles']:
            print(f"    {tile['tile_id']}: {tile['count']:,} Gebäude")

    if cache_stats['recent_tiles']:
        print(f"\n  Letzte Downloads:")
        for tile in cache_stats['recent_tiles']:
            print(f"    {tile['tile_id']}: {tile['downloaded_at']}")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Batch-Import für swissBUILDINGS3D Tiles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Status anzeigen
  python -m scripts.batch.import_tiles --status

  # Einzelnes Tile
  python -m scripts.batch.import_tiles --tile 1332-21

  # Region Bern
  python -m scripts.batch.import_tiles --region bern

  # Parallel mit 4 Workern
  python -m scripts.batch.import_tiles --region bern --workers 4

  # Aus URL-Datei
  python -m scripts.batch.import_tiles --url-file tiles.csv

Verfügbare Regionen: """ + ", ".join(REGIONS.keys())
    )

    parser.add_argument('--status', action='store_true',
                        help='Zeigt Datenbank-Status')
    parser.add_argument('--tile', type=str,
                        help='Einzelnes Tile importieren (z.B. 1332-21)')
    parser.add_argument('--tiles', type=str,
                        help='Mehrere Tiles (kommasepariert)')
    parser.add_argument('--region', type=str, choices=list(REGIONS.keys()),
                        help='Region importieren')
    parser.add_argument('--url-file', type=Path,
                        help='CSV-Datei mit Download-URLs')
    parser.add_argument('--workers', type=int, default=1,
                        help='Anzahl paralleler Worker (default: 1)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Nur simulieren, nichts herunterladen')

    args = parser.parse_args()

    # Status anzeigen
    if args.status:
        show_status()
        return

    # Importer erstellen
    importer = TileImporter(workers=args.workers, dry_run=args.dry_run)

    # Import starten
    if args.tile:
        asyncio.run(importer.run_import(tile_ids=[args.tile]))
    elif args.tiles:
        tile_list = [t.strip() for t in args.tiles.split(',')]
        asyncio.run(importer.run_import(tile_ids=tile_list))
    elif args.region:
        asyncio.run(importer.run_import(region=args.region))
    elif args.url_file:
        if not args.url_file.exists():
            logger.error(f"Datei nicht gefunden: {args.url_file}")
            sys.exit(1)
        tile_urls = importer.get_tiles_from_url_file(args.url_file)
        asyncio.run(importer.run_import(tile_urls=tile_urls))
    else:
        parser.print_help()
        print("\nFehler: Mindestens --tile, --tiles, --region oder --url-file angeben")
        sys.exit(1)


if __name__ == '__main__':
    main()
