#!/usr/bin/env python
"""
Test-Script fuer swissBUILDINGS3D Composite Service.

Testet den kombinierten Service mit:
- Polygon von geodienste.ch WFS
- Hoehen aus lokaler SQLite DB
- Dachflaechen von sonnendach.ch

Verwendung:
    cd backend
    python scripts/test_swissbuildings3d.py
"""

import asyncio
import sys
from pathlib import Path

# Backend-Pfad hinzufuegen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.swissbuildings3d_service import (
    get_swissbuildings3d_service,
    Building3D
)
from app.services.sonnendach_service import (
    get_sonnendach_service,
    RoofAnalysis
)
from app.services.height_db import get_database_stats


# Test-Koordinaten (LV95)
TEST_BUILDINGS = [
    {
        "name": "Bundeshaus Bern",
        "e": 2600423,
        "n": 1199521,
        "expected_polygon_min_points": 4,
    },
    {
        "name": "Zytglogge Bern",
        "e": 2600656,
        "n": 1199736,
        "expected_polygon_min_points": 4,
    },
    {
        "name": "Kramgasse 10, Bern",
        "e": 2600668,
        "n": 1199600,
        "expected_polygon_min_points": 4,
    },
    {
        "name": "Rathaus Bern",
        "e": 2600550,
        "n": 1199750,
        "expected_polygon_min_points": 4,
    },
]


async def test_composite_service():
    """Testet den kombinierten swissBUILDINGS3D Service."""
    print("=" * 60)
    print("TEST: swissBUILDINGS3D Composite Service")
    print("=" * 60)
    print()
    print("Datenquellen:")
    print("  - Polygon: geodienste.ch WFS (Live-API)")
    print("  - Hoehen: Lokale SQLite DB (falls importiert)")
    print("  - Dachflaechen: sonnendach.ch API (Live-API)")
    print()

    # DB-Status anzeigen
    db_stats = get_database_stats()
    if db_stats.get("exists"):
        print(f"Hoehendatenbank: {db_stats.get('records', 0)} Eintraege")
    else:
        print("[INFO] Hoehendatenbank nicht vorhanden - Hoehen werden nicht gefunden")
    print()

    service = get_swissbuildings3d_service()
    results = []

    for building in TEST_BUILDINGS:
        print(f"[BUILDING] {building['name']}")
        print(f"   Koordinaten: E={building['e']}, N={building['n']}")

        try:
            result = await service.get_building_by_coordinates(
                building['e'],
                building['n'],
                include_roof_analysis=True
            )

            if result:
                print(f"   [OK] Daten gefunden!")

                # Polygon
                if result.polygon:
                    print(f"   - Polygon: {len(result.polygon)} Punkte")
                    if len(result.polygon) >= building['expected_polygon_min_points']:
                        print(f"   - Perimeter: {result.perimeter_m:.1f} m")
                        print(f"   - Flaeche: {result.area_m2:.1f} m2")
                        print(f"   - Fassaden: {len(result.sides)} Seiten")
                else:
                    print(f"   - Polygon: [WARN] Nicht gefunden")

                # Hoehen
                if result.has_valid_heights():
                    print(f"   - Traufhoehe: {result.trauf_height_m:.1f} m")
                    print(f"   - Firsthoehe: {result.first_height_m:.1f} m")
                    print(f"   - Hoehenquelle: {result.height_source}")
                else:
                    print(f"   - Hoehen: [INFO] Nicht in DB (Import erforderlich)")

                # Dach
                if result.roof_type:
                    print(f"   - Dachtyp: {result.roof_type}")
                if result.roof_surfaces:
                    print(f"   - Dachflaechen: {len(result.roof_surfaces)} von sonnendach.ch")

                # Bewertung
                if result.polygon:
                    results.append(("PASS", building['name'], "Polygon gefunden"))
                else:
                    results.append(("WARN", building['name'], "Kein Polygon"))

            else:
                print(f"   [FAIL] Keine Daten gefunden")
                results.append(("FAIL", building['name'], "Keine Daten"))

        except Exception as e:
            print(f"   [ERROR] Fehler: {e}")
            results.append(("ERROR", building['name'], str(e)))

        print()

    return results


async def test_sonnendach_standalone():
    """Testet Sonnendach Service separat."""
    print("=" * 60)
    print("TEST: Sonnendach.ch Service (separat)")
    print("=" * 60)

    service = get_sonnendach_service()
    results = []

    for building in TEST_BUILDINGS[:2]:  # Nur erste 2 testen
        print(f"\n[BUILDING] {building['name']}")
        print(f"   Koordinaten: E={building['e']}, N={building['n']}")

        try:
            analysis = await service.analyze_roof(
                building['e'],
                building['n']
            )

            if analysis.has_data:
                print(f"   [OK] Dachflaechen gefunden!")
                print(f"   - Anzahl Flaechen: {analysis.surfaces_count}")
                print(f"   - Gesamtflaeche: {analysis.total_area_m2} m2")
                print(f"   - Hauptausrichtung: {analysis.main_orientation or 'N/A'}")
                print(f"   - Hauptneigung: {analysis.main_tilt_degrees or 'N/A'} Grad")
                print(f"   - Dachtyp: {analysis.roof_type}")

                for i, surface in enumerate(analysis.surfaces[:3], 1):
                    print(f"   - Flaeche {i}: {surface.area_m2}m2, {surface.tilt_degrees} Grad, {surface.eignung}")

                results.append(("PASS", building['name']))
            else:
                print(f"   [WARN] Keine Dachflaechen gefunden")
                results.append(("WARN", building['name']))

        except Exception as e:
            print(f"   [ERROR] Fehler: {e}")
            results.append(("ERROR", building['name']))

    return results


async def main():
    """Hauptfunktion."""
    print("\n" + "=" * 60)
    print("  swissBUILDINGS3D + Sonnendach Integration Test")
    print("=" * 60)

    all_results = []

    # Tests ausfuehren
    results1 = await test_composite_service()
    all_results.extend(results1)

    results2 = await test_sonnendach_standalone()
    all_results.extend([(r[0], r[1], "") for r in results2])

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)

    passed = sum(1 for r in all_results if r[0] == "PASS")
    warned = sum(1 for r in all_results if r[0] == "WARN")
    failed = sum(1 for r in all_results if r[0] in ("FAIL", "ERROR"))
    total = len(all_results)

    print(f"\n[PASS] Erfolgreich: {passed}/{total}")
    print(f"[WARN] Warnungen: {warned}/{total}")
    print(f"[FAIL] Fehlgeschlagen: {failed}/{total}")

    print("\n" + "-" * 60)
    print("HINWEISE:")
    print("-" * 60)
    print("- Polygon-Daten: geodienste.ch WFS (funktioniert fuer BE, SO, BS, etc.)")
    print("- Hoehendaten: Muessen erst aus swissBUILDINGS3D importiert werden")
    print("  -> python scripts/import_building_heights.py daten.gml --canton BE")
    print("- Dachflaechen: sonnendach.ch API (schweizweit verfuegbar)")

    if failed == 0:
        print("\n*** Alle Tests bestanden! ***")
        return 0
    else:
        print("\n*** Einige Tests fehlgeschlagen. Siehe Details oben. ***")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
