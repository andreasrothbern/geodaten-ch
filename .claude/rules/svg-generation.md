# SVG-Generierung

## Architektur

```
SmartBuildingService
    ↓
BuildingDataBundle (mit Zonen)
    ↓
UnifiedPromptGenerator
    ↓
Claude API (Sonnet)
    ↓
SVG Output
```

## Stil-Vorgaben

| Element | Farbe | Verwendung |
|---------|-------|------------|
| Hintergrund | #FFFFFF | Immer weiss |
| Gebäude-Füllung | url(#hatch) | Schraffur-Pattern |
| Gerüst-Ständer | #0066CC | Blau |
| Verankerung | #CC0000 | Rot, gestrichelt |
| Beläge | #8B4513 | Braun |
| Kuppel | url(#copper) | Kupfer-Gradient |

## Zonen-Typen

| Typ | Beschreibung |
|-----|--------------|
| hauptgebaeude | Hauptbaukörper |
| anbau | Seitenflügel |
| turm | Türme, Kirchturm |
| kuppel | Kuppeln (Sonderkonstruktion) |
| arkade | Arkaden, Laubengänge |

## Bekannte Gebäude

Definiert in `smart_building/known_buildings.py`:
- Bundeshaus: 3 Zonen (Arkaden, Hauptgebäude, Kuppel)
- Berner Münster: 3 Zonen (Kirchenschiff, Seitenkapellen, Turm)
- St. Peter & Paul: 3 Zonen (Kirchenschiff, Seitenschiffe, Turm)
- Zytglogge: 2 Zonen (Torhaus, Turm)

## Cache

SVG-Cache in `claude_svg_cache.db`:
- Key: SHA256(egid + svg_type + version)
- Invalidierung bei Prompt-Änderungen über Version