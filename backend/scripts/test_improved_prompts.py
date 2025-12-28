"""
Test-Script: Verbesserter Prompt mit Zonen an Claude API senden.

Testet zwei Gebäude:
1. Bundeshaus (komplex) - sollte Arkade, Hauptgebäude, Kuppel haben
2. Kramgasse 10, 3011 Bern (einfach) - normales Wohngebäude

Ausgabe:
- Zeigt den generierten Prompt
- Speichert SVGs in docs/showcase/
"""

import asyncio
import os
import sys
from pathlib import Path

# UTF-8 Ausgabe erzwingen
sys.stdout.reconfigure(encoding='utf-8')

# .env laden
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
print(f"[Setup] .env geladen von: {env_path}")

# Backend-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.swisstopo import SwisstopoService
from app.services.geodienste import GeodiensteService, get_height_details
from app.services.building_context import BuildingContextService
from app.services.claude_svg_zones import (
    generate_cross_section_with_zones,
    generate_elevation_with_zones,
    is_available,
    clear_cache
)
from app.services.svg_prompts import (
    get_elevation_prompt,
    get_cross_section_prompt,
    get_prompt_metadata,
    detect_building_complexity,
)

# Output-Verzeichnis
OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs" / "showcase" / "api_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_building_data(address: str):
    """Holt Gebäudedaten vom API."""
    swisstopo = SwisstopoService()
    geodienste = GeodiensteService()
    context_service = BuildingContextService()

    print(f"\n{'='*60}")
    print(f"Fetching data for: {address}")
    print('='*60)

    # 1. Geocoding
    geo = await swisstopo.geocode(address)
    if not geo:
        print(f"ERROR: Could not geocode address")
        return None

    print(f"Coordinates: E={geo.coordinates.lv95_e}, N={geo.coordinates.lv95_n}")

    # 2. Building identification
    buildings = await swisstopo.identify_buildings(
        geo.coordinates.lv95_e,
        geo.coordinates.lv95_n,
        tolerance=15
    )
    building = buildings[0] if buildings else None

    if building:
        print(f"EGID: {building.egid}")
        print(f"Floors: {building.floors}")
        print(f"Area: {building.area_m2} m²")
        print(f"Category: {building.building_category_code} ({building.building_category})")

    # 3. Building geometry
    geometry = await geodienste.get_building_geometry(
        x=geo.coordinates.lv95_e,
        y=geo.coordinates.lv95_n,
        tolerance=50,
        egid=building.egid if building else None
    )

    width_m = 20.0
    if geometry and geometry.sides:
        # sides ist eine Liste von Dicts mit 'length_m' key
        side_lengths = [s.get('length_m', 0) for s in geometry.sides]
        sorted_lengths = sorted(side_lengths, reverse=True)
        width_m = sorted_lengths[0] if sorted_lengths else 20.0
        print(f"Side lengths: {[round(s,1) for s in sorted_lengths[:4]]}")
        print(f"Width: {width_m:.1f}m")

    # 4. Building Context (mit Zonen)
    zones = []
    context = None
    if building and building.egid:
        # Erst versuchen, existierenden Kontext zu laden
        context = context_service.get_context(str(building.egid))

        # Falls nicht vorhanden, Context erstellen
        if not context:
            print("\nKein existierender Kontext gefunden...")
            polygon_data = []
            if geometry and geometry.polygon:
                polygon_data = [{"x": p[0], "y": p[1]} for p in geometry.polygon]

            # Height data - ECHTE Höhen aus swissBUILDINGS3D holen
            print("Hole echte Höhendaten aus swissBUILDINGS3D...")
            height_details = get_height_details(
                floors=building.floors,
                building_category_code=building.building_category_code,
                manual_height=None,
                egid=building.egid,
                lv95_e=geo.coordinates.lv95_e,
                lv95_n=geo.coordinates.lv95_n
            )

            print(f"  Traufhöhe: {height_details.get('traufhoehe_m')}m")
            print(f"  Firsthöhe: {height_details.get('firsthoehe_m')}m")
            print(f"  Gebäudehöhe: {height_details.get('gebaeudehoehe_m')}m")
            print(f"  Quelle: {height_details.get('active_source')}")

            height_data = {
                "traufhoehe_m": height_details.get('traufhoehe_m') or height_details.get('active_height_m', 10) * 0.75,
                "firsthoehe_m": height_details.get('firsthoehe_m') or height_details.get('active_height_m', 12),
                "gebaeudehoehe_m": height_details.get('gebaeudehoehe_m') or height_details.get('active_height_m', 12),
            }

            # GWR data mit zusätzlichen Gebäude-Hints
            gwr_data = {
                "gkat": building.building_category_code,
                "garea": building.area_m2,
                "gastw": building.floors,
            }

            # Bekannte Gebäude mit speziellen Zonen-Hints
            if "Bundesplatz" in address or building.egid == 2242547:
                print("  -> Erkannt: Bundeshaus Bern - füge Zonen-Hints hinzu")
                gwr_data["building_name"] = "Bundeshaus (Schweizer Parlamentsgebäude)"
                gwr_data["building_hints"] = """
BEKANNTES GEBÄUDE: Bundeshaus Bern (Schweizer Parlament)

Dieses Gebäude hat MEHRERE HÖHENZONEN:
1. **Arkaden/Laubengang** (Erdgeschoss): ca. 5-6m Höhe, Typ=arkade
2. **Hauptfassade** (Parlamentsgebäude): ca. 20-25m Höhe, Typ=hauptgebaeude
3. **Kuppel** (zentral): bis 64m Höhe, Typ=kuppel, sonderkonstruktion=true

Die gemessene Firsthöhe (62.6m) ist die KUPPELHÖHE, NICHT die Dachhöhe des Hauptgebäudes!

Du MUSST mindestens 3 Zonen erstellen:
- Zone 'Arkaden': traufhoehe_m=5, gebaeudehoehe_m=6, beruesten=true
- Zone 'Hauptgebäude': traufhoehe_m=20, firsthoehe_m=25, beruesten=true
- Zone 'Kuppel': gebaeudehoehe_m=64, sonderkonstruktion=true, beruesten=false (Spezialgerüst nötig)
"""

            elif "Münsterplatz" in address or "Muensterplatz" in address:
                print("  -> Erkannt: Berner Münster - füge Zonen-Hints hinzu")
                gwr_data["building_name"] = "Berner Münster (Gotische Kathedrale)"
                gwr_data["building_hints"] = """
BEKANNTES GEBÄUDE: Berner Münster (Gotische Kathedrale, UNESCO Welterbe)

Dieses Gebäude hat MEHRERE HÖHENZONEN:
1. **Kirchenschiff** (Langhaus): ca. 25-28m Traufhöhe, gotisches Gewölbe, Typ=hauptgebaeude
2. **Chor** (Ostseite): ca. 25m Höhe, Typ=hauptgebaeude
3. **Turm** (Westseite): ca. 100m Höhe (höchster Kirchturm der Schweiz!), Typ=turm, sonderkonstruktion=true
4. **Seitenkapellen**: ca. 15m Höhe, Typ=anbau

Die gemessene Höhe spiegelt den TURM wider, NICHT das Kirchenschiff!

Du MUSST mindestens 3 Zonen erstellen:
- Zone 'Kirchenschiff': traufhoehe_m=20, firsthoehe_m=28, beruesten=true
- Zone 'Seitenkapellen': traufhoehe_m=12, firsthoehe_m=15, beruesten=true
- Zone 'Turm': gebaeudehoehe_m=100, sonderkonstruktion=true, beruesten=false (Spezialgerüst/Industriekletterer nötig)
"""

            elif "Rathausgasse" in address and "2" in address:
                print("  -> Erkannt: St. Peter und Paul Kirche - füge Zonen-Hints hinzu")
                gwr_data["building_name"] = "Kirche St. Peter und Paul Bern (Katholische Kirche)"
                gwr_data["building_hints"] = """
BEKANNTES GEBÄUDE: Kirche St. Peter und Paul Bern (Neugotische katholische Kirche)

Diese Kirche (erbaut 1858-1864) hat MEHRERE HÖHENZONEN:
1. **Kirchenschiff**: ca. 18-22m Traufhöhe, Typ=hauptgebaeude
2. **Doppeltürme** (Westfassade): ca. 60m Höhe, zwei symmetrische Türme, Typ=turm
3. **Chor/Apsis** (Ostseite): ca. 15m Höhe, Typ=anbau

Du MUSST mindestens 3 Zonen erstellen:
- Zone 'Kirchenschiff': traufhoehe_m=18, firsthoehe_m=22, beruesten=true
- Zone 'Doppeltürme': gebaeudehoehe_m=60, sonderkonstruktion=true, beruesten=false (Spezialgerüst nötig)
- Zone 'Chor': traufhoehe_m=12, firsthoehe_m=15, beruesten=true
"""

            # Komplexität prüfen
            complexity = context_service.detect_complexity(
                polygon=polygon_data,
                gwr_data=gwr_data,
                area_m2=building.area_m2
            )
            print(f"Erkannte Komplexität: {complexity.value}")

            # Bei komplexen Gebäuden: Claude-Analyse
            if complexity.value == "complex":
                print("Starte Claude-Analyse für komplexes Gebäude...")
                try:
                    context = await context_service.analyze_with_claude(
                        egid=str(building.egid),
                        adresse=address,
                        polygon=polygon_data,
                        height_data=height_data,
                        gwr_data=gwr_data
                    )
                    if context:
                        context_service.save_context(context)
                        print(f"Claude-Analyse erfolgreich: {len(context.zones)} Zonen erkannt")
                except Exception as e:
                    print(f"Claude-Analyse Fehler: {e}")
                    # Fallback auf Auto-Context
                    context = None

            # Fallback: Auto-Context für einfache Gebäude oder bei Fehler
            if not context:
                print("Erstelle Auto-Context...")
                try:
                    context = context_service.create_auto_context(
                        egid=str(building.egid),
                        adresse=address,
                        polygon=polygon_data,
                        height_data=height_data,
                        gwr_data=gwr_data
                    )
                    if context:
                        context_service.save_context(context)
                except Exception as e:
                    print(f"Auto-Context Fehler: {e}")

        if context and context.zones:
            zones = [
                {
                    "name": z.name,
                    "type": z.type.value if hasattr(z.type, 'value') else str(z.type),
                    "typ": z.type.value if hasattr(z.type, 'value') else str(z.type),
                    "traufhoehe_m": z.traufhoehe_m,
                    "firsthoehe_m": z.firsthoehe_m,
                    "gebaeudehoehe_m": z.gebaeudehoehe_m,
                }
                for z in context.zones
            ]
            print(f"\nZones ({len(zones)}):")
            for z in zones:
                print(f"  - {z['name']} ({z['type']}): {z.get('gebaeudehoehe_m') or z.get('firsthoehe_m', '?')}m")

    # 5. Fallback-Zone wenn keine vorhanden
    if not zones:
        # Höhe aus Geschossen schätzen
        floors = building.floors if building and building.floors else 3
        hoehe = floors * 3.0 + 3.0  # Geschosshöhe + Dach
        zones = [{
            "name": "Hauptgebäude",
            "type": "hauptgebaeude",
            "typ": "hauptgebaeude",
            "traufhoehe_m": hoehe * 0.7,
            "firsthoehe_m": hoehe,
            "gebaeudehoehe_m": hoehe,
        }]
        print(f"\nFallback zone created: height={hoehe}m")

    return {
        "address": address,
        "egid": building.egid if building else None,
        "floors": building.floors if building else 3,
        "gkat": building.building_category_code if building else None,
        "building_category": building.building_category if building else None,
        "area_m2": building.area_m2 if building else None,
        "width_m": width_m,
        "polygon_points": len(geometry.polygon) if geometry and geometry.polygon else 4,
        "zones": zones,
        "context": context,
    }


