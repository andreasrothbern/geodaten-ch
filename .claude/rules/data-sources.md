# Datenquellen

## Übersicht

| Quelle | Daten | Status |
|--------|-------|--------|
| swisstopo API | Geocoding, GWR, Terrain | Live |
| swissBUILDINGS3D | Höhe + Polygon | On-Demand STAC |
| swissALTI3D | Terrain-Höhe (m ü.M.) | Live |
| ~~geodienste.ch WFS~~ | ~~Gebäude-Polygon~~ | **Deaktiviert** |

> **Änderung 01.01.2026:** geodienste.ch wurde deaktiviert.
> Alle Polygon-Daten kommen jetzt aus swissBUILDINGS3D.
> Das funktioniert für ALLE Schweizer Kantone.

## Höhen-Lookup Strategie

```
1. Bekannte Gebäude (_known_zones)
2. EGID-Lookup (building_heights_detailed)
3. Koordinaten-Lookup (±50m Toleranz)
4. On-Demand STAC API Fetch
5. Geschätzt aus GWR (Geschosse × 3.2m)
6. Standard nach Kategorie
```

## Polygon-Lookup Strategie (NEU)

```
1. swissBUILDINGS3D via STAC API
2. Tile-Download (~5-10s beim ersten Mal)
3. Suche nächstes Gebäude (±50m Toleranz)
4. Rückgabe: Polygon + Seiten + Höhen
```

## Koordinatensysteme

- **LV95 (EPSG:2056)**: Primär für alle APIs
- **LV03**: Automatische Konvertierung
- **WGS84**: Nur für 3D-Viewer URLs

## API-Limits

- swisstopo: Keine Rate-Limits, aber Timeouts bei Last
- swissBUILDINGS3D: STAC API (kostenlos, keine Limits)
- Claude API: Token-basiert (~$0.01-0.15 pro Anfrage)