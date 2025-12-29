# backend/app/services/svg_prompts/terrain_prompt.py
"""
SVG-Prompt für TERRAIN-Darstellung (Hanglage, Gefälle).

Dieses Modul generiert Prompts für:
- Terrain-Schnitt mit Höhenkoten
- Hanglage-Visualisierung
- Gefälle pro Fassade

Version: 1.0
Datum: 29.12.2025
"""

from typing import List, Dict, Any, Optional, Tuple


# =============================================================================
# SVG PATTERNS FÜR TERRAIN
# =============================================================================

TERRAIN_SVG_DEFS = """<defs>
    <!-- Terrain/Boden (Erde) -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#8B7355" stroke-width="0.5"/>
    </pattern>

    <!-- Fels/Stein -->
    <pattern id="rock" patternUnits="userSpaceOnUse" width="15" height="15">
      <path d="M0,0 L5,10 L15,5 L10,15 L0,10" stroke="#666" stroke-width="0.5" fill="none"/>
    </pattern>

    <!-- Gebäude-Schnitt -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Höhen-Markierung -->
    <marker id="height-arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,5 L10,5 M7,2 L10,5 L7,8" stroke="#333" stroke-width="1" fill="none"/>
    </marker>
</defs>"""


# =============================================================================
# FARBPALETTE FÜR TERRAIN
# =============================================================================

TERRAIN_COLORS = """## Farben für Terrain-SVG

| Element | Farbe | Code |
|---------|-------|------|
| Hintergrund | Weiss | #FFFFFF |
| Terrain-Füllung | Erd-Pattern | url(#ground) |
| Terrain-Oberkante | Dunkelbraun | #5D4037 |
| Höhenlinien | Grau gestrichelt | #999999 |
| Höhenkoten-Text | Dunkelgrau | #333333 |
| Gebäude-Schnitt | Schraffur | url(#cut-hatch) |
| Referenzlinie | Rot | #CC0000 |
"""


# =============================================================================
# TERRAIN-SCHNITT PROMPT
# =============================================================================

