# backend/app/services/svg_prompts/environment_prompt.py
"""
SVG-Prompt für UMGEBUNGS-Darstellung (Nachbargebäude, blockierte Fassaden).

Dieses Modul generiert Prompts für:
- Umgebungs-Grundriss mit Nachbargebäuden
- Blockierte Fassaden markieren
- Zugänglichkeit visualisieren

Version: 1.0
Datum: 29.12.2025
"""

from typing import List, Dict, Any, Optional


# =============================================================================
# SVG PATTERNS FÜR UMGEBUNG
# =============================================================================

ENVIRONMENT_SVG_DEFS = """<defs>
    <!-- Hauptgebäude -->
    <pattern id="main-hatch" patternUnits="userSpaceOnUse" width="6" height="6">
      <path d="M0,0 l6,6" stroke="#333" stroke-width="0.5"/>
    </pattern>

    <!-- Nachbargebäude (hellere Schraffur) -->
    <pattern id="neighbor-hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#AAA" stroke-width="0.3"/>
    </pattern>

    <!-- Blockierte Fassade -->
    <pattern id="blocked" patternUnits="userSpaceOnUse" width="10" height="10">
      <path d="M0,5 L10,5 M5,0 L5,10" stroke="#CC0000" stroke-width="0.5"/>
    </pattern>

    <!-- Gerüstzone -->
    <pattern id="scaffold-zone" patternUnits="userSpaceOnUse" width="4" height="4">
      <rect width="4" height="4" fill="#FFFDE7" fill-opacity="0.5"/>
    </pattern>

    <!-- Strasse/Freifläche -->
    <pattern id="street" patternUnits="userSpaceOnUse" width="20" height="4">
      <path d="M0,2 L5,2 M10,2 L15,2" stroke="#666" stroke-width="1" stroke-dasharray="5,5"/>
    </pattern>
</defs>"""


# =============================================================================
# FARBPALETTE FÜR UMGEBUNG
# =============================================================================

ENVIRONMENT_COLORS = """## Farben für Umgebungs-SVG

| Element | Farbe | Code |
|---------|-------|------|
| Hintergrund | Weiss | #FFFFFF |
| Hauptgebäude | Dunkle Schraffur | url(#main-hatch) + Umriss #333 |
| Nachbargebäude | Helle Schraffur | url(#neighbor-hatch) + Umriss #AAA |
| Freie Fassade | Grün | #4CAF50 (Umriss) |
| Blockierte Fassade | Rot | #F44336 (Umriss) + url(#blocked) |
| Gerüstzone | Gelb transparent | #FFFDE7 mit 50% Opacity |
| Abstand-Markierung | Orange gestrichelt | #FF9800 |
| Strasse/Weg | Grau | #9E9E9E |
"""


# =============================================================================
# UMGEBUNGS-GRUNDRISS PROMPT
# =============================================================================

def generate_environment_prompt(
    main_building: Dict[str, Any],
    surrounding_buildings: List[Dict[str, Any]],
    blocked_facades: List[int],
    radius_m: float = 50
) -> str:
    """
    Generiert einen Prompt für Umgebungs-Visualisierung mit Nachbargebäuden.

    Args:
        main_building: Hauptgebäude-Daten (EGID, Polygon, Adresse)
        surrounding_buildings: Liste der Nachbargebäude
        blocked_facades: Indizes der blockierten Fassaden
        radius_m: Radius des dargestellten Bereichs

    Returns:
        Prompt-String für Claude API
    """

    address = main_building.get('address', main_building.get('adresse', 'Unbekannt'))
    egid = main_building.get('egid', '-')

    # Hauptgebäude-Dimensionen
    main_polygon = main_building.get('polygon', [])
    main_sides = main_building.get('sides', [])
    num_sides = len(main_sides) if main_sides else len(main_polygon) - 1 if main_polygon else 4

    # Nachbargebäude-Tabelle
    neighbor_table = "| Nr. | Abstand | Richtung | Typ |\n|-----|---------|----------|-----|"
    for i, nb in enumerate(surrounding_buildings[:10]):  # Max 10 Nachbarn
        dist = nb.get('distance_m', '?')
        direction = nb.get('direction', '?')
        nb_type = nb.get('type', 'Gebäude')
        neighbor_table += f"\n| {i+1} | {dist}m | {direction} | {nb_type} |"

    if not surrounding_buildings:
        neighbor_table = "Keine Nachbargebäude im Umkreis von {radius_m}m gefunden."

    # Blockierte Fassaden
    blocked_text = ""
    if blocked_facades:
        blocked_text = f"""
## Blockierte Fassaden

**ACHTUNG:** Die folgenden Fassaden können NICHT eingerüstet werden:
- Fassaden-Indizes: {', '.join(map(str, blocked_facades))}
- Grund: Abstand zu Nachbargebäude < 2.0m

Diese Fassaden werden im SVG **ROT** markiert.
"""
    else:
        blocked_text = """
## Blockierte Fassaden

**Keine blockierten Fassaden** - alle Seiten können eingerüstet werden.
"""

    # Fassaden-Status-Tabelle
    facade_status_table = "| Fassade | Status | Farbe |\n|---------|--------|-------|"
    for i in range(num_sides):
        if i in blocked_facades:
            facade_status_table += f"\n| {i+1} | BLOCKIERT | Rot (#F44336) |"
        else:
            facade_status_table += f"\n| {i+1} | Frei | Grün (#4CAF50) |"

    return f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## Aufgabe