def show_prompt(building_data: dict, svg_type: str):
    """Zeigt den generierten Prompt."""
    zones = building_data.get("zones", [])

    prepared_data = {
        "address": building_data.get("address"),
        "adresse": building_data.get("address"),
        "egid": building_data.get("egid"),
        "fassadenbreite_m": building_data.get("width_m"),
        "facade_length_m": building_data.get("width_m"),
        "width_m": building_data.get("width_m"),
        "geschosse": building_data.get("floors"),
        "gastw": building_data.get("floors"),
        "floors": building_data.get("floors"),
        "gkat": building_data.get("gkat"),
        "building_category_code": building_data.get("gkat"),
        "area_m2": building_data.get("area_m2"),
        "garea": building_data.get("area_m2"),
        "sides": building_data.get("polygon_points"),
        "polygon_points": building_data.get("polygon_points"),
    }

    # Komplexität ermitteln
    metadata = get_prompt_metadata(zones, prepared_data)
    complexity = metadata.get("complexity", "unknown")

    print(f"\n{'='*60}")
    print(f"Prompt für {svg_type.upper()}")
    print(f"Komplexität: {complexity}")
    print(f"Metadata: {metadata}")
    print('='*60)

    if svg_type == "elevation":
        prompt = get_elevation_prompt(zones, prepared_data, None)
    else:
        prompt = get_cross_section_prompt(zones, prepared_data, None)

    # Prompt nur teilweise zeigen (ersten 2000 Zeichen)
    print(f"\n{prompt[:2000]}...")
    print(f"\n[Prompt gekürzt - {len(prompt)} Zeichen total]")

    return prompt, complexity


