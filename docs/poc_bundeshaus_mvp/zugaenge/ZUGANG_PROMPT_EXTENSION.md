# ZUGANG_PROMPT_EXTENSION.md
# Erweiterung für den Claude-Analyse-Prompt

> **Datum:** 25.12.2025
> **Zweck:** Diese Erweiterung wird dem CONTEXT_ANALYSIS_PROMPT hinzugefügt,
>            damit Claude auch Zugangs-Empfehlungen liefert.

## Erweiterung zum bestehenden Prompt

Füge diesen Abschnitt zum `CONTEXT_ANALYSIS_PROMPT` in `BUILDING_CONTEXT.md` hinzu:

```python
ZUGANG_ANALYSE_SECTION = """

## Zusätzliche Aufgabe: Zugänge empfehlen

Basierend auf der Gebäudestruktur, empfehle Positionen für Gerüst-Zugänge (Treppen).

### SUVA-Vorschriften (Schweiz)
- **Max. 50m Fluchtweg** zum nächsten Abstieg
- **Mindestens 2 Zugänge** pro Gerüst
- **Treppenbreite** mind. 0.5m (empfohlen 0.6m)

### Platzierungs-Regeln
1. **An Gebäudeecken bevorzugt** - mehr Platz, weniger Behinderung
2. **An Stirnseiten** bei rechteckigen Gebäuden
3. **Ein Zugang pro Flügel** bei L/U/komplexen Grundrissen
4. **Nicht vor Haupteingängen** bei öffentlichen Gebäuden
5. **Nicht vor Fenstern** wenn vermeidbar
6. **Bei Zonen mit unterschiedlichen Höhen**: Zugang an Zonengrenze

### Berechnung
```
anzahl_zugaenge = max(2, ceil(geruest_umfang_m / 50))
```

### Beispiele

**Rechteckiges EFH (10m × 12m, Umfang 44m):**
- 2 Zugänge (44m < 50m × 2)
- Z1: Westseite (Stirn)
- Z2: Ostseite (Stirn)

**L-förmiges MFH (Umfang 80m):**
- 2 Zugänge (80m < 50m × 2, aber L-Form)
- Z1: Ende Flügel 1
- Z2: Ende Flügel 2

**Bundeshaus (Umfang ~200m):**
- 4 Zugänge (200m / 50m = 4)
- Z1: West (Stirnseite)
- Z2: Nord-Mitte (Parlamentseingang)
- Z3: Süd-Mitte (Bundesplatz)
- Z4: Ost (Stirnseite)

## Output-Format

Füge zum bestehenden JSON-Output hinzu:

```json
{
  "zones": [...],
  "zone_adjacency": {...},
  
  "zugaenge": [
    {
      "id": "Z1",
      "fassade_id": "W",
      "position_percent": 0.5,
      "grund": "Stirnseite West, Ecke"
    },
    {
      "id": "Z2",
      "fassade_id": "N",
      "position_percent": 0.5,
      "grund": "Mitte Nordfassade, Haupteingang"
    },
    {
      "id": "Z3",
      "fassade_id": "S",
      "position_percent": 0.5,
      "grund": "Mitte Südfassade, Bundesplatz"
    },
    {
      "id": "Z4",
      "fassade_id": "E",
      "position_percent": 0.5,
      "grund": "Stirnseite Ost, Ecke"
    }
  ],
  "zugaenge_hinweise": [
    "Zugang Z2 nicht direkt vor Parlamentseingang platzieren",
    "Bei Zone 'Arkaden' separater Zugang empfohlen wegen niedriger Höhe"
  ]
}
```

### Felder

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | string | "Z1", "Z2", etc. |
| `fassade_id` | string | Fassaden-ID ("N", "E", "S", "W" oder "F1", etc.) |
| `position_percent` | float | 0.0 (Start) bis 1.0 (Ende) auf der Fassade |
| `grund` | string | Begründung für die Position |

### Validierung

Claude soll prüfen:
1. ✅ Anzahl Zugänge ausreichend? (Umfang / 50m)
2. ✅ Max. Fluchtweg eingehalten? (50m)
3. ✅ Jede Zone mit eigener Höhe erreichbar?
4. ✅ Keine Zugänge vor Eingängen/Fenstern?

Bei Problemen: In `zugaenge_hinweise` dokumentieren.
"""
```

## Vollständiger aktualisierter Prompt

