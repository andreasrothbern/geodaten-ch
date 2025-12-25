# backend/app/services/svg_prompts/simple_building_prompt.py
"""
SVG-Prompts für EINFACHE Gebäude (Wohnhäuser, MFH).

WICHTIG: Diese Prompts enthalten KEINE Referenzen zu:
- Kuppeln
- Türmen
- Arkaden
- Kupfer-Gradienten
- Komplexen architektonischen Elementen

Version: 1.0
Datum: 25.12.2025
"""

from typing import List, Dict, Any, Optional


# =============================================================================
# SVG PATTERNS FÜR EINFACHE GEBÄUDE
# =============================================================================

SIMPLE_SVG_DEFS = """<defs>
    <!-- Schraffur für Gebäude -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Dach-Schraffur (gleich wie Gebäude) -->
    <pattern id="roof-hatch" patternUnits="userSpaceOnUse" width="6" height="6">
      <path d="M0,0 l6,6 M-1,5 l3,3 M5,-1 l3,3" stroke="#777" stroke-width="0.5"/>
    </pattern>
</defs>"""


# =============================================================================
# FARBPALETTE FÜR EINFACHE GEBÄUDE
# =============================================================================

SIMPLE_COLORS = """## Farben (STRIKT - KEINE ANDEREN FARBEN!)

| Element | Farbe | Code |
|---------|-------|------|
| Hintergrund | Weiss | #FFFFFF |
| Gebäude-Füllung | Schraffur | url(#hatch) |
| Dach-Füllung | Schraffur | url(#roof-hatch) |
| Linien/Umrisse | Dunkelgrau | #333333 |
| Gerüst-Ständer | Blau | #0066CC |
| Gerüst-Beläge | Braun | #8B4513 |
| Verankerung | Rot gestrichelt | #CC0000 |
| Text | Dunkelgrau | #333333 |

VERBOTEN:
- KEINE Gradienten
- KEINE bunten Farben
- KEINE Kupfer/Bronze-Töne
- KEIN blauer Himmel-Hintergrund"""


# =============================================================================
# ELEVATION PROMPT (ANSICHT)
# =============================================================================

def generate_simple_elevation_prompt(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any],
    scaffolding_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generiert den Elevation-Prompt für ein EINFACHES Gebäude.

    WICHTIG: Enthält KEINE Referenzen zu Kuppeln oder komplexen Elementen!
    """

    # Gebäudedaten extrahieren
    address = building_data.get('address', building_data.get('adresse', 'Unbekannt'))
    egid = building_data.get('egid', '-')

    # Höhe aus Zone oder Building-Data
    if zones and len(zones) > 0:
        zone = zones[0]
        hoehe = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
                 zone.get('first_height_m') or zone.get('building_height_m') or 10)
        traufhoehe = zone.get('traufhoehe_m') or zone.get('eave_height_m') or hoehe * 0.7
    else:
        hoehe = building_data.get('hoehe_m') or building_data.get('gebaeudehoehe_m') or 10
        traufhoehe = building_data.get('traufhoehe_m') or hoehe * 0.7

    # Breite und Geschosse
    breite = building_data.get('fassadenbreite_m') or building_data.get('facade_length_m') or building_data.get('width_m') or 12
    geschosse = building_data.get('geschosse') or building_data.get('gastw') or building_data.get('floors') or 3

    # Gerüst-Daten
    if scaffolding_data:
        geruest_hoehe = scaffolding_data.get('gesamthoehe_m', hoehe + 1)
        anzahl_lagen = scaffolding_data.get('anzahl_lagen', int(geruest_hoehe / 2))
    else:
        geruest_hoehe = hoehe + 1
        anzahl_lagen = int(geruest_hoehe / 2)

    # Höhenskala berechnen
    max_skala = int((hoehe // 5 + 1) * 5)  # Aufrunden auf 5er
    hoehenskala_werte = list(range(0, max_skala + 5, 5))

    return f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## KRITISCHE REGELN - UNBEDINGT BEACHTEN!

1. Dies ist ein **EINFACHES WOHNGEBÄUDE** - KEIN Bundeshaus, KEINE Kirche!
2. Zeichne NUR: Rechteck + Satteldach (einfaches Dreieck)
3. **VERBOTEN:**
   - KEINE Kuppeln
   - KEINE Türme
   - KEINE Bögen oder Arkaden
   - KEINE besonderen architektonischen Elemente
   - KEINE Gradienten oder Farbverläufe
   - KEIN blauer Himmel

## Gebäudedaten

- **Adresse:** {address}
- **EGID:** {egid}
- **Gebäudehöhe:** {hoehe:.1f} m (First)
- **Traufhöhe:** {traufhoehe:.1f} m
- **Fassadenbreite:** {breite:.1f} m
- **Geschosse:** {geschosse}

## Gebäudeform (EXAKT SO ZEICHNEN!)

```
        /\\
       /  \\          <- Satteldach (Dreieck bis First {hoehe:.1f}m)
      /    \\
     /______\\        <- Traufe bei {traufhoehe:.1f}m
     |      |
     |      |         <- Rechteckiger Körper
     |      |         <- {geschosse} Geschosse mit Fensterreihen
     |______|
     ========         <- Terrain
```

## Gerüst-Konfiguration

- **Gerüsthöhe:** {geruest_hoehe:.1f} m
- **Anzahl Lagen:** {anzahl_lagen}
- **Verankerungen:** alle 4m vertikal (gestrichelte rote Linien)

## SVG-Struktur

{SIMPLE_SVG_DEFS}

{SIMPLE_COLORS}

## Höhenskala (links)

Werte: {', '.join([f'+{h}' for h in hoehenskala_werte])} m
- Beschriftung alle 5m
- Horizontale Hilfslinien (hellgrau, gestrichelt)

## Lagenbeschriftung (rechts)

- Von "1. Lage" bis "{anzahl_lagen}. Lage"
- Alle 2m Höhe eine Lage

## Elemente im SVG

1. **Weisser Hintergrund** - `<rect width="100%" height="100%" fill="#FFFFFF"/>`
2. **Terrain** - Horizontale Linie bei Y=85%, Pattern `url(#ground)`
3. **Gebäude** - Rechteck mit `fill="url(#hatch)"`, schwarzer Umriss
4. **Dach** - Dreieck mit `fill="url(#roof-hatch)"`, schwarzer Umriss
5. **Fenster** - Kleine Rechtecke pro Geschoss (optional, angedeutet)
6. **Gerüst** - Blaue Ständer (#0066CC), braune Beläge (#8B4513)
7. **Verankerungen** - Gestrichelte rote Linien alle 4m
8. **Höhenskala** - Links mit Werten
9. **Lagenbeschriftung** - Rechts

## Output

Erstelle ein SVG mit `viewBox="0 0 700 480"`.
Antworte NUR mit dem SVG-Code, KEINE Erklärungen."""