def generate_and_save_svg(building_data: dict, svg_type: str, filename: str):
    """Generiert SVG via Claude API und speichert."""

    zones = building_data.get("zones", [])

    # Building data für Claude vorbereiten
    bd = {
        "gkat": building_data.get("gkat"),
        "building_category_code": building_data.get("gkat"),
        "area_m2": building_data.get("area_m2"),
        "garea": building_data.get("area_m2"),
        "sides": building_data.get("polygon_points"),
        "polygon_points": building_data.get("polygon_points"),
    }

    print(f"\n{'='*60}")
    print(f"Generiere {svg_type} für {building_data.get('address')}")
    print('='*60)

    if svg_type == "elevation":
        svg = generate_elevation_with_zones(
            address=building_data.get("address"),
            egid=building_data.get("egid"),
            width_m=building_data.get("width_m", 20),
            floors=building_data.get("floors", 3),
            zones=zones,
            svg_width=700,
            svg_height=480,
            building_data=bd
        )
    else:
        svg = generate_cross_section_with_zones(
            address=building_data.get("address"),
            egid=building_data.get("egid"),
            width_m=building_data.get("width_m", 20),
            floors=building_data.get("floors", 3),
            zones=zones,
            svg_width=700,
            svg_height=480,
            building_data=bd
        )

    if svg:
        output_path = OUTPUT_DIR / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg)
        print(f"✅ SVG gespeichert: {output_path}")
        print(f"   Grösse: {len(svg)} Zeichen")
        return svg
    else:
        print(f"❌ Fehler bei SVG-Generierung")
        return None