```python
CONTEXT_ANALYSIS_PROMPT = """
Du analysierst ein Schweizer Gebäude für die Gerüstplanung.

## Eingabedaten

### Grundriss-Polygon (LV95 Koordinaten)
```json
{polygon_json}
```

### Polygon-Eigenschaften
- Anzahl Ecken: {num_vertices}
- Grundfläche: {area_m2:.1f} m²
- Umfang: {perimeter_m:.1f} m
- Bounding Box: {bbox_width:.1f}m × {bbox_height:.1f}m

### Verfügbare Höhendaten
- Globale Traufhöhe: {traufhoehe_m} m (swissBUILDINGS3D)
- Globale Firsthöhe: {firsthoehe_m} m
- Globale Gebäudehöhe: {gebaeudehoehe_m} m

### Gebäude-Metadaten (GWR)
- EGID: {egid}
- Adresse: {adresse}
- Kategorie: {gkat} ({gkat_text})
- Geschosse: {gastw}
- Baujahr: {gbauj}
- Grundfläche (GWR): {garea} m²

{orthofoto_section}

## Aufgabe 1: Zonen identifizieren

Analysiere das Gebäude und teile es in Höhenzonen auf.

[... bestehender Zonen-Teil ...]

## Aufgabe 2: Zugänge empfehlen

Basierend auf der Gebäudestruktur, empfehle Positionen für Gerüst-Zugänge.

### Regeln
- Max. 50m Fluchtweg (SUVA)
- Mindestens 2 Zugänge
- Bevorzugt an Ecken/Stirnseiten
- Ein Zugang pro Zone/Flügel
- Nicht vor Eingängen bei öffentlichen Gebäuden

### Berechnung
anzahl = max(2, ceil({perimeter_m} / 50))

## Output-Format

Antworte NUR mit validem JSON:

```json
{{
  "complexity": "simple|moderate|complex",
  "zones": [
    {{
      "id": "zone_1",
      "name": "Hauptgebäude",
      "type": "hauptgebaeude",
      "polygon_point_indices": [0, 1, 2, 3],
      "traufhoehe_m": 12.5,
      "firsthoehe_m": 15.0,
      "gebaeudehoehe_m": 15.0,
      "fassaden_ids": ["N", "E", "S", "W"],
      "beruesten": true,
      "sonderkonstruktion": false,
      "confidence": 0.9,
      "notes": null
    }}
  ],
  "zone_adjacency": {{}},
  "has_height_variations": false,
  "has_setbacks": false,
  "has_towers": false,
  "has_annexes": false,
  "has_special_features": false,
  "overall_confidence": 0.9,
  "reasoning": "Begründung",
  
  "zugaenge": [
    {{
      "id": "Z1",
      "fassade_id": "W",
      "position_percent": 0.5,
      "grund": "Stirnseite West"
    }},
    {{
      "id": "Z2",
      "fassade_id": "E",
      "position_percent": 0.5,
      "grund": "Stirnseite Ost"
    }}
  ],
  "zugaenge_hinweise": []
}}
```

## Wichtige Regeln

1. Bei einfachen rechteckigen Gebäuden: NUR 1 Zone, 2 Zugänge
2. Erfinde KEINE Höhen ohne Grundlage
3. Bei Unsicherheit: Weniger Zonen/Zugänge sind besser
4. `position_percent`: 0.0 = Fassaden-Start, 1.0 = Fassaden-Ende
5. Zugänge an Ecken: position_percent ≈ 0.05 oder ≈ 0.95
"""
```

## Integration in Backend

```python
# backend/app/services/context_analyzer.py

from .access_calculator import calculate_access_points, AccessPoint

async def analyze_building_with_claude(
    polygon: list,
    gwr_data: dict,
    height_data: dict,
    include_orthofoto: bool = False
) -> dict:
    """
    Analysiert ein Gebäude mit Claude API.
    
    Returns:
        BuildingContext mit Zonen UND Zugängen
    """
    
    # Prompt zusammenbauen
    prompt = CONTEXT_ANALYSIS_PROMPT.format(
        polygon_json=json.dumps(polygon),
        num_vertices=len(polygon),
        area_m2=calculate_area(polygon),
        perimeter_m=calculate_perimeter(polygon),
        # ... weitere Parameter
    )
    
    # Claude aufrufen
    response = await claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # JSON parsen
    result = json.loads(response.content[0].text)
    
    # Falls Claude keine Zugänge liefert: Heuristik als Fallback
    if not result.get('zugaenge'):
        fassaden = extract_fassaden_from_polygon(polygon)
        access_result = calculate_access_points(fassaden)
        result['zugaenge'] = [z.model_dump() for z in access_result.zugaenge]
        result['zugaenge_source'] = 'heuristik_fallback'
    else:
        result['zugaenge_source'] = 'claude'
    
    return result
```

## Datenmodell-Erweiterung

Füge zu `BuildingContext` in `building_context.py` hinzu:

```python
class AccessPoint(BaseModel):
    """Gerüst-Zugang (Treppe)"""
    id: str
    fassade_id: str
    position_percent: float
    position_m: float | None = None
    source: Literal["auto", "claude", "manual"] = "auto"
    grund: str | None = None
    koordinate_e: float | None = None
    koordinate_n: float | None = None


class BuildingContext(BaseModel):
    # ... bestehende Felder ...
    
    # Zugänge
    zugaenge: list[AccessPoint] = []
    zugaenge_hinweise: list[str] = []
    zugaenge_validated: bool = False
```
