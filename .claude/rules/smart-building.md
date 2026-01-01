# SmartBuildingService

## Pipeline (Phasen)

```
PHASE 1 (sequentiell):
  1. Geocoding (swisstopo) → Koordinaten, EGID

PHASE 2 (parallel):
  2. GWR-Daten (Geschosse, Fläche, Kategorie)
  3. Höhendaten (swissBUILDINGS3D)
  4. Terrain (swissALTI3D)
  5. Polygon (swissBUILDINGS3D)

PHASE 3 (parallel, braucht Phase 2):
  6a. Dach-Analyse (berechnet aus Höhen + Polygon)
  6b. Sonnendach.ch (BFE) → Dachüberstand, Neigung
  7. Recherche (bekannte Gebäude → Claude Sonnet)

PHASE 4 (sequentiell):
  8. Zonen-Analyse (bei komplexen Gebäuden)

PHASE 5 (synchron):
  9. SUVA Zugänge (max 50m Abstand)
  10. Qualitätsbewertung
```

## Dateien

```
backend/app/services/smart_building/
├── models.py                # BuildingDataBundle, ZoneInfo
├── service.py               # Orchestrierung
├── prompt_generator.py      # Prompt-Aufbau
├── known_buildings.py       # Bekannte Gebäude-Cache
└── research_integration.py  # Kirchen-Zonen + Integration
```

## Komplexitäts-Erkennung

| Kriterium | COMPLEX |
|-----------|---------|
| Höhendifferenz > 15m | Ja |
| GKAT 1040, 1060, 1080, 1110 | Ja |
| Fläche > 1000 m² | Ja |
| Polygon > 12 Punkte | Ja |

## Zonen-Priorisierung

1. **_known_zones** aus known_buildings.py
2. **Kirchen-Zonen** bei Sakralbauten (research_integration.py)
3. **Standard-Zonen** bei extremer Höhendifferenz
4. **Einfache Zone** für normale Gebäude

## Bundle-Caching

- TTL: 24 Stunden
- Storage: SQLite
- Invalidierung: force_refresh=true