async def main():
    # Check Claude API availability
    if not is_available():
        print("❌ Claude API nicht verfügbar!")
        print("   Stelle sicher, dass ANTHROPIC_API_KEY gesetzt ist.")
        return

    print("✅ Claude API verfügbar")

    # Cache leeren für frische Ergebnisse
    print("\nCache wird geleert...")
    clear_cache()

    # Auch Building Contexts löschen für frische Claude-Analyse
    print("Building Contexts werden gelöscht für frische Analyse...")
    context_service = BuildingContextService()
    context_service.delete_context("2242547")  # Bundeshaus
    context_service.delete_context("1230453")  # Kramgasse

    # Test-Gebäude
    test_buildings = [
        "Münsterplatz 1, 3011 Bern",   # Komplex (Berner Münster - Gotische Kathedrale)
        "Rathausgasse 2, 3011 Bern",   # Komplex (St. Peter und Paul Kirche)
    ]

    for address in test_buildings:
        # Daten holen
        data = await fetch_building_data(address)
        if not data:
            continue

        # Prompt zeigen
        prompt_elev, complexity_elev = show_prompt(data, "elevation")

        # SVG generieren
        safe_name = address.split(",")[0].replace(" ", "_").lower()

        # Elevation
        svg_elev = generate_and_save_svg(
            data, "elevation",
            f"{safe_name}_elevation_{complexity_elev}.svg"
        )

        # Cross-section
        svg_section = generate_and_save_svg(
            data, "cross-section",
            f"{safe_name}_cross_section_{complexity_elev}.svg"
        )

    print(f"\n{'='*60}")
    print(f"Test abgeschlossen!")
    print(f"SVGs gespeichert in: {OUTPUT_DIR}")
    print('='*60)


if __name__ == "__main__":
    asyncio.run(main())