def generate_terrain_prompt(
    building_data: Dict[str, Any],
    terrain_data: Dict[str, Any],
    facade_profiles: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Generiert einen Prompt für Terrain-Visualisierung mit Hanglage.

    Args:
        building_data: Gebäudedaten (Adresse, EGID, Dimensionen)
        terrain_data: Terrain-Daten von swissALTI3D
        facade_profiles: Optional - Gefälle pro Fassade

    Returns:
        Prompt-String für Claude API
    """

    address = building_data.get('address', building_data.get('adresse', 'Unbekannt'))
    egid = building_data.get('egid', '-')

    # Terrain-Daten extrahieren
    terrain_height = terrain_data.get('terrain_height_m', 500)
    min_height = terrain_data.get('min_height_m', terrain_height)
    max_height = terrain_data.get('max_height_m', terrain_height)
    slope_m = terrain_data.get('slope_m', 0)
    classification = terrain_data.get('classification', 'eben')

    # Eckhöhen-Tabelle
    corner_heights = terrain_data.get('corner_heights', [])
    corner_table = ""
    if corner_heights:
        corner_table = "| Ecke | Höhe (m ü.M.) | Differenz |\n|------|---------------|-----------|"
        for ch in corner_heights:
            diff = ch.get('height_m', 0) - min_height
            corner_table += f"\n| {ch.get('index', '?')} | {ch.get('height_m', 0):.1f} | +{diff:.1f}m |"

    # Fassaden-Gefälle
    facade_table = ""
    if facade_profiles:
        facade_table = "\n\n## Gefälle pro Fassade\n\n| Fassade | Start | Ende | Gefälle |\n|---------|-------|------|---------|"
        for fp in facade_profiles:
            start_h = fp.get('start_height_m', 0)
            end_h = fp.get('end_height_m', 0)
            slope = fp.get('slope_m', 0)
            facade_table += f"\n| {fp.get('facade_index', '?')} | {start_h:.1f}m | {end_h:.1f}m | {slope:+.1f}m |"

    # Hanglage-Skizze
    if classification in ['hanglage', 'steilhang']:
        slope_sketch = f"""
```
                ╱───────╮
               ╱        │  Gebäude
              ╱         │
╲            ╱          │
 ╲          ╱           │
  ╲________╱____________│
   ↑       ↑            ↑
   {min_height:.1f}m   {(min_height+max_height)/2:.1f}m    {max_height:.1f}m ü.M.

   Gefälle: {slope_m:.1f}m über Gebäudebreite
```"""
    else:
        slope_sketch = f"""
```
   ┌─────────────────────┐
   │      Gebäude        │
───┴─────────────────────┴───  {terrain_height:.1f}m ü.M.
   ════════════════════════
         Terrain (eben)
```"""

    return f"""Du bist ein Experte für TECHNISCHE Terrain-Visualisierungen im SVG-Format.

## Aufgabe

Erstelle eine **Terrain-Schnittdarstellung** die das Gefälle unter dem Gebäude zeigt.

## Gebäudedaten

- **Adresse:** {address}
- **EGID:** {egid}
- **Terrain-Referenz:** {terrain_height:.1f} m ü.M.

## Terrain-Analyse (swissALTI3D)

- **Minimale Höhe:** {min_height:.1f} m ü.M.
- **Maximale Höhe:** {max_height:.1f} m ü.M.
- **Gesamtgefälle:** {slope_m:.1f} m
- **Klassifikation:** {classification}

### Eckhöhen
{corner_table}
{facade_table}

## Visualisierung
{slope_sketch}

## SVG-Patterns

{TERRAIN_SVG_DEFS}

{TERRAIN_COLORS}

## Anforderungen

### Darstellung
- **Perspektive:** Seitliche Schnittansicht (2D)
- **Terrain:** Geneigte oder ebene Linie je nach Klassifikation
- **Gebäude:** Vereinfachte Schnittdarstellung auf dem Terrain
- **Höhenkoten:** Alle relevanten Höhen beschriften (m ü.M.)

### Elemente
1. **Weisser Hintergrund**
2. **Terrain-Schnitt** mit `url(#ground)` Pattern
3. **Terrain-Oberkante** als {('geneigte' if slope_m > 0.5 else 'horizontale')} Linie
4. **Höhenskala links** (m ü.M.)
5. **Gebäude-Schnitt** vereinfacht auf Terrain
6. **Referenz-Höhe** als rote gestrichelte Linie bei {min_height:.1f}m ü.M.
7. **Gefälle-Angabe** mit Pfeil und Beschriftung "{slope_m:.1f}m"

### Bei Hanglage zusätzlich:
- Unterschiedliche Fundament-Höhen andeuten
- Gefälle-Richtung mit Pfeil
- Höchster und tiefster Punkt markieren

## Output

SVG mit `viewBox="0 0 700 300"`. NUR SVG, keine Erklärungen."""


# =============================================================================
# TERRAIN-ÜBERSICHT PROMPT (Draufsicht)
# =============================================================================

def generate_terrain_overview_prompt(
    building_data: Dict[str, Any],
    terrain_data: Dict[str, Any],
    polygon: List[Tuple[float, float]]
) -> str:
    """
    Generiert einen Prompt für Terrain-Übersicht (Draufsicht mit Höhenlinien).

    Args:
        building_data: Gebäudedaten
        terrain_data: Terrain-Daten
        polygon: Gebäude-Polygon Koordinaten

    Returns:
        Prompt-String für Claude API
    """

    address = building_data.get('address', 'Unbekannt')

    # Terrain-Daten
    min_height = terrain_data.get('min_height_m', 500)
    max_height = terrain_data.get('max_height_m', 500)
    slope_m = terrain_data.get('slope_m', 0)
    classification = terrain_data.get('classification', 'eben')

    # Höhenlinien-Abstände berechnen
    height_diff = max_height - min_height
    contour_interval = 1.0 if height_diff < 5 else 2.0 if height_diff < 10 else 5.0

    corner_heights = terrain_data.get('corner_heights', [])

    return f"""Du bist ein Experte für TECHNISCHE Terrain-Visualisierungen im SVG-Format.

## Aufgabe

Erstelle eine **Terrain-Übersicht** (Draufsicht) mit Höhenlinien.

## Gebäudedaten

- **Adresse:** {address}
- **Terrain-Bereich:** {min_height:.1f} - {max_height:.1f} m ü.M.
- **Klassifikation:** {classification}

## Höhenlinien-Konfiguration

- **Intervall:** alle {contour_interval:.1f}m
- **Höhenbereich:** {min_height:.0f}m - {max_height:.0f}m ü.M.
- **Anzahl Linien:** ca. {int(height_diff / contour_interval) + 1}

## Eckhöhen (an Polygon-Ecken)

| Ecke | Höhe (m ü.M.) |
|------|---------------|
{chr(10).join([f"| {ch.get('index', i)} | {ch.get('height_m', 0):.1f} |" for i, ch in enumerate(corner_heights)])}

## SVG-Patterns

{TERRAIN_SVG_DEFS}

## Anforderungen

### Darstellung
- **Perspektive:** Draufsicht (wie Grundriss)
- **Gebäude-Polygon:** Als schwarzer Umriss
- **Höhenlinien:** Konzentrische Linien um tiefsten Punkt
- **Gefälle-Richtung:** Pfeil von hoch nach tief

### Elemente
1. **Weisser Hintergrund**
2. **Höhenlinien** (grau, gestrichelt, beschriftet)
3. **Gebäude-Polygon** (schwarzer Umriss)
4. **Höhenkoten** an jeder Gebäudeecke
5. **Gefälle-Pfeil** mit Beschriftung
6. **Nordpfeil**
7. **Legende** mit Höhenlinien-Intervall

### Farbcodierung Höhenlinien
- Tiefste Linien: Hellgrau #CCCCCC
- Höchste Linien: Dunkelgrau #666666

## Output

SVG mit `viewBox="0 0 500 500"`. NUR SVG, keine Erklärungen."""
