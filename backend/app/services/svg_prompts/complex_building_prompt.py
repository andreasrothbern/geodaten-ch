# backend/app/services/svg_prompts/complex_building_prompt.py
"""
SVG-Prompts für KOMPLEXE Gebäude (Bundeshaus, Kirchen, öffentliche Gebäude).

Diese Prompts unterstützen:
- Kuppeln (mit Kupfer-Gradient)
- Türme
- Arkaden
- Mehrere Höhenzonen
- Komplexe architektonische Elemente

Version: 1.0
Datum: 25.12.2025
"""

from typing import List, Dict, Any, Optional


# =============================================================================
# SVG PATTERNS FÜR KOMPLEXE GEBÄUDE
# =============================================================================

COMPLEX_SVG_DEFS = """<defs>
    <!-- Schraffur für Gebäude -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Dach-Schraffur -->
    <pattern id="roof-hatch" patternUnits="userSpaceOnUse" width="6" height="6">
      <path d="M0,0 l6,6 M-1,5 l3,3 M5,-1 l3,3" stroke="#777" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient für Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="50%" style="stop-color:#5A9A87"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>

    <!-- Arkaden-Muster -->
    <pattern id="arcade" patternUnits="userSpaceOnUse" width="30" height="40">
      <path d="M5,40 L5,15 Q15,5 25,15 L25,40" fill="none" stroke="#666" stroke-width="1"/>
    </pattern>
</defs>"""


# =============================================================================
# FARBPALETTE FÜR KOMPLEXE GEBÄUDE
# =============================================================================

COMPLEX_COLORS = """## Farben

| Element | Farbe | Code |
|---------|-------|------|
| Hintergrund | Weiss | #FFFFFF |
| Gebäude-Füllung | Schraffur | url(#hatch) |
| Dach-Füllung | Schraffur | url(#roof-hatch) |
| Kuppel | Kupfer-Gradient | url(#copper) |
| Linien/Umrisse | Dunkelgrau | #333333 |
| Gerüst-Ständer | Blau | #0066CC |
| Gerüst-Beläge | Braun | #8B4513 |
| Verankerung | Rot gestrichelt | #CC0000 |
| Text | Dunkelgrau | #333333 |

HINWEIS: Kuppel ist das EINZIGE Element mit Gradient!"""


# =============================================================================
# ZONE-TYP BESCHREIBUNGEN
# =============================================================================

ZONE_TYPE_DESCRIPTIONS = {
    'hauptgebaeude': 'Rechteckiger Hauptkörper mit Geschosslinien und Satteldach, Schraffur url(#hatch)',
    'turm': 'Schmaler, hoher Turm mit Spitzdach oder Flachdach, Schraffur url(#hatch)',
    'kuppel': 'Halbkreis/Ellipse mit Kupfer-Gradient url(#copper) - EINZIGER Gradient!',
    'arkade': 'Niedriger Bereich mit Bögen (Rundbogen), Schraffur url(#hatch)',
    'anbau': 'Niedrigerer Anbau am Hauptgebäude, Schraffur url(#hatch)',
    'vordach': 'Flaches Vordach, Schraffur url(#hatch)',
    'treppenhaus': 'Vertikales Element neben Hauptgebäude, Schraffur url(#hatch)',
}


def _generate_zone_descriptions(zones: List[Dict[str, Any]]) -> str:
    """Generiert Beschreibungen der vorhandenen Zonen."""

    if not zones:
        return "- **Hauptgebäude** (Typ: hauptgebaeude)\n  - Standard-Darstellung"

    descriptions = []
    zone_types_seen = set()

    for zone in zones:
        zone_type = zone.get('type') or zone.get('typ') or 'hauptgebaeude'
        zone_name = zone.get('name') or zone.get('id', 'Zone')

        hoehe = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
                 zone.get('first_height_m') or zone.get('building_height_m', 10))
        traufhoehe = zone.get('traufhoehe_m') or zone.get('eave_height_m')

        desc = f"- **{zone_name}** (Typ: {zone_type})\n"
        desc += f"  - Höhe: {hoehe:.1f}m"
        if traufhoehe:
            desc += f", Traufe: {traufhoehe:.1f}m"

        descriptions.append(desc)
        zone_types_seen.add(zone_type.lower())

    # Zone-Typ Erklärungen nur für vorhandene Typen
    type_explanations = "\n\n## Darstellung der Zone-Typen (NUR die oben genannten!)\n\n"
    for zt in zone_types_seen:
        if zt in ZONE_TYPE_DESCRIPTIONS:
            type_explanations += f"- **{zt}** = {ZONE_TYPE_DESCRIPTIONS[zt]}\n"

    return "\n".join(descriptions) + type_explanations


