# Prompt-Erweiterung: Position-Feld für suggested_zones

## Ziel

Erweitere den Building-Analysis-Prompt, sodass jede Zone in `suggested_zones` ein `position`-Feld erhält, das die räumliche Anordnung für 3D-Modelle und richtungsspezifische SVG-Generierung beschreibt.

---

## Neue Prompt-Sektion: RÄUMLICHE ANORDNUNG

```markdown
## RÄUMLICHE ANORDNUNG (POSITION)

Jede Zone MUSS ein `position`-Feld erhalten. Die Position beschreibt, wo sich der Gebäudeteil 
relativ zum Hauptbaukörper befindet - aus der Perspektive der **Hauptfassade** (typischerweise 
der repräsentativsten Seite mit Haupteingang).

### Erlaubte Werte für `position`:

| Wert | Beschreibung | Typische Anwendung |
|------|--------------|-------------------|
| `zentral` | Hauptbaukörper, bildet das Zentrum | Kirchenschiff, Hauptgebäude, zentrale Kuppel |
| `links` | Links vom Zentrum (vom Betrachter aus) | Linker Turm, linker Anbau, linker Flügel |
| `rechts` | Rechts vom Zentrum (vom Betrachter aus) | Rechter Turm, rechter Anbau, rechter Flügel |
| `flankierend` | Symmetrisch beidseitig | Doppeltürme, Seitenkapellen, Seitenflügel |
| `umlaufend` | Umgibt das Zentrum | Arkaden, Laubengänge, umlaufende Balkone |
| `hinten` | Hinter dem Hauptbaukörper | Chor (bei Kirchen), Hintergebäude, Apsiden |
| `vorne` | Vor dem Hauptbaukörper | Vorhalle (Narthex), Portikus, Vorbau |

### Entscheidungslogik:

1. **Identifiziere die Hauptfassade:**
   - Bei Kirchen: Westfassade (Hauptportal) oder Fassade mit dominantem Turm
   - Bei Wohnhäusern: Strassenfassade oder Eingangsseite
   - Bei öffentlichen Gebäuden: Repräsentative Fassade mit Hauptzugang

2. **Bestimme das Zentrum:**
   - Das grösste zusammenhängende Volumen = `zentral`
   - Bei Kirchen: Kirchenschiff = `zentral`

3. **Ordne restliche Zonen relativ zum Zentrum ein:**
   - Symmetrische Elemente (z.B. zwei identische Türme) = `flankierend`
   - Einzelne seitliche Elemente = `links` oder `rechts`
   - Chor, Apsis, Hintergebäude = `hinten`
   - Vorhallen, Portikus = `vorne`

### WICHTIG:
- `links`/`rechts` ist aus **Betrachtersicht der Hauptfassade**
- Bei unklarer Orientierung: Nutze Nordausrichtung als Referenz
- Jede Zone braucht GENAU EINEN position-Wert
```

---

## Erweitertes JSON-Schema

```json
{
  "suggested_zones": {
    "type": "array",
    "items": {
      "type": "object",
      "required": ["name", "type", "height_m", "scaffolding", "position"],
      "properties": {
        "name": {
          "type": "string",
          "description": "Bezeichnung der Zone"
        },
        "type": {
          "type": "string",
          "enum": ["hauptgebaeude", "turm", "anbau", "kuppel", "dach", "arkade"],
          "description": "Gebäudetyp der Zone"
        },
        "height_m": {
          "type": "number",
          "description": "Geschätzte Höhe in Metern"
        },
        "scaffolding": {
          "type": "boolean",
          "description": "Ob Zone eingerüstet werden kann"
        },
        "position": {
          "type": "string",
          "enum": ["zentral", "links", "rechts", "flankierend", "umlaufend", "hinten", "vorne"],
          "description": "Räumliche Position relativ zum Hauptbaukörper"
        }
      }
    }
  }
}
```

---

## Konkrete Beispiele für zuverlässige Generierung

### Beispiel 1: Kirche St. Peter und Paul (Doppeltürme)

**Input-Kontext:**
```
Gebäude: Christkatholische Kirche St. Peter und Paul, Bern
Baustil: Neugotik
Besonderheit: Zwei symmetrische Türme an der Westfassade
```

