# SSE Building Data Flow - Vollständige Prozessdokumentation

**Stand:** 29.01.2026 15:00
**Status:** Aktualisiert - DEPRECATED Felder entfernt

---

## 1. Übersicht: Zwei SSE-Streams

Das System verwendet zwei separate SSE-Streams:

| Stream | Endpoint | Verwendung | Hook |
|--------|----------|------------|------|
| **Building Data** | `/building/data/stream` | Projekt erstellen | `useBuildingDataStream` |
| **Project Context** | `/projects/{id}/context/stream` | Projekt öffnen | `useProjectContextStream` |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐              ┌─────────────────────┐              │
│  │  NewProjectPage     │              │  ConfiguratorPage   │              │
│  │  GeodataStep        │              │                     │              │
│  └──────────┬──────────┘              └──────────┬──────────┘              │
│             │                                    │                          │
│             ▼                                    ▼                          │
│  ┌─────────────────────┐              ┌─────────────────────┐              │
│  │useBuildingDataStream│              │useProjectContextStream│            │
│  └──────────┬──────────┘              └──────────┬──────────┘              │
│             │                                    │                          │
└─────────────┼────────────────────────────────────┼──────────────────────────┘
              │                                    │
              ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐              ┌─────────────────────┐              │
│  │BuildingDataStream   │              │ProjectContextStream │              │
│  │Service              │              │Service              │              │
│  └──────────┬──────────┘              └──────────┬──────────┘              │
│             │                                    │                          │
│             ▼                                    ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SmartBuildingService                             │   │
│  │                    (10-Schritte Pipeline)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Building Data Stream - Events im Detail

### Endpoint
```
GET /api/v1/geruestbau/building/data/stream?address=Knospenweg%201-9,%20Bern
    &include_research=true
    &include_zones=true
    &include_terrain=true
    &force_refresh=false
```

---

### EVENT 1: geocoding

**Datenquelle:** swisstopo SearchServer API + GWR Identify

**Was passiert:**
1. Adresse wird an swisstopo Geocoding gesendet
2. Koordinaten (LV95) werden zurückgegeben
3. GWR-Identify liefert EGID für die Koordinaten

**SSE Response:**
```json
{
  "matched_address": "Knospenweg 1, 3006 Bern",
  "egid": "1243787",
  "coordinates": {"lv95_e": 2596298.5, "lv95_n": 1199798.2},
  "duration_ms": 123
}
```

**Frontend verwendet:** Adresse anzeigen, Karte zentrieren

---

### EVENT 2: gwr

**Datenquelle:** swisstopo GWR (Gebäude- und Wohnungsregister)

**Was passiert:**
- GWR-Daten werden aus dem Geocoding-Schritt extrahiert
- Bereits im Bundle vorhanden, separates Event für UI-Feedback

**SSE Response:**
```json
{
  "egid": "1243787",
  "floors": 2,
  "area_m2": 120,
  "category": 1020,
  "category_name": "Einfamilienhaus"
}
```

**Frontend verwendet:** Geschoss-Anzeige, Gebäudekategorie

---

### EVENT 3: polygon

**Datenquelle:** swissBUILDINGS3D (STAC API → GDB → building_3d.db)

**Was passiert:**
1. Prüft ob Gebäude in `building_3d.db` (Cache)
2. Falls nicht: Tile von swisstopo STAC API laden (~5-10s)
3. GDB parsen, alle Gebäude im Tile in DB speichern
4. Polygon + Seiten zurückgeben

**Daten die geladen werden:**
| Feld | Quelle | Beschreibung |
|------|--------|--------------|
| `polygon` | swissBUILDINGS3D Building_solid | Gebäude-Grundriss [[e,n], ...] |
| `sides` | Berechnet aus Polygon | Fassaden mit Start/End/Länge |
| `perimeter_m` | Berechnet | Umfang in Metern |
| `area_m2` | Berechnet | Grundfläche in m² |

**SSE Response:**
```json
{
  "egid": "1243787",
  "polygon": [[2596298.5, 1199798.2], [2596308.5, 1199798.2], ...],
  "sides": [{"start": {...}, "end": {...}, "length_m": 10.5, "direction": "N"}, ...],
  "perimeter_m": 42.5,
  "area_m2": 120.5,
  "cache_hit": true
}
```

**Frontend verwendet:**
- 2D-Ansicht: Polygon zeichnen
- 3D-Ansicht: Gebäude-Grundriss extrudieren
- Fassaden-Panel: Fassaden-Liste mit Längen

