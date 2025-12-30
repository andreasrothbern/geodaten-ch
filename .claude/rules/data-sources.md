# Datenquellen

## Übersicht

| Quelle | Daten | Status |
|--------|-------|--------|
| swisstopo API | Geocoding, GWR, Terrain | Live |
| geodienste.ch WFS | Gebäude-Polygon | Live |
| swissBUILDINGS3D | Trauf-/Firsthöhe | DB + On-Demand |
| swissALTI3D | Terrain-Höhe (m ü.M.) | Live |

## Höhen-Lookup Strategie

```
1. Bekannte Gebäude (_known_zones)
2. EGID-Lookup (building_heights_detailed)
3. Koordinaten-Lookup (±50m Toleranz)
4. On-Demand STAC API Fetch
5. Geschätzt aus GWR (Geschosse × 3.2m)
6. Standard nach Kategorie
```

## Koordinatensysteme

- **LV95 (EPSG:2056)**: Primär für alle APIs
- **LV03**: Automatische Konvertierung
- **WGS84**: Nur für 3D-Viewer URLs

## API-Limits

- swisstopo: Keine Rate-Limits, aber Timeouts bei Last
- geodienste.ch: Kantonal unterschiedlich
- Claude API: Token-basiert (~$0.01-0.15 pro Anfrage)