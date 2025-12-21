#!/usr/bin/env python3
"""
Batch Import für alle swissBUILDINGS3D Tiles
============================================

Importiert alle Tiles aus einer URL-Liste (CSV von data.geo.admin.ch)
"""

import argparse
import os
import sys
import tempfile
import zipfile
import urllib.request
import shutil
from pathlib import Path
from datetime import datetime

# Zum Backend-Verzeichnis navigieren
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from app.services.height_db import (
    init_database,
    bulk_insert_heights,
    log_import,
    get_database_stats
)
from scripts.import_building_heights import parse_citygml


def download_and_extract(url: str, temp_dir: Path) -> Path:
    """ZIP herunterladen und entpacken"""
    zip_path = temp_dir / "tile.zip"

    # Download
    urllib.request.urlretrieve(url, zip_path)

    # Entpacken
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(temp_dir)

    # GML-Datei finden
    for f in temp_dir.glob("*.gml"):
        return f

    raise FileNotFoundError("Keine GML-Datei im ZIP gefunden")


def import_tile(gml_path: Path, source: str, batch_size: int = 5000) -> int:
    """Ein Tile importieren"""
    batch = []
    total_count = 0

    for egid, height in parse_citygml(gml_path):
        batch.append((egid, height))

        if len(batch) >= batch_size:
            bulk_insert_heights(batch, source)
            total_count += len(batch)
            batch = []

    # Restliche Daten
    if batch:
        bulk_insert_heights(batch, source)
        total_count += len(batch)

    return total_count


def main():
    parser = argparse.ArgumentParser(
        description='Importiert alle swissBUILDINGS3D Tiles aus einer URL-Liste'
    )
    parser.add_argument('url_file', type=Path, help='CSV-Datei mit Download-URLs')
    parser.add_argument('--canton', type=str, default='BE', help='Kanton')
    parser.add_argument('--start', type=int, default=0, help='Start bei Tile Nr.')
    parser.add_argument('--limit', type=int, default=0, help='Max. Anzahl Tiles (0=alle)')
    parser.add_argument('--keep-temp', action='store_true', help='Temp-Dateien behalten')

    args = parser.parse_args()

    if not args.url_file.exists():
        print(f"[FEHLER] Datei nicht gefunden: {args.url_file}")
        sys.exit(1)

    # URLs lesen
    with open(args.url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and line.startswith('http')]

    print(f"\n=== swissBUILDINGS3D Batch Import ===")
    print(f"Kanton: {args.canton}")
    print(f"Tiles gefunden: {len(urls)}")
    print(f"Start bei: {args.start}")
    if args.limit:
        print(f"Limit: {args.limit} Tiles")
    print()

    # Datenbank initialisieren
    init_database()

    # Subset auswählen
    if args.start > 0:
        urls = urls[args.start:]
    if args.limit > 0:
        urls = urls[:args.limit]

    total_tiles = len(urls)
    total_buildings = 0
    failed_tiles = []
    start_time = datetime.now()

    source = f"swissBUILDINGS3D_3.0_{args.canton}"

    for i, url in enumerate(urls, 1):
        tile_name = url.split('/')[-2]  # z.B. swissbuildings3d_3_0_2021_1166-24

        print(f"\n[{i}/{total_tiles}] {tile_name}")

        # Temp-Verzeichnis erstellen
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Download und Entpacken
            print(f"  Downloading...")
            gml_path = download_and_extract(url, temp_dir)

            # Import
            count = import_tile(gml_path, source)
            total_buildings += count
            print(f"  -> {count:,} Gebaeude importiert")

            # Fortschritt
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = total_buildings / elapsed if elapsed > 0 else 0
            remaining = (total_tiles - i) * (elapsed / i) if i > 0 else 0
            print(f"  Gesamt: {total_buildings:,} | {rate:.0f} Geb./s | ~{remaining/60:.0f} Min. verbleibend")

        except Exception as e:
            print(f"  [FEHLER] {e}")
            failed_tiles.append((tile_name, str(e)))

        finally:
            # Aufräumen
            if not args.keep_temp:
                shutil.rmtree(temp_dir, ignore_errors=True)

    # Zusammenfassung
    elapsed_total = (datetime.now() - start_time).total_seconds()

    print(f"\n{'='*50}")
    print(f"[OK] Import abgeschlossen!")
    print(f"  Tiles verarbeitet: {total_tiles - len(failed_tiles)}/{total_tiles}")
    print(f"  Gebaeude importiert: {total_buildings:,}")
    print(f"  Dauer: {elapsed_total/60:.1f} Minuten")

    if failed_tiles:
        print(f"\n  Fehlgeschlagene Tiles ({len(failed_tiles)}):")
        for name, error in failed_tiles[:10]:
            print(f"    - {name}: {error}")
        if len(failed_tiles) > 10:
            print(f"    ... und {len(failed_tiles) - 10} weitere")

    # Log
    log_import(
        source_file=f"batch_import_{args.canton}_{total_tiles}_tiles",
        canton=args.canton,
        records=total_buildings,
        version="3.0"
    )

    # Finale Statistik
    stats = get_database_stats()
    print(f"\n  Datenbank enthaelt jetzt {stats.get('records', 0):,} Gebaeude")
    print(f"  Datenbankgroesse: {stats.get('db_size_mb', 0):.1f} MB")


if __name__ == '__main__':
    main()