---

### EVENT 4: heights

**Datenquelle:** swissBUILDINGS3D (building_roofs Tabelle)

**Was passiert:**
1. `_load_roof_data_from_db()` lädt Dach-Daten
2. Setzt `roof_dach_min_m` (Traufe m ü.M.) und `roof_dach_max_m` (First m ü.M.)

**WICHTIG - Höhenberechnung:**
```
traufhoehe_m = roof_dach_min_m - terrain_z_min
firsthoehe_m = roof_dach_max_m - terrain_z_min

Beispiel Knospenweg 1:
  roof_dach_min_m = 562.94 m ü.M. (Traufe absolut)
  terrain_z_min   = 555.80 m ü.M. (tiefster Terrain-Punkt)
  → traufhoehe_m  = 7.14 m (relative Höhe über Terrain)
```

**SSE Response:**
```json
{
  "egid": "1243787",
  "gebaeudehoehe_m": 8.2,
  "source": "swissBUILDINGS3D",
  "has_3d_layers": true,
  "has_roof_geometry": true,
  "roof_dach_min_m": 562.94,
  "roof_dach_max_m": 565.2,
  "roof_type": "satteldach",
  "roof_orientation": "N-S",
  "roof_angle_deg": 28.5
}
```

**Frontend verwendet:**
- `roof_dach_min_m` - `terrain_z_min` = Traufhöhe für Gerüst
- `roof_type`, `roof_orientation` = 3D-Dach rendern

---

### EVENT 5: terrain

**Datenquelle:** swissBUILDINGS3D (building_walls Tabelle)

**Was passiert:**
1. `_collect_terrain_data()` lädt Wall-Daten
2. `reference_height_m` = min(building_walls.z_min) aller Wände
3. `facade_z_min/z_max` = Z-Werte pro Fassadenrichtung aus Wall-Layer

**WICHTIG - Hanglage wird im FRONTEND berechnet:**
```typescript
// Frontend: polygonSimplifier.ts
const wallMatch = matchFacadeToWall(facade, buildingWalls);
const facadeZMin = extractZFromRing(wallMatch.coords_3d).min;
const facadeZMax = extractZFromRing(wallMatch.coords_3d).max;
const slope_m = Math.abs(facadeZMax - facadeZMin);
```

**SSE Response:**
```json
{
  "egid": "1243787",
  "terrain_height_m": 555.8,
  "min_terrain_m": 554.2,
  "max_terrain_m": 556.5,
  "facade_z_min": {"N": 555.8, "E": 555.2, "S": 554.2, "W": 555.5},
  "facade_z_max": {"N": 561.3, "E": 561.3, "S": 561.3, "W": 561.3},
  "facade_heights_source": "wall_layer"
}
```

**Frontend verwendet:**
- `facade_z_min` = Stellspindel-Höhe pro Fassade
- `terrain_height_m` = Referenz-Höhe für 3D-Ansicht
- Hanglage-Berechnung aus `building_walls.geometry` Z-Koordinaten

---

### EVENT 6: zones

**Datenquelle:** known_buildings.py / Claude API / Auto-Berechnung

**Was passiert:**
1. Prüft ob bekanntes Gebäude (Bundeshaus, Münster, etc.)
2. Falls komplex: Claude API für Zonen-Analyse
3. Falls einfach: Auto-Zone "Hauptgebäude"

**SSE Response:**
```json
{
  "egid": "1243787",
  "zones": [
    {"id": "zone_1", "name": "Hauptgebäude", "zone_type": "hauptgebaeude",
     "traufhoehe_m": 5.5, "firsthoehe_m": 8.2, "beruesten": true}
  ],
  "complexity": "simple",
  "source": "auto"
}
```

---

### EVENT 7: research (optional)

**Datenquelle:** known_buildings.py / Claude Sonnet API

**SSE Response:**
```json
{
  "egid": "1243787",
  "building_name": null,
  "building_type": "Einfamilienhaus",
  "architectural_style": null,
  "source": "auto"
}
```

---

### EVENT 8: complete

**Was passiert:**
- `_calculate_object_data()` berechnet Union aller Polygone
- `projectBuildings[]` enthält Metadaten aller Gebäude