**Erwartete Ausgabe:**
```json
{
  "suggested_zones": [
    {
      "name": "Kirchenschiff",
      "type": "hauptgebaeude",
      "height_m": 22,
      "scaffolding": true,
      "position": "zentral"
    },
    {
      "name": "Doppeltürme West",
      "type": "turm",
      "height_m": 60,
      "scaffolding": false,
      "position": "flankierend"
    },
    {
      "name": "Seitenschiffe",
      "type": "anbau",
      "height_m": 12,
      "scaffolding": true,
      "position": "flankierend"
    },
    {
      "name": "Chor",
      "type": "anbau",
      "height_m": 18,
      "scaffolding": true,
      "position": "hinten"
    }
  ]
}
```

### Beispiel 2: Bundeshaus (asymmetrisch)

**Input-Kontext:**
```
Gebäude: Bundeshaus, Bern
Baustil: Neorenaissance mit Kuppel
Besonderheit: Zentrale Kuppel, zwei Seitenflügel
```

**Erwartete Ausgabe:**
```json
{
  "suggested_zones": [
    {
      "name": "Hauptbau mit Kuppel",
      "type": "hauptgebaeude",
      "height_m": 45,
      "scaffolding": false,
      "position": "zentral"
    },
    {
      "name": "Kuppel",
      "type": "kuppel",
      "height_m": 64,
      "scaffolding": false,
      "position": "zentral"
    },
    {
      "name": "Westflügel",
      "type": "anbau",
      "height_m": 28,
      "scaffolding": true,
      "position": "links"
    },
    {
      "name": "Ostflügel",
      "type": "anbau",
      "height_m": 28,
      "scaffolding": true,
      "position": "rechts"
    }
  ]
}
```

### Beispiel 3: Wohnhaus mit Anbau

**Input-Kontext:**
```
Gebäude: Mehrfamilienhaus mit Garage
Baustil: Moderne
Besonderheit: Einzelner Anbau rechts
```

**Erwartete Ausgabe:**
```json
{
  "suggested_zones": [
    {
      "name": "Hauptgebäude",
      "type": "hauptgebaeude",
      "height_m": 12,
      "scaffolding": true,
      "position": "zentral"
    },
    {
      "name": "Garage/Anbau",
      "type": "anbau",
      "height_m": 4,
      "scaffolding": true,
      "position": "rechts"
    }
  ]
}
```

### Beispiel 4: Kloster mit Kreuzgang

**Input-Kontext:**
```
Gebäude: Kloster Einsiedeln
Baustil: Barock
Besonderheit: Klosterkirche mit umlaufendem Kreuzgang
```

**Erwartete Ausgabe:**
```json
{
  "suggested_zones": [
    {
      "name": "Klosterkirche",
      "type": "hauptgebaeude",
      "height_m": 35,
      "scaffolding": true,
      "position": "zentral"
    },
    {
      "name": "Doppeltürme",
      "type": "turm",
      "height_m": 55,
      "scaffolding": false,
      "position": "flankierend"
    },
    {
      "name": "Kreuzgang",
      "type": "arkade",
      "height_m": 8,
      "scaffolding": true,
      "position": "umlaufend"
    },
    {
      "name": "Vorhalle (Gnadenkapelle)",
      "type": "anbau",
      "height_m": 15,
      "scaffolding": true,
      "position": "vorne"
    }
  ]
}
```

---

## Vollständiger Prompt-Baustein (zum Einfügen)

