# SmartBuildingService

## 10-Schritte Pipeline

```
1. Geocoding (swisstopo)
2. GWR-Daten (Geschosse, Fläche, Kategorie)
3. Höhendaten (swissBUILDINGS3D)
4. Terrain (swissALTI3D)
5. Polygon (swissBUILDINGS3D)
6. Dach-Analyse (berechnet)
7. Recherche (bekannte Gebäude → Claude Sonnet)
8. Zonen-Analyse (bei komplexen Gebäuden)
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