# =============================================================================
# ELEVATION PROMPT (ANSICHT)
# =============================================================================

def generate_complex_elevation_prompt(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any],
    scaffolding_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generiert den Elevation-Prompt für ein KOMPLEXES Gebäude.

    Unterstützt Kuppeln, Türme, Arkaden und mehrere Höhenzonen.
    """

    # Gebäudedaten extrahieren
    address = building_data.get('address', building_data.get('adresse', 'Unbekannt'))
    egid = building_data.get('egid', '-')
    geschosse = building_data.get('geschosse') or building_data.get('gastw') or building_data.get('floors') or 3

    # Breite
    breite = (building_data.get('fassadenbreite_m') or
              building_data.get('facade_length_m') or
              building_data.get('width_m') or
              building_data.get('dimensions', {}).get('facade_length_m', 30))

    # Maximale Höhe aus Zonen berechnen
    max_hoehe = 10
    for zone in zones:
        h = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
             zone.get('first_height_m') or zone.get('building_height_m', 0))
        if h > max_hoehe:
            max_hoehe = h

    # Fallback auf Building-Data
    if max_hoehe == 10:
        max_hoehe = (building_data.get('hoehe_m') or
                     building_data.get('gebaeudehoehe_m') or
                     building_data.get('dimensions', {}).get('firsthoehe_m', 10))

    # Gerüst-Daten
    if scaffolding_data:
        geruest_hoehe = scaffolding_data.get('gesamthoehe_m', max_hoehe + 1)
        anzahl_lagen = scaffolding_data.get('anzahl_lagen', int(geruest_hoehe / 2))
    else:
        geruest_hoehe = max_hoehe + 1
        anzahl_lagen = int(geruest_hoehe / 2)

    # Höhenskala berechnen
    max_skala = int((max_hoehe // 10 + 1) * 10)  # Aufrunden auf 10er
    hoehenskala_werte = list(range(0, max_skala + 10, 10))

    # Zone-Beschreibungen generieren
    zone_descriptions = _generate_zone_descriptions(zones)

    # Prüfen welche speziellen Elemente vorhanden sind
    zone_types = set()
    for zone in zones:
        zt = zone.get('type') or zone.get('typ') or 'hauptgebaeude'
        zone_types.add(zt.lower())

    has_kuppel = 'kuppel' in zone_types
    has_turm = 'turm' in zone_types
    has_arkade = 'arkade' in zone_types

    # Spezielle Hinweise
    special_hints = []
    if has_kuppel:
        special_hints.append("- KUPPEL: Halbkreis/Ellipse mit `fill=\"url(#copper)\"` - EINZIGER Gradient!")
    if has_turm:
        special_hints.append("- TÜRME: Schmal und hoch, mit Schraffur, NICHT mit Gradient")
    if has_arkade:
        special_hints.append("- ARKADEN: Niedrig, mit Rundbogen, Schraffur")

    special_hints_text = "\n".join(special_hints) if special_hints else "- Standard-Darstellung"

    return f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## KRITISCHE REGEL

Zeichne NUR die Gebäudeteile die in "Höhenzonen" aufgelistet sind!
- Jede Zone hat einen Typ und eine Höhe
- Verwende NUR die angegebenen Darstellungen
- KEINE zusätzlichen Elemente erfinden!

## WICHTIG: STIL

TECHNISCH-PROFESSIONELL, NICHT künstlerisch!
- Hintergrund: REINWEISS (#FFFFFF) - KEIN Himmel, KEIN blauer Gradient!
- Perspektive: 2D Frontalansicht (Orthogonalprojektion)
- Farben: Graustufen + Akzentfarben (Gerüst blau, Kuppel kupfer)

## Gebäudedaten

- **Adresse:** {address}
- **EGID:** {egid}
- **Fassadenbreite:** {breite:.1f} m
- **Maximale Höhe:** {max_hoehe:.1f} m
- **Geschosse:** {geschosse}

## Höhenzonen (NUR DIESE ZEICHNEN!)

{zone_descriptions}

## Spezielle Elemente

{special_hints_text}

## Gerüst-Konfiguration

- **Gerüsthöhe:** {geruest_hoehe:.1f} m
- **Anzahl Lagen:** {anzahl_lagen}
- **Verankerungen:** alle 4m vertikal

## SVG-Patterns

{COMPLEX_SVG_DEFS}

{COMPLEX_COLORS}

## Höhenskala (links)

Werte: {', '.join([f'+{h}' for h in hoehenskala_werte])} m

## Lagenbeschriftung (rechts)

- Von "1. Lage" bis "{anzahl_lagen}. Lage"

## Anforderungen

1. **Weisser Hintergrund** - `<rect width="100%" height="100%" fill="white"/>`
2. **Terrain** - Horizontale Linie bei Y=85% mit `url(#ground)` Pattern
3. **Frontalansicht** - 2D, keine Perspektive
4. **Gebäude mit Schraffur** - `fill="url(#hatch)"` für Hauptgebäude
5. **Kuppel** - NUR wenn in Zonen vorhanden: `fill="url(#copper)"`
6. **Gerüst VOR Fassade** - Ständer #0066CC, Beläge #8B4513
7. **Verankerungen** - Gestrichelte Linien #CC0000
8. **Höhenskala links** - Beschriftung in 10m Schritten
9. **Lagenbeschriftung rechts** - Nummeriert

## Output

SVG mit `viewBox="0 0 700 480"`. NUR SVG, keine Erklärungen."""


