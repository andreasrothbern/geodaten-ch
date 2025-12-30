# API Standards

## Haupt-Endpunkte

### SmartBuildingService (empfohlen)
```
GET /api/v1/smart-building/data?address=...
    &include_research=true
    &include_zones=true
    &include_terrain=true
```
Sammelt alle Gebäudedaten in einer 10-Schritte Pipeline.

### SVG-Visualisierung
```
GET /api/v1/visualize/floor-plan?address=...   # Grundriss
GET /api/v1/visualize/cross-section?address=... # Schnitt
GET /api/v1/visualize/elevation?address=...     # Ansicht
```

### Prompt-Generierung
```
GET /api/v1/smart-building/prompt?address=...&svg_type=all
```

## Datenquellen-Reihenfolge

1. **Bekannte Gebäude** (known_buildings.py) - kostenlos, sofort
2. **Claude Research API** - bei unbekannten Gebäuden
3. **Standard-Zonen** - Fallback bei Fehlern

## Response-Format

Alle API-Responses nutzen UTF-8 Encoding (FastAPI Standard).

## Error Handling

- 400: Ungültige Parameter
- 404: Gebäude nicht gefunden
- 500: Server-Fehler (mit Logging)
- Timeouts: swisstopo API kann bei Last langsam sein (ConnectTimeout)