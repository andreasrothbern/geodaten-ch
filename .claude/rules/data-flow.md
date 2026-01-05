# Datenfluss-Architektur

## Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                      GEODATEN-CH                                │
│                  (SmartBuildingService)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  building_geodata.db (Grunddaten, pro EGID)                    │
│  ══════════════════════════════════════════                     │
│  ├─ EGID, Koordinaten                                          │
│  ├─ Polygon (Original aus swissBUILDINGS3D)                    │
│  └─ Höhen (Trauf-, First-, Gebäudehöhe)                        │
│                                                                 │
│  building_contexts.db (Enrichment, pro EGID)                   │
│  ═══════════════════════════════════════════                    │
│  ├─ building_contexts Tabelle                                  │
│  │   └─ Zonen (Claude-Analyse / known_buildings.py)            │
│  └─ building_environment Tabelle                               │
│      ├─ Terrain (Geländehöhe aus swissALTI3D)                  │
│      └─ Hanglage (slope_m, slope_class)                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ per EGID referenziert
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GERUESTBAU-APP                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  geruestbau.db (Projekte, pro User/Projekt)                    │
│  ═══════════════════════════════════════════                    │
│  ├─ egid / buildings[] (Referenzen)                            │
│  ├─ scaffold_config (simplify_epsilon, field_length_ratio)     │
│  └─ client_name, deadline, etc.                                │
│                                                                 │
│  DYNAMISCHE BERECHNUNGEN (nicht gespeichert)                   │
│  └─ Nachbar-Gebäude (GET /building/{egid}/neighbors)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 1. Grunddaten (aus swissBUILDINGS3D Tiles)

Direkt aus Tiles gemappt, in `building_geodata.db` gespeichert.

| Daten | Tile-Attribut | Berechnung |
|-------|---------------|------------|
| EGID | EGID | direkt |
| Polygon | Geometrie | direkt |
| traufhoehe_m | DACH_MIN, GELAENDEPUNKT | DACH_MIN - GELAENDEPUNKT |
| firsthoehe_m | DACH_MAX, GELAENDEPUNKT | DACH_MAX - GELAENDEPUNKT |
| gebaeudehoehe_m | GESAMTHOEHE | direkt |

**NICHT aus Tiles:** Zonen, Terrain, Hanglage → diese sind Enrichment

### Speicherung der Grunddaten

Die Gebäudedaten werden an **zwei Stellen** gespeichert:

```
1. swissbuildings3d_fetcher.py
   │
   ├─ fetch_building_polygon_for_coordinates()
   │   │
   │   ├─ Tile-Cache prüfen
   │   │
   │   ├─ Gebäude parsen
   │   │
   │   └─ _save_building_to_geodata_cache(result, e, n)  ← SOFORT speichern!
   │       └─ geodata_service.save(geodata) → building_geodata.db
   │
   └─ schedule_prefetch(exclude_egid=...)  ← Background-Job für REST
       └─ tile_prefetch.py speichert alle ANDEREN Gebäude im Tile
```

**Wichtig:** Das abgefragte Gebäude wird **sofort** in `building_geodata.db` gespeichert,
BEVOR der Background-Prefetch startet (der dieses Gebäude excludiert).

## 2. Enrichment-Daten

Werden **direkt nach dem Laden der Grunddaten** ausgeführt (BEVOR das Projekt gespeichert wird).
Gespeichert in `building_contexts.db` pro EGID (nicht pro Projekt).

### Enrichment beim Projekt-Erstellen (GeodataStep)

```
Frontend: GeodataStep.tsx
   │
   ├─ 1. Adresse eingeben
   │
   ├─ 2. GET /api/v1/smart-building/data?address=...
   │   │   └─ SmartBuildingService.collect_all_data()
   │   │       ├─ Geocoding
   │   │       ├─ GWR-Daten
   │   │       ├─ 3D-Daten (Polygon + Höhen) ← Grunddaten
   │   │       ├─ Terrain (swissALTI3D)      ← Enrichment!
   │   │       ├─ Sonnendach.ch              ← Enrichment!
   │   │       ├─ Zonen-Analyse              ← Enrichment!
   │   │       └─ SUVA-Zugänge               ← Enrichment!
   │   │
   │   └─ Response: BuildingDataBundle (vollständig!)
   │
   ├─ 3. Daten im Frontend anzeigen
   │
   └─ 4. "Projekt erstellen" klicken
       │
       └─ POST /api/v1/geruestbau/projects
           └─ Speichert NUR: egid, address, client_name, etc.
           └─ NICHT: Polygon, Höhen (die sind in building_geodata.db)
```

**Reihenfolge:**
1. Grunddaten laden → in `building_geodata.db` speichern
2. Enrichment ausführen → in `building_contexts.db` speichern
3. Projekt erstellen → nur Referenzen in `geruestbau.db`

**Beim Projekt-Laden (ConfiguratorPage):**
```
1. Projekt laden → egid aus geruestbau.db
2. geodata_service.get_by_egid(egid) → Polygon, Höhen aus building_geodata.db
3. building_context laden → Zonen, Terrain aus building_contexts.db
```

| Daten | Tabelle | Quelle |
|-------|---------|--------|
| Terrain-Höhe | `building_environment.terrain_data` | swissALTI3D |
| Hanglage | `building_environment.terrain_data` | swissALTI3D (Polygon-Ecken) |
| Zonen | `building_contexts.context_json` | Claude-Analyse / known_buildings.py |
| Foto-Analyse | `building_environment` | Claude Vision (geplant) |

### Hanglage-Klassifikation

