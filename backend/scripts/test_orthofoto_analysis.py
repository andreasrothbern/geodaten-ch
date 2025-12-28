"""
Test-Script für Orthofoto-Analyse Integration

Testet die Claude-Analyse mit und ohne Orthofoto für ein bekanntes Gebäude.

Ausführung:
    cd backend
    python scripts/test_orthofoto_analysis.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.services.building_context import get_building_context_service
from app.services.swisstopo import SwisstopoService
from app.services.geodienste import GeodiensteService
from app.services.orthofoto import get_orthofoto_service
import json


async def test_orthofoto_service():
    """Testet den Orthofoto-Service direkt"""
    print("=" * 60)
    print("TEST 1: Orthofoto-Service direkt")
    print("=" * 60)

    orthofoto_service = get_orthofoto_service()

    # Bundeshaus Koordinaten
    center_e = 2600450
    center_n = 1199830

    result = await orthofoto_service.get_orthofoto(
        center_e=center_e,
        center_n=center_n,
        width_m=100,
        height_m=100,
        resolution_m=0.5
    )

    if result:
        print(f"✓ Orthofoto geladen: {result.width_px}x{result.height_px}px")
        print(f"  Auflösung: {result.resolution_m}m/px")
        print(f"  Base64-Länge: {len(result.image_base64)} Zeichen")
        print(f"  Media-Type: {result.media_type}")
    else:
        print("✗ Orthofoto konnte nicht geladen werden")

    return result is not None


async def test_building_context_without_orthofoto():
    """Testet die Claude-Analyse ohne Orthofoto"""
    print("\n" + "=" * 60)
    print("TEST 2: Claude-Analyse OHNE Orthofoto")
    print("=" * 60)

    # Services initialisieren
    swisstopo = SwisstopoService()
    geodienste = GeodiensteService()
    context_service = get_building_context_service()

    # Test-Adresse
    address = "Kramgasse 10, 3011 Bern"
    print(f"\nAdresse: {address}")

    # Geocoding
    geo_result = await swisstopo.geocode(address)
    if not geo_result:
        print("✗ Geocoding fehlgeschlagen")
        return False

    print(f"✓ Geocoding: E={geo_result.coordinates.lv95_e}, N={geo_result.coordinates.lv95_n}")

    # Gebäude-Geometrie
    geometry = await geodienste.get_building_geometry(
        x=geo_result.coordinates.lv95_e,
        y=geo_result.coordinates.lv95_n,
        tolerance=50,
        egid=geo_result.gwr_data.egid if geo_result.gwr_data else None
    )

    if not geometry:
        print("✗ Keine Gebäudegeometrie gefunden")
        return False

    print(f"✓ Geometrie: {len(geometry.polygon)} Punkte")

    # Polygon formatieren
    polygon = [{"x": p[0], "y": p[1]} for p in geometry.polygon]

    # Höhendaten
    height_data = {
        "traufhoehe_m": geometry.heights.get("traufhoehe_m") if geometry.heights else None,
        "firsthoehe_m": geometry.heights.get("firsthoehe_m") if geometry.heights else None,
        "gebaeudehoehe_m": geometry.heights.get("gebaeudehoehe_m") if geometry.heights else None
    }
    print(f"✓ Höhen: Traufe={height_data['traufhoehe_m']}m, First={height_data['firsthoehe_m']}m")

    # GWR-Daten
    gwr_data = geo_result.gwr_data.model_dump() if geo_result.gwr_data else None

    # EGID
    egid = str(geo_result.gwr_data.egid) if geo_result.gwr_data else "unknown"

    print("\nStarte Claude-Analyse (ohne Orthofoto)...")

    try:
        context = await context_service.analyze_with_claude(
            egid=egid,
            adresse=address,
            polygon=polygon,
            height_data=height_data,
            gwr_data=gwr_data,
            include_orthofoto=False
        )

        print(f"\n✓ Analyse abgeschlossen:")
        print(f"  Komplexität: {context.complexity.value}")
        print(f"  Zonen: {len(context.zones)}")
        for zone in context.zones:
            print(f"    - {zone.name}: {zone.type.value}, {zone.gebaeudehoehe_m}m")
        print(f"  Konfidenz: {context.confidence}")
        print(f"  Orthofoto-Analyse: {context.has_orthofoto_analysis}")

        return True

    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


async def test_building_context_with_orthofoto():
    """Testet die Claude-Analyse MIT Orthofoto"""
    print("\n" + "=" * 60)
    print("TEST 3: Claude-Analyse MIT Orthofoto")
    print("=" * 60)

    # Services initialisieren
    swisstopo = SwisstopoService()
    geodienste = GeodiensteService()
    context_service = get_building_context_service()

    # Test-Adresse (U-förmiges Gebäude mit Innenhof)
    address = "Münsterplatz 1, 3011 Bern"  # Berner Münster
    print(f"\nAdresse: {address}")

    # Geocoding
    geo_result = await swisstopo.geocode(address)
    if not geo_result:
        print("✗ Geocoding fehlgeschlagen")
        return False

    print(f"✓ Geocoding: E={geo_result.coordinates.lv95_e}, N={geo_result.coordinates.lv95_n}")

    # Gebäude-Geometrie
    geometry = await geodienste.get_building_geometry(
        x=geo_result.coordinates.lv95_e,
        y=geo_result.coordinates.lv95_n,
        tolerance=50,
        egid=geo_result.gwr_data.egid if geo_result.gwr_data else None
    )

    if not geometry:
        print("✗ Keine Gebäudegeometrie gefunden")
        return False

    print(f"✓ Geometrie: {len(geometry.polygon)} Punkte")

    # Polygon formatieren
    polygon = [{"x": p[0], "y": p[1]} for p in geometry.polygon]

    # Höhendaten
    height_data = {
        "traufhoehe_m": geometry.heights.get("traufhoehe_m") if geometry.heights else None,
        "firsthoehe_m": geometry.heights.get("firsthoehe_m") if geometry.heights else None,
        "gebaeudehoehe_m": geometry.heights.get("gebaeudehoehe_m") if geometry.heights else None
    }
    print(f"✓ Höhen: Traufe={height_data['traufhoehe_m']}m, First={height_data['firsthoehe_m']}m")

    # GWR-Daten
    gwr_data = geo_result.gwr_data.model_dump() if geo_result.gwr_data else None

    # EGID
    egid = str(geo_result.gwr_data.egid) if geo_result.gwr_data else "unknown"

    print("\nStarte Claude-Analyse (MIT Orthofoto)...")
    print("(Dies kann ~30 Sekunden dauern und kostet ~$0.05-0.10)")

    try:
        context = await context_service.analyze_with_claude(
            egid=egid,
            adresse=address,
            polygon=polygon,
            height_data=height_data,
            gwr_data=gwr_data,
            include_orthofoto=True  # MIT Orthofoto
        )

        print(f"\n✓ Analyse abgeschlossen:")
        print(f"  Komplexität: {context.complexity.value}")
        print(f"  Zonen: {len(context.zones)}")
        for zone in context.zones:
            beruest = "✓" if zone.beruesten else "✗"
            print(f"    - {zone.name}: {zone.type.value}, {zone.gebaeudehoehe_m}m, berüsten={beruest}")
        print(f"  Konfidenz: {context.confidence}")
        print(f"  Orthofoto-Analyse: {context.has_orthofoto_analysis}")

        if context.orthofoto_analysis:
            print(f"\n  Orthofoto-Details:")
            print(f"    {json.dumps(context.orthofoto_analysis, indent=4, ensure_ascii=False)}")

        return True

    except Exception as e:
        print(f"✗ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("ORTHOFOTO-ANALYSE INTEGRATION TEST")
    print("=" * 60)

    results = []

    # Test 1: Orthofoto-Service
    results.append(("Orthofoto-Service", await test_orthofoto_service()))

    # Test 2: Analyse ohne Orthofoto
    results.append(("Claude ohne Orthofoto", await test_building_context_without_orthofoto()))

    # Test 3: Analyse mit Orthofoto
    results.append(("Claude mit Orthofoto", await test_building_context_with_orthofoto()))

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)

    passed = 0
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\nErgebnis: {passed}/{len(results)} Tests bestanden")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