```markdown
## ZONE POSITION REQUIREMENTS

KRITISCH: Jede Zone in `suggested_zones` MUSS ein `position`-Feld enthalten.

### Position-Werte und ihre Bedeutung:

**`zentral`** - Der Hauptbaukörper
- Kirchenschiff, Hauptgebäude, zentraler Trakt
- Es gibt typischerweise nur EINE zentrale Zone (ausser bei Kuppeln auf dem Zentrum)

**`flankierend`** - Symmetrisch beidseitig
- Doppeltürme, Seitenflügel, Seitenschiffe
- NUR verwenden wenn ZWEI symmetrische Elemente existieren

**`links` / `rechts`** - Asymmetrische seitliche Elemente
- Einzelner Turm, einzelner Anbau
- Perspektive: Betrachter steht VOR der Hauptfassade

**`hinten`** - Hinter dem Zentrum
- Chor bei Kirchen, Hintergebäude, Apsiden
- Vom Haupteingang aus gesehen "hinten"

**`vorne`** - Vor dem Zentrum
- Vorhalle, Portikus, Vorbau
- Zwischen Betrachter und Hauptgebäude

**`umlaufend`** - Umgibt das Zentrum
- Arkaden, Laubengänge, Umgänge
- Schliesst das Zentrum ein oder um

### Validierungsregeln:
1. Mindestens eine Zone muss `position: "zentral"` haben
2. `flankierend` nur bei echten Paaren (2 Türme, 2 Flügel)
3. Bei Unsicherheit: `zentral` für Hauptbau, `hinten`/`vorne` nach Logik

### Output-Format:
```json
{
  "suggested_zones": [
    {"name": "...", "type": "...", "height_m": ..., "scaffolding": ..., "position": "..."}
  ]
}
```
```

---

## Integration in bestehenden Prompt

Der Baustein sollte **VOR** dem JSON-Schema eingefügt werden und **NACH** den Gebäudedaten. 

Empfohlene Reihenfolge:
1. Gebäudeinformationen (Adresse, EGID, Baustil, etc.)
2. **→ ZONE POSITION REQUIREMENTS (neu)**
3. JSON-Schema mit Beispielen
4. Anweisungen zur SVG-Generierung

---

## Fallback-Strategie bei fehlender Position

Falls die API trotzdem Zonen ohne `position` zurückgibt:

```python
def ensure_zone_positions(zones: List[dict]) -> List[dict]:
    """
    Stellt sicher, dass alle Zonen eine Position haben.
    Wendet Heuristiken an falls position fehlt.
    """
    for zone in zones:
        if 'position' not in zone or zone['position'] is None:
            zone['position'] = infer_position(zone)
    return zones

def infer_position(zone: dict) -> str:
    """Leitet Position aus Zoneneigenschaften ab."""
    zone_type = zone.get('type', '')
    zone_name = zone.get('name', '').lower()
    
    # Typ-basierte Heuristik
    if zone_type == 'hauptgebaeude':
        return 'zentral'
    if zone_type == 'kuppel':
        return 'zentral'
    
    # Name-basierte Heuristik
    if 'chor' in zone_name or 'apsis' in zone_name:
        return 'hinten'
    if 'vorhalle' in zone_name or 'portikus' in zone_name:
        return 'vorne'
    if 'seitenschiff' in zone_name or 'seitenflügel' in zone_name:
        return 'flankierend'
    if 'turm' in zone_name:
        # Einzelturm vs. Doppelturm prüfen
        if 'links' in zone_name or 'nord' in zone_name:
            return 'links'
        if 'rechts' in zone_name or 'süd' in zone_name:
            return 'rechts'
        return 'flankierend'  # Default für Türme
    if 'arkade' in zone_name or 'kreuzgang' in zone_name:
        return 'umlaufend'
    
    # Fallback
    return 'zentral'
```

---

## Nutzung für 3D-Modell und SVG

### 3D-Positionierung:
```python
POSITION_OFFSETS = {
    'zentral': (0, 0),
    'links': (-1, 0),      # Negative X-Achse
    'rechts': (1, 0),      # Positive X-Achse
    'flankierend': None,   # Spezialfall: zwei Objekte erzeugen
    'hinten': (0, 1),      # Positive Y-Achse (weg vom Betrachter)
    'vorne': (0, -1),      # Negative Y-Achse (zum Betrachter)
    'umlaufend': None      # Spezialfall: Ring-Geometrie
}
```

### SVG-Zeichenreihenfolge:
```python
DRAW_ORDER = {
    'hinten': 0,      # Zuerst zeichnen (im Hintergrund)
    'flankierend': 1,
    'umlaufend': 1,
    'zentral': 2,
    'vorne': 3,
    'links': 2,
    'rechts': 2
}
```