| Klasse | Höhendifferenz | Bedeutung |
|--------|----------------|-----------|
| `eben` | < 0.5m | Kein Höhenausgleich nötig |
| `leicht` | 0.5 - 1.5m | Stellspindeln reichen |
| `mittel` | 1.5 - 3.0m | Ausgleichsrahmen nötig |
| `stark` | > 3.0m | Spezielle Fundamentierung |

### Enrichment-Caching (building_environment)

Die Enrichment-Daten werden persistent pro EGID gecacht:

```
1. SmartBuildingService._collect_terrain_data()
   │
   ├─ Cache prüfen: _load_terrain_from_environment(egid)
   │   → Falls vorhanden: TerrainProfile aus Cache laden
   │   → DataSource.CACHE setzen
   │
   └─ Falls nicht gecacht:
       ├─ swissALTI3D API aufrufen
       ├─ Polygon-Ecken samplen (max 8 Punkte)
       ├─ Hanglage berechnen (min/max/slope_m)
       └─ _save_terrain_to_environment(egid) → Cache speichern
```

**Cache-Struktur in building_environment.terrain_data:**
```json
{
  "height_m": 533.5,
  "min_terrain_m": 531.2,
  "max_terrain_m": 537.1,
  "slope_m": 5.9,
  "slope_class": "stark",
  "requires_level_compensation": true
}
```

**Implementierung:**
- `service.py:_load_terrain_from_environment()` - Cache lesen
- `service.py:_save_terrain_to_environment()` - Cache schreiben
- Tabelle: `building_environment` in `building_contexts.db`

### Zonen-Caching (building_contexts)

Gebäudezonen werden in `building_contexts` pro EGID gespeichert:

```
1. SmartBuildingService._create_default_zone()
   │
   ├─ Cache prüfen: _load_zones_from_building_context(egid)
   │   → Falls vorhanden + validiert: Zonen aus Cache
   │
   ├─ Falls nicht gecacht:
   │   ├─ Bekannte Gebäude? → known_buildings.py
   │   ├─ Kirche erkannt? → create_church_zones()
   │   ├─ Extreme Höhendifferenz? → Auto-Zonen (Hauptgebäude + Turm)
   │   └─ Standard: 1 Zone (Hauptgebäude)
   │
   └─ _save_zones_to_building_context(bundle) → Cache speichern
```

**Cache-Struktur in building_contexts.context_json (Zones):**
```json
{
  "zones": [
    {
      "id": "zone_1",
      "name": "Hauptgebäude",
      "type": "hauptgebaeude",
      "traufhoehe_m": 12.5,
      "firsthoehe_m": 16.2,
      "beruesten": true,
      "sonderkonstruktion": false,
      "confidence": 1.0
    },
    {
      "id": "zone_2",
      "name": "Turm",
      "type": "turm",
      "traufhoehe_m": 12.5,
      "firsthoehe_m": 45.0,
      "beruesten": true,
      "sonderkonstruktion": true,
      "confidence": 0.85
    }
  ]
}
```

**Implementierung:**
- `service.py:_load_zones_from_building_context()` - Cache lesen
- `service.py:_save_zones_to_building_context()` - Cache schreiben
- Tabelle: `building_contexts` in `building_contexts.db`

## 3. Projekt-Einstellungen

Werden pro Projekt gespeichert in `config` / `scaffold_config`.

### Fassaden-Vereinfachung (Douglas-Peucker)

| Einstellung | Feld | Beschreibung |
|-------------|------|--------------|
| Epsilon | `simplify_epsilon` | Toleranz für Punktreduktion |
| Winkeltoleranz | `simplify_angle_tolerance` | Für kollineare Segmente |

**Standard-Werte** (oft ungenau - Regler in 2D-Ansicht zur Anpassung):

| Epsilon | Effekt |
|---------|--------|
| 0.3m | Minimal (viele Fassaden) |
| 1.0m | Moderat (Standard) |
| 2.0m | Stark (wenige Fassaden) |

**Workflow:**
1. Projekt laden → Standard-Vereinfachung anwenden
2. Benutzer passt Regler in 2D-Ansicht an
3. Einstellung wird auf Projekt gespeichert
4. Beim erneuten Laden → gespeicherte Einstellung verwenden
5. Gerüst-Konfiguration bleibt konsistent

### Feldlängen-Ratio

| Einstellung | Feld | Beschreibung |
|-------------|------|--------------|
| Ratio | `field_length_ratio` | 0-100% (2.57m vs. 3.07m) |

| Slider | 2.57m Anteil | 3.07m Anteil |
|--------|--------------|--------------|
| 0% | 100% | 0% |
| 50% | 50% | 50% |
| 100% | 0% | 100% |

## 4. Dynamische Berechnungen

Werden NICHT gespeichert, bei jeder Interaktion neu berechnet.

### Nachbar-Gebäude

```
GET /api/v1/geruestbau/building/{egid}/neighbors
    ?radius_m=10   # 0, 5, oder 10m (Slider)
    &include_polygons=true
```

**Warum dynamisch?** Der Benutzer wählt den Radius je nach Bedarf:
- `0m`: Nur direkt angrenzende Gebäude (blockierte Fassaden)
- `5m`: Nah, relevant für Gerüstführung
- `10m`: Kontext für 3D-Visualisierung

## API-Endpunkte

### Grunddaten
```
GET /api/v1/smart-building/data?address=...
GET /api/v1/geruestbau/address/resolve?address=Knospenweg 2-10
```

### Enrichment
```
POST /api/v1/geruestbau/projects/{id}/enrich
```

### Projekt-Einstellungen
```
PUT /api/v1/geruestbau/projects/{id}/scaffold
GET /api/v1/geruestbau/projects/{id}/scaffold
```

### Dynamische Berechnungen
```
GET /api/v1/geruestbau/building/{egid}/neighbors?radius_m=10
```