# =============================================================================
# CROSS-SECTION PROMPT (SCHNITT)
# =============================================================================

def generate_simple_cross_section_prompt(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any],
    scaffolding_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generiert den Cross-Section-Prompt für ein EINFACHES Gebäude.
    """

    # Gebäudedaten extrahieren
    address = building_data.get('address', building_data.get('adresse', 'Unbekannt'))
    egid = building_data.get('egid', '-')

    # Höhe aus Zone oder Building-Data
    if zones and len(zones) > 0:
        zone = zones[0]
        hoehe = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
                 zone.get('first_height_m') or zone.get('building_height_m') or 10)
        traufhoehe = zone.get('traufhoehe_m') or zone.get('eave_height_m') or hoehe * 0.7
    else:
        hoehe = building_data.get('hoehe_m') or building_data.get('gebaeudehoehe_m') or 10
        traufhoehe = building_data.get('traufhoehe_m') or hoehe * 0.7

    # Tiefe und Geschosse
    tiefe = building_data.get('gebaeudetiefe_m') or building_data.get('width_m') or 10
    geschosse = building_data.get('geschosse') or building_data.get('gastw') or building_data.get('floors') or 3

    # Gerüst-Daten
    if scaffolding_data:
        geruest_hoehe = scaffolding_data.get('gesamthoehe_m', hoehe + 1)
        anzahl_lagen = scaffolding_data.get('anzahl_lagen', int(geruest_hoehe / 2))
    else:
        geruest_hoehe = hoehe + 1
        anzahl_lagen = int(geruest_hoehe / 2)

    return f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## KRITISCHE REGELN

1. Dies ist ein **EINFACHES WOHNGEBÄUDE**
2. Schnittdarstellung (Seitenansicht durch das Gebäude)
3. **VERBOTEN:** Kuppeln, Türme, komplexe Elemente, Gradienten

## Gebäudedaten

- **Adresse:** {address}
- **EGID:** {egid}
- **Firsthöhe:** {hoehe:.1f} m
- **Traufhöhe:** {traufhoehe:.1f} m
- **Gebäudetiefe:** {tiefe:.1f} m
- **Geschosse:** {geschosse}

## Schnitt-Darstellung

```
           /\\
          /  \\        <- Dachraum
         /____\\       <- Traufe {traufhoehe:.1f}m
        |      |
   -----|      |----- <- Geschossdecken
        |      |
   -----|      |-----
        |      |
   =====|______|===== <- Terrain +/-0.00
        vvvvvvvv
        Fundament (angedeutet)
```

## Gerüst im Schnitt

- Gerüst VOR der Fassade (links und rechts)
- Lagen: {anzahl_lagen} Stück
- Beläge als horizontale braune Linien
- Ständer als vertikale blaue Linien

## SVG-Patterns

{SIMPLE_SVG_DEFS}

{SIMPLE_COLORS}

## Elemente

1. **Weisser Hintergrund**
2. **Terrain-Linie** bei +/-0.00
3. **Gebäudeschnitt** - Schraffiert
4. **Geschossdecken** - Horizontale Linien
5. **Dach** - Dreieck, schraffiert
6. **Gerüst links und rechts** - Ständer + Beläge
7. **Höhenkoten** - +/-0.00, Traufe, First

## Output

SVG mit `viewBox="0 0 700 480"`. NUR SVG, keine Erklärungen."""
