"""
Test swissBUILDINGS3D Polygon-Extraktion für Luzern.
Luzern hatte vorher keine Polygon-Daten (geodienste.ch nicht verfügbar).
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.height_fetcher import fetch_building_polygon_for_coordinates
from app.services.swisstopo import SwisstopoService


async def test_polygon_extraction():
    """Test polygon extraction for multiple addresses."""

    addresses = [
        # Luzern - vorher nicht möglich
        "Pilatusstrasse 1, 6003 Luzern",
        # Bern - sollte weiterhin funktionieren
        "Bundesplatz 3, 3011 Bern",
        # Genf - vorher nicht möglich
        "Rue du Rhône 50, 1204 Genève",
    ]

    swisstopo = SwisstopoService()

    for address in addresses:
        print(f"\n{'='*60}")
        print(f"Adresse: {address}")
        print('='*60)

        try:
            # Geocode
            geocode = await swisstopo.geocode(address)
            if not geocode:
                print("  FEHLER: Geocoding fehlgeschlagen")
                continue

            print(f"  Koordinaten: E={geocode.coordinates.lv95_e:.1f}, N={geocode.coordinates.lv95_n:.1f}")

            # Polygon abrufen
            result = await fetch_building_polygon_for_coordinates(
                e=geocode.coordinates.lv95_e,
                n=geocode.coordinates.lv95_n,
                tolerance_m=50.0
            )

            if result:
                print(f"  ✅ Polygon gefunden!")
                print(f"     Punkte: {len(result.get('polygon', []))}")
                print(f"     Seiten: {len(result.get('sides', []))}")
                print(f"     Umfang: {result.get('perimeter_m')} m")
                print(f"     Fläche: {result.get('area_m2')} m²")
                print(f"     Traufhöhe: {result.get('traufhoehe_m')} m")
                print(f"     Firsthöhe: {result.get('firsthoehe_m')} m")
                print(f"     Match-Distanz: {result.get('match_distance_m')} m")
                print(f"     EGID: {result.get('egid')}")
                print(f"     Quelle: {result.get('source')}")
                print(f"     Tile: {result.get('tile_id')}")
            else:
                print("  ❌ Kein Polygon gefunden")

        except Exception as e:
            print(f"  FEHLER: {e}")


if __name__ == "__main__":
    print("Test: swissBUILDINGS3D Polygon-Extraktion")
    print("Ersetzt geodienste.ch für ALLE Kantone\n")
    asyncio.run(test_polygon_extraction())