**SSE Response:**
```json
{
  "status": "ok",
  "duration_ms": 1523,
  "building_count": 1,
  "object_data": {
    "polygon": [[...], [...], ...],
    "facades_object": [...],
    "roof_object": {"z_min": 562.94, "z_max": 565.2},
    "projectBuildings": [{"egid": "1243787", "address": "...", "center_e": ..., "center_n": ...}],
    "total_area_m2": 120,
    "total_perimeter_m": 42.5,
    "avg_traufhoehe_m": 7.14,
    "building_count": 1
  },
  "bundle": {...}
}
```

---

## 3. Datenquellen-Übersicht

### swissBUILDINGS3D Tabellen

| Tabelle | Felder | Verwendet für |
|---------|--------|---------------|
| `buildings_3d` | polygon, center_e/n, tile_id | Grundriss, Nachbar-Suche |
| `building_roofs` | dach_min, dach_max, roof_type | Höhen, Dachform |
| `building_walls` | z_min, z_max, geometry_wkb | Terrain, Fassaden-Höhen |

### Höhen-Berechnungsformel

```
KORREKT (seit 16.01.2026):
traufhoehe_m = roof_dach_min_m - min(facade_z_min.values())
firsthoehe_m = roof_dach_max_m - min(facade_z_min.values())

DEPRECATED (entfernt 29.01.2026):
traufhoehe_m, firsthoehe_m direkt aus Bundle
slope_m, slope_class vom Backend
```

---

## 4. DEPRECATED Felder (entfernt 29.01.2026)

Die folgenden Felder werden **NICHT MEHR** vom Backend gesendet:

| Feld | Grund | Ersatz |
|------|-------|--------|
| `traufhoehe_m` | Falsch bei Hanglagen | `roof_dach_min_m - terrain_z_min` |
| `firsthoehe_m` | Falsch bei Hanglagen | `roof_dach_max_m - terrain_z_min` |
| `slope_m` | Frontend berechnet präziser | `building_walls.geometry` Z-Koordinaten |
| `slope_class` | Frontend berechnet präziser | Aus `slope_m` ableiten |

---

## 5. Änderungen 29.01.2026 (diese Session)

### Was wurde entfernt:

**building_data_stream.py:**
- `traufhoehe_m`, `firsthoehe_m` aus heights Event
- `slope_m`, `slope_class` aus terrain Event
- `traufhoehe_m`, `firsthoehe_m` aus `_bundle_to_dict()`
- `slope_m`, `slope_class` aus terrain_dict in `_bundle_to_dict()`

### Was wurde in der VORHERIGEN Session geändert (ohne Genehmigung):

1. **building_data_stream.py:556-586** - Prefetch nach Schleife statt pro Gebäude
   - Objekt-Mittelpunkt berechnen (INLINE)
   - 100m Radius statt 5m
   - skip_egids für alle geladenen Gebäude

2. **tile_prefetch.py** - DB-Fallback wenn GDB nicht existiert
   - Wenn GDB gelöscht (status='cleaned'), aus DB laden

3. **building_3d_service.py** - Neue Funktion `get_neighbors_by_coordinates()`
   - Koordinaten-basierte Nachbar-Suche

4. **service.py** - Import-Fix
   - `get_layer_fetcher` → `get_layer_fetcher_service`

---

## 6. Offene Punkte

### Vorgeschlagene Verbesserungen:

1. **object_geometry.py** - Wiederverwendbare Funktionen:
   - `calculate_centroid(bundles)`
   - `calculate_union(bundles)`

2. **object_data.centroid** - Objekt-Mittelpunkt im complete Event

3. **Prefetch-Logik** - `load_from_db_if_no_gdb` Parameter

---

## 7. Frontend-Erwartungen (TypeScript Interfaces)

Siehe `geruestbau-app/src/hooks/useBuildingDataStream.ts`:

```typescript
interface HeightsData {
  gebaeudehoehe_m: number | null;
  source: string;
  has_3d_layers?: boolean;
  roof_dach_min_m?: number | null;  // Absolut m ü.M.
  roof_dach_max_m?: number | null;  // Absolut m ü.M.
  roof_type?: string | null;
  roof_orientation?: string | null;
  roof_angle_deg?: number | null;
  // ENTFERNT: traufhoehe_m, firsthoehe_m
}

interface TerrainData {
  terrain_height_m: number | null;
  facade_z_min?: Record<string, number>;
  facade_z_max?: Record<string, number>;
  facade_heights_source?: 'wall_layer' | 'terrain_sampled' | 'global';
  // ENTFERNT: slope_m, slope_class (Frontend berechnet)
}
```