# =============================================================================
# CROSS-SECTION PROMPT (SCHNITT)
# =============================================================================

def generate_complex_cross_section_prompt(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any],
    scaffolding_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generiert den Cross-Section-Prompt für ein KOMPLEXES Gebäude.
    """

    # Gebäudedaten
    address = building_data.get('address', building_data.get('adresse', 'Unbekannt'))
    egid = building_data.get('egid', '-')
    geschosse = building_data.get('geschosse') or building_data.get('gastw') or building_data.get('floors') or 3
    tiefe = building_data.get('gebaeudetiefe_m') or building_data.get('width_m') or 15

    # Maximale Höhe aus Zonen
    max_hoehe = 10
    for zone in zones:
        h = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
             zone.get('first_height_m') or zone.get('building_height_m', 0))
        if h > max_hoehe:
            max_hoehe = h

    if max_hoehe == 10:
        max_hoehe = building_data.get('hoehe_m', 10)

    # Zone-Beschreibungen
    zone_descriptions = _generate_zone_descriptions(zones)

    # Gerüst
    if scaffolding_data:
        geruest_hoehe = scaffolding_data.get('gesamthoehe_m', max_hoehe + 1)
        anzahl_lagen = scaffolding_data.get('anzahl_lagen', int(geruest_hoehe / 2))
    else:
        geruest_hoehe = max_hoehe + 1
        anzahl_lagen = int(geruest_hoehe / 2)

    return f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## KRITISCHE REGEL

Dies ist ein SCHNITT (Seitenansicht durch das Gebäude).
Zeichne NUR die Zonen die aufgelistet sind!

## Gebäudedaten

- **Adresse:** {address}
- **EGID:** {egid}
- **Maximale Höhe:** {max_hoehe:.1f} m
- **Gebäudetiefe:** {tiefe:.1f} m
- **Geschosse:** {geschosse}

## Höhenzonen

{zone_descriptions}

## Schnitt-Darstellung

- Gebäudeprofil mit unterschiedlichen Höhen pro Zone
- Bei Kuppel: Halbkreis-Kontur oben
- Bei Türmen: Erhöhte Bereiche
- Bei Arkaden: Niedrigerer Bereich mit Bögen

## Gerüst im Schnitt

- **Gerüsthöhe:** {geruest_hoehe:.1f} m
- **Lagen:** {anzahl_lagen}
- Gerüst VOR der Fassade (links und rechts sichtbar)

## SVG-Patterns

{COMPLEX_SVG_DEFS}

{COMPLEX_COLORS}

## Elemente

1. **Weisser Hintergrund**
2. **Terrain-Linie** bei +/-0.00
3. **Gebäudeschnitt** - Schraffiert, verschiedene Höhen pro Zone
4. **Geschossdecken** - Horizontale Linien
5. **Kuppel-Schnitt** - Falls vorhanden: Halbkreis-Kontur
6. **Gerüst** - Links und rechts
7. **Höhenkoten** - +/-0.00, Traufen, Firste

## Output

SVG mit `viewBox="0 0 700 480"`. NUR SVG, keine Erklärungen."""