Erstelle einen **Umgebungs-Grundriss** der das Hauptgebäude mit Nachbargebäuden zeigt.
Markiere blockierte Fassaden (zu wenig Platz für Gerüst).

## Hauptgebäude

- **Adresse:** {address}
- **EGID:** {egid}
- **Polygon-Punkte:** {len(main_polygon) if main_polygon else '?'}
- **Anzahl Fassaden:** {num_sides}

## Nachbargebäude (im Umkreis von {radius_m}m)

{neighbor_table}
{blocked_text}
## Fassaden-Status

{facade_status_table}

## SVG-Patterns

{ENVIRONMENT_SVG_DEFS}

{ENVIRONMENT_COLORS}

## Darstellungs-Regeln

### Hauptgebäude
- **Füllung:** `url(#main-hatch)` (dunkle Schraffur)
- **Umriss:** #333333, 2px
- **Freie Fassaden:** Grüner Umriss #4CAF50, 3px
- **Blockierte Fassaden:** Roter Umriss #F44336, 3px + `url(#blocked)` Pattern

### Nachbargebäude
- **Füllung:** `url(#neighbor-hatch)` (helle Schraffur)
- **Umriss:** #AAAAAA, 1px
- **Beschriftung:** Abstand in Metern

### Gerüstzone (optional)
- **Füllung:** `url(#scaffold-zone)` (gelb transparent)
- **Abstand:** 1.0m um Hauptgebäude (nur an freien Fassaden)

### Strassen/Freiflächen
- Hellgrau (#EEEEEE) mit Mittelstreifen-Pattern

## Anforderungen

1. **Draufsicht** (Vogelperspektive)
2. **Hauptgebäude zentral** (schwarz, schraffiert)
3. **Nachbargebäude** (grau, heller schraffiert)
4. **Farbcodierung** der Fassaden:
   - GRÜN = frei, einrüstbar
   - ROT = blockiert, NICHT einrüstbar
5. **Abstände** als gestrichelte Linien mit Beschriftung
6. **Nordpfeil** oben rechts
7. **Massstab** unten
8. **Legende** mit Farberklärung

## Legende-Inhalt

```
┌────────────────────────────┐
│ ██ Hauptgebäude            │
│ ░░ Nachbargebäude          │
│ ── Freie Fassade (grün)    │
│ ═══ Blockiert (rot)        │
│ ▓▓ Gerüstzone              │
│ -- Abstandsmessung         │
└────────────────────────────┘
```

## Output

SVG mit `viewBox="0 0 600 600"`. NUR SVG, keine Erklärungen."""


# =============================================================================
# ZUGÄNGLICHKEITS-PROMPT (Detailansicht einer Fassade)
# =============================================================================

def generate_accessibility_prompt(
    facade_index: int,
    facade_data: Dict[str, Any],
    obstacles: List[Dict[str, Any]]
) -> str:
    """
    Generiert einen Prompt für Zugänglichkeits-Analyse einer spezifischen Fassade.

    Args:
        facade_index: Index der Fassade
        facade_data: Fassadendaten (Länge, Richtung, etc.)
        obstacles: Hindernisse (Bäume, Leitungen, Nachbargebäude)

    Returns:
        Prompt-String für Claude API
    """

    length_m = facade_data.get('length_m', 10)
    direction = facade_data.get('direction', 'N')
    height_m = facade_data.get('height_m', 10)

    # Hindernisse-Tabelle
    obstacle_table = "| Typ | Position | Abstand | Auswirkung |\n|-----|----------|---------|------------|"
    for obs in obstacles:
        obs_type = obs.get('type', 'Hindernis')
        position = obs.get('position', '?')
        distance = obs.get('distance_m', '?')
        impact = obs.get('impact', 'unbekannt')
        obstacle_table += f"\n| {obs_type} | {position} | {distance}m | {impact} |"

    if not obstacles:
        obstacle_table = "Keine Hindernisse identifiziert."

    return f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## Aufgabe

Erstelle eine **Zugänglichkeits-Analyse** für Fassade {facade_index + 1}.

## Fassaden-Daten

- **Fassade:** {facade_index + 1}
- **Richtung:** {direction}
- **Länge:** {length_m:.1f} m
- **Höhe:** {height_m:.1f} m

## Hindernisse

{obstacle_table}

## Darstellung

### Draufsicht (oben)
- Fassade als Linie
- Gerüstzone (1.0m) davor
- Hindernisse als Symbole

### Seitenansicht (unten)
- Fassade mit Gerüst
- Hindernisse in Seitenansicht

## SVG-Patterns

{ENVIRONMENT_SVG_DEFS}

## Anforderungen

1. **Zwei Ansichten** übereinander:
   - Oben: Draufsicht auf Fassade + Vorplatz
   - Unten: Seitenansicht der Fassade
2. **Hindernisse markieren:**
   - Bäume: Grüner Kreis
   - Leitungen: Blaue Linie
   - Gebäude: Graues Rechteck
3. **Gerüstzone** (gelb) zeigen
4. **Mindestabstände** beschriften
5. **Zugänglichkeits-Bewertung** als Text

## Bewertungs-Skala

- **GRÜN**: Voll zugänglich
- **GELB**: Eingeschränkt (manueller Transport nötig)
- **ROT**: Nicht zugänglich

## Output

SVG mit `viewBox="0 0 700 500"`. NUR SVG, keine Erklärungen."""
