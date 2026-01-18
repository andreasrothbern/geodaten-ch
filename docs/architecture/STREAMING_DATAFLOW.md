# Datenfluss: SSE SmartBuildingService → GeruestbauData

**Stand: 16.01.2026**

Dieses Dokument beschreibt den Datenfluss von der SSE-API (SmartBuildingService) bis zur Speicherung in `buildings_data`.

## Konzept

```
┌─────────────────────────────────────────────────────────────────┐
│                         PROJEKT                                  │
├─────────────────────────────────────────────────────────────────┤
│  address: "Knospenweg 4-6, Bern"    ◄── Eingegebene Adresse     │
│  name: "Fassadensanierung Knospenweg"                           │
│  client_name: "Bauherr AG"                                       │
│  ...                                                             │
├─────────────────────────────────────────────────────────────────┤
│  buildings_data:                     ◄── Aufgelöste Gebäude     │
│    "1243790": { GeruestbauData }     ◄── Knospenweg 4           │
│    "1243792": { GeruestbauData }     ◄── Knospenweg 6           │
│                                                                  │
│  Alle Gebäude sind GLEICHWERTIG - kein "primäres" Gebäude!      │
└─────────────────────────────────────────────────────────────────┘
```

## Übersicht Datenfluss

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  SSE Stream      │ ──► │  GeruestbauData  │ ──► │  buildings_data  │
│  (Bundle)        │     │  (pro Gebäude)   │     │  (EGID als Key)  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## 1. Single-Address Beispiel: "Kramgasse 49, 3011 Bern"

### 1.1 SSE Response (BuildingDataBundle)

```
GET /api/v1/smart-building/stream?address=Kramgasse%2049,%203011%20Bern
```

```json
{
  "egid": "1243787",
  "address_matched": "Kramgasse 49, 3011 Bern",
  "lv95_e": 2600656.5,
  "lv95_n": 1199497.2,

  "polygon": [[2600652.1, 1199492.3], [2600661.2, 1199492.8], ...],
  "polygon_point_count": 8,
  "perimeter_m": 45.6,
  "footprint_area_m2": 125.4,

  "traufhoehe_m": 12.5,
  "firsthoehe_m": 16.2,
  "gebaeudehoehe_m": 16.2,
  "height_source": "swissbuildings3d",

  "terrain": {
    "reference_height_m": 535.4,
    "min_terrain_m": 534.1,
    "max_terrain_m": 536.2,
    "slope_m": 2.1,
    "slope_class": "leicht"
  },

  "zones": [{
    "id": "zone_1",
    "name": "Hauptgebäude",
    "zone_type": "hauptgebaeude",
    "traufhoehe_m": 12.5,
    "firsthoehe_m": 16.2,
    "beruesten": true,
    "sonderkonstruktion": false
  }],

  "complexity": "simple",
  "research_source": "auto"
}
```

### 1.2 Transformation zu GeruestbauData

`project_service._build_geruestbaudata()` konvertiert das Bundle:

```json
{
  "building": {
    "egid": "1243787",
    "address": "Kramgasse 49, 3011 Bern",
    "polygon": [[2600652.1, 1199492.3], ...],
    "polygon_simplified": null,
    "center_e": 2600656.5,
    "center_n": 1199497.2,
    "perimeter_m": 45.6,
    "area_m2": 125.4
  },
  "heights": {
    "traufhoehe_m": 12.5,
    "firsthoehe_m": 16.2,
    "gebaeudehoehe_m": 16.2,
    "terrain_height_m": 535.4,
    "source": "swissBUILDINGS3D"
  },
  "walls": [
    {"gebaeudeeinheit": "...", "z_min": 535.4, "z_max": 547.9, "coords_3d": [...]}
  ],
  "roofs": [
    {"gebaeudeeinheit": "...", "dach_min": 547.9, "dach_max": 551.6, "coords_3d": [...]}
  ],
  "terrain": {
    "height_m": 535.4,
    "min_m": 534.1,
    "max_m": 536.2,
    "slope_m": 2.1,
    "slope_class": "leicht",
    "requires_level_compensation": true
  },
  "zones": [{
    "id": "zone_1",
    "name": "Hauptgebäude",
    "zone_type": "hauptgebaeude",
    "traufhoehe_m": 12.5,
    "firsthoehe_m": 16.2,
    "beruesten": true,
    "sonderkonstruktion": false,
    "confidence": 1.0
  }],
  "fetched_at": "2026-01-16T10:30:00.000Z",
  "data_quality": "complete"
}
```

### 1.3 Speicherung in buildings_data

```json
{
  "1243787": { ... GeruestbauData ... }
}
```

**EGID ist der Key** - ermöglicht einheitliche Struktur für Single- und Multi-Building.

---

## 2. Multi-Address Beispiel: "Knospenweg 4-6, 3006 Bern"

### 2.1 Adress-Auflösung

```
GET /api/v1/geruestbau/address/resolve?address=Knospenweg%204-6,%203006%20Bern
```

```json
{
  "parsed": {
    "street": "Knospenweg",
    "numbers": [4, 6],
    "city": "Bern"
  },
  "buildings": [
    {"address": "Knospenweg 4, 3006 Bern", "egid": "1243790", "traufhoehe_m": 5.54, ...},
    {"address": "Knospenweg 6, 3006 Bern", "egid": "1243792", "traufhoehe_m": 5.54, ...}
  ],
  "building_count": 2
}
```

### 2.2 Datensammlung

Für **jede EGID** wird ein BuildingDataBundle via SmartBuildingService geladen:

```
"1243790" → SSE Stream → BuildingDataBundle → GeruestbauData
"1243792" → SSE Stream → BuildingDataBundle → GeruestbauData
```

Alle Gebäude werden **gleichwertig** behandelt.

### 2.3 Projekt-Struktur

```json
{
  "id": "proj_123",
  "name": "Fassadensanierung Knospenweg",
  "address": "Knospenweg 4-6, 3006 Bern",     // ◄── Eingegebene Adresse
  "client_name": "Bauherr AG",

  "buildings_data": {                          // ◄── Aufgelöste Gebäude
    "1243790": { ... },                        // Knospenweg 4
    "1243792": { ... }                         // Knospenweg 6
  }
}
```

### 2.4 Speicherung in buildings_data

```json
{
  "1243790": {
    "building": {
      "egid": "1243790",
      "address": "Knospenweg 4, 3006 Bern",
      "polygon": [[2596297.2, 1199800.5], ...],
      "center_e": 2596299.0,
      "center_n": 1199805.0,
      "perimeter_m": 32.4,
      "area_m2": 65.2
    },
    "heights": {"traufhoehe_m": 5.54, "firsthoehe_m": 8.2, ...},
    "walls": [...],
    "roofs": [...],
    "terrain": {"slope_m": 1.8, "slope_class": "leicht", ...},
    "zones": [...]
  },

  "1243792": {
    "building": {
      "egid": "1243792",
      "address": "Knospenweg 6, 3006 Bern",
      "polygon": [[2596299.5, 1199812.3], ...],
      "center_e": 2596301.0,
      "center_n": 1199815.0,
      "perimeter_m": 32.4,
      "area_m2": 65.2
    },
    "heights": {"traufhoehe_m": 5.54, "firsthoehe_m": 8.2, ...},
    "walls": [...],
    "roofs": [...],
    "terrain": {"slope_m": 1.8, "slope_class": "leicht", ...},
    "zones": [...]
  }
}
```

**Beide Gebäude sind gleichwertig** - die Reihenfolge der Keys hat keine Bedeutung.

---

## 3. Frontend-Zugriff

### 3.1 Hilfsfunktionen (types/project.ts)

```typescript
// Alle EGIDs im Projekt (gleichwertig!)
getBuildingEgids(project: ProjectWithGeruestbaudata): string[]

// Daten für eine bestimmte EGID
getBuildingData(project: ProjectWithGeruestbaudata, egid: string): GeruestbauData | null

// Über alle Gebäude iterieren
forEachBuilding(project: ProjectWithGeruestbaudata, callback: (egid, data) => void): void

// Prüfungen
getBuildingCount(project: ProjectWithGeruestbaudata): number
isMultiBuilding(project: ProjectWithGeruestbaudata): boolean
```

### 3.2 Verwendung in ConfiguratorPage.tsx

```typescript
const project: ProjectWithGeruestbaudata = await geruestbauApi.getProject(id);

// Alle EGIDs holen (gleichwertig, keine Priorisierung!)
const egids = getBuildingEgids(project);

// Single-Building: ["1243787"]
// Multi-Building:  ["1243790", "1243792"]

// Über alle Gebäude iterieren
forEachBuilding(project, (egid, data) => {
  console.log(`Gebäude ${egid}: ${data.building.address}`);
  // Jedes Gebäude gleichwertig verarbeiten
});

// Oder mit explizitem EGID-Zugriff
const buildingData = project.buildings_data?.["1243790"];
if (buildingData) {
  const geodata = convertGeruestbaudataToGeodata(buildingData);
}
```

### 3.3 UI-Darstellung bei Multi-Building

Bei mehreren Gebäuden zeigt das UI alle gleichwertig an:
- **Kartenansicht**: Alle Polygone auf der Karte
- **3D-Ansicht**: Alle Gebäude im 3D-Viewer
- **Fassadenliste**: Fassaden aller Gebäude (gruppiert nach EGID)

---

## 4. Transformation-Mapping

| SSE BuildingDataBundle | → | GeruestbauData |
|------------------------|---|----------------|
| `egid` | → | `building.egid` |
| `address_matched` | → | `building.address` |
| `lv95_e`, `lv95_n` | → | `building.center_e`, `building.center_n` |
| `polygon` | → | `building.polygon` |
| `perimeter_m` | → | `building.perimeter_m` |
| `footprint_area_m2` | → | `building.area_m2` |
| `traufhoehe_m` | → | `heights.traufhoehe_m` |
| `firsthoehe_m` | → | `heights.firsthoehe_m` |
| `gebaeudehoehe_m` | → | `heights.gebaeudehoehe_m` |
| `terrain.reference_height_m` | → | `heights.terrain_height_m` |
| `terrain.*` | → | `terrain.*` |
| `zones[]` | → | `zones[]` |
| (aus layer_fetcher) | → | `walls[]`, `roofs[]` |

---

## 5. Datenbank-Schema

### 5.1 projects Tabelle (geruestbau.db)

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,            -- UUID, eindeutig pro Projekt (NICHT EGID!)
  name TEXT NOT NULL,
  address TEXT NOT NULL,          -- Eingegebene Adresse (z.B. "Knospenweg 4-6, Bern")
  egid TEXT,                      -- Legacy: Einzelne EGID (deprecated, nicht PK!)
  buildings TEXT,                 -- JSON: BuildingEntry[] (Referenzen mit Adresse/EGID)
  buildings_data TEXT,            -- JSON: Record<EGID, GeruestbauData>
  status TEXT DEFAULT 'draft',
  config TEXT,                    -- JSON: ScaffoldConfig
  ...
);
```

### 5.2 Primary Key vs. EGID - WICHTIG!

```
┌─────────────────────────────────────────────────────────────────┐
│  PRIMARY KEY = projects.id (UUID)                               │
│  NICHT EGID!                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Ein Gebäude (EGID) kann in MEHREREN Projekten vorkommen:      │
│                                                                 │
│  Projekt "proj_001" (Fassadensanierung 2024):                  │
│    buildings_data: {"1243790": {...}}                          │
│                                                                 │
│  Projekt "proj_002" (Dacharbeiten 2026):                       │
│    buildings_data: {"1243790": {...}}  ◄── Gleiche EGID, OK!   │
│                                                                 │
│  EGID ist nur Key INNERHALB des JSON, nicht DB Primary Key.    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 buildings_data Format

Sowohl Single- als auch Multi-Building verwenden die **gleiche Struktur**:

```
// Single-Building (1 Gebäude):
{
  "1234567": GeruestbauData
}

// Multi-Building (n Gebäude, alle gleichwertig):
{
  "1234567": GeruestbauData,
  "1234568": GeruestbauData,
  "1234569": GeruestbauData
}
```

**Wichtig**:
- `projects.id` = Primary Key (UUID, eindeutig pro Projekt)
- EGID = Key innerhalb von `buildings_data` JSON (kann in mehreren Projekten vorkommen)
- Alle Gebäude innerhalb eines Projekts sind gleichwertig

---

## 6. Relevante Dateien

| Datei | Beschreibung |
|-------|--------------|
| `backend/app/services/smart_building/models.py` | BuildingDataBundle Definition |
| `backend/app/services/smart_building/service.py` | SmartBuildingService (SSE) |
| `backend/app/services/geruestbau/project_service.py` | Speicherung als GeruestbauData |
| `geruestbau-app/src/types/project.ts` | Frontend TypeScript Interfaces |
| `geruestbau-app/src/pages/ConfiguratorPage.tsx` | Frontend Verwendung |

---

## 7. Legacy-Kompatibilität

### 7.1 Alte Struktur (vor 16.01.2026)

```json
{
  "geruestbaudata": { ... }  // Einzelnes Objekt
}
```

### 7.2 Neue Struktur (ab 16.01.2026)

```json
{
  "buildings_data": {
    "EGID": { ... }          // EGID als Key
  }
}
```

### 7.3 Migration

`project_service.get_project_with_data()` migriert automatisch:

```python
# Legacy-Fallback
if not buildings_data and row['geruestbaudata']:
    geruestbaudata = json.loads(row['geruestbaudata'])
    if geruestbaudata and geruestbaudata.get('building', {}).get('egid'):
        egid = geruestbaudata['building']['egid']
        buildings_data = {egid: geruestbaudata}  # Auto-Migration
```

---

# Teil 2: Neighbor-Enrichment (100m Radius)

> **Stand: 18.01.2026 11:00**
> **Status: IMPLEMENTIERT**

## 8. Begriffe

### 8.1 "Objekt" vs. "Gebäude"

| Begriff | Bedeutung | Beispiel |
|---------|-----------|----------|
| **Objekt** | Das Projekt-Objekt (1 oder mehrere Gebäude) | "Knospenweg 2-6" = 3 Gebäude |
| **Gebäude** | Ein einzelnes Gebäude mit EGID | EGID 1243790 = Knospenweg 4 |
| **Nachbarn** | Gebäude im Umkreis des Objekts | 53 Gebäude im 100m Radius |

**Wichtig:** Ein "Objekt" kann aus mehreren Gebäuden bestehen (Multi-Adress)!

---

## 9. Use Case: Terrain-Sampling für Nachbarn

### 9.1 Problem

Aktuell haben Nachbargebäude nur **ungenaue Höhendaten** aus `GELAENDEPUNKT`
(swissBUILDINGS3D). Bei Hanglagen weicht dies um **1-2m** vom tatsächlichen
Terrain ab.

**Beispiel Knospenweg 4, Bern (Hanglage):**

```
Objekt (Knospenweg 4):
  └─ Terrain-Sampling: 8 Polygon-Ecken via swissALTI3D
  └─ facade_z_min: 555.8m, facade_z_max: 557.6m
  └─ Korrekte Gerüst-Berechnung!

Nachbar (Knospenweg 2, 8m entfernt):
  └─ Nur GELAENDEPUNKT: 556.5m (Gebäudezentrum)
  └─ Tatsächliches Terrain: 554.2m - 558.1m
  └─ FEHLER: 2.3m Ungenauigkeit bei Hanglage!
```

### 9.2 Ziel

Alle Nachbargebäude im konfigurierbaren Radius sollen **vollständige 3D-Daten** erhalten:
- 3D-Geometrie (Roof, Wall Layer)
- Terrain-Sampling (terrain_z_min, terrain_z_max)
- Korrekte Höhenberechnung

---

## 10. Neuer Parameter: `neighbor_enrichment_radius_m`

### 10.1 Definition

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `neighbor_enrichment_radius_m` | int | 100 | Radius für vollständiges Nachbar-Enrichment |

### 10.2 Werte

| Wert | Verhalten |
|------|-----------|
| `0` | Kein Enrichment - Nachbarn nur mit Basis-Daten |
| `50` | Nachbarn im 50m-Radius erhalten 3D-Layer + Terrain |
| `100` | Nachbarn im 100m-Radius erhalten 3D-Layer + Terrain (STANDARD) |
| `150` | Nachbarn im 150m-Radius (für Grossprojekte) |

### 10.3 Verwendung

**API:**
```
GET /api/v1/smart-building/data
    ?address=Knospenweg%204,%20Bern
    &neighbor_enrichment_radius_m=100
```

**Python:**
```python
bundle = await service.collect_all_data(
    address="Knospenweg 4, Bern",
    neighbor_enrichment_radius_m=100
)
```

---

## 11. Zwei-Stufen Datenfluss (User-Flow)

> **NEU 18.01.2026:** Vereinfachte Architektur - prefetch_neighbors() lädt das ganze Tile!

### 11.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZWEI-STUFEN DATENFLUSS (User-Flow)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STUFE 1: collect_all_data(address)                             │
│  ═══════════════════════════════════                            │
│  └─ Lädt ALLE Daten für das Objekt (1 oder mehrere Gebäude)    │
│  └─ Inkl. GWR, Zonen, Research, SUVA, Qualität                 │
│  └─ SSE-Events: geocoding → gwr → polygon → heights → ...      │
│  └─ ✅ USER ERHÄLT ANTWORT                                      │
│                                                                 │
│           │                                                     │
│           ▼ schedule (Background)                               │
│                                                                 │
│  STUFE 2: prefetch_neighbors(e, n, radius_m=100)                │
│  ═══════════════════════════════════════════════                │
│  └─ 🔄 SCHEDULED (läuft im Background)                          │
│  └─ Lädt das GANZE TILE mit differenziertem Enrichment:        │
│      │                                                          │
│      ├─ ENRICHED (≤100m): Building + Roof + Wall + Terrain     │
│      │   └─ Sortiert nach Distanz (5m zuerst!)                 │
│      │   └─ Für blocked_facades + 3D-Visualisierung            │
│      │                                                          │
│      └─ BASIC (>100m): NUR Building Layer                      │
│          └─ Für zukünftige Koordinaten-Lookups                 │
│                                                                 │
│  └─ Parquet-Pipeline: GDB → Parquet → DuckDB                   │
│  └─ Cleanup: Parquets + GDB werden gelöscht                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    BATCH-IMPORT (Separat)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  prefetch_tile(tile_id) - NUR für scripts/import_tiles.py      │
│  ═══════════════════════════════════════════════════════════    │
│  └─ Läuft OHNE User-Request (Pre-Deployment)                   │
│  └─ NUR Building Layer (kein Enrichment)                       │
│  └─ Keine Roof/Wall/Terrain-Daten                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 STUFE 1: collect_all_data (Objekt)

```
┌─────────────────────────────────────────────────────────────────┐
│  STUFE 1: collect_all_data(address)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Für JEDES Gebäude im Objekt:                                   │
│      │                                                          │
│      ├─► 1. _collect_geocoding()                                │
│      │       └─ swisstopo: Adresse → LV95 Koordinaten           │
│      │                                                          │
│      ├─► 2. _collect_gwr_data()                                 │
│      │       └─ swisstopo GWR: → EGID, Geschosse, Fläche, GKAT  │
│      │                                                          │
│      ├─► 3. _collect_building_3d_data()                         │
│      │       └─ Polygon, Höhen, 3D-Layer (Roof, Wall)           │
│      │                                                          │
│      ├─► 4. _collect_terrain_data()                             │
│      │       └─ swissALTI3D: 8 Polygon-Ecken                    │
│      │       └─ facade_z_min, facade_z_max, slope_m             │
│      │                                                          │
│      ├─► 5. _collect_sonnendach_data()                          │
│      │       └─ BFE: Dachneigung, Azimut, Überstand             │
│      │                                                          │
│      ├─► 6. _create_default_zone() / _collect_zones_analysis()  │
│      │       └─ Auto-Zone oder Claude Sonnet Analyse            │
│      │                                                          │
│      ├─► 7. _collect_research_data()                            │
│      │       └─ known_buildings.py oder Claude Recherche        │
│      │       └─ building_name, architectural_style              │
│      │                                                          │
│      ├─► 8. _calculate_suva_access_points()                     │
│      │       └─ SUVA-konforme Zugangspunkte (max 50m Abstand)   │
│      │                                                          │
│      └─► 9. _assess_data_quality()                              │
│              └─ overall_quality, warnings                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.3 STUFE 2: prefetch_neighbors(e, n, radius_m) - SCHEDULED

```
┌─────────────────────────────────────────────────────────────────┐
│  STUFE 2: prefetch_neighbors(e, n, radius_m=100)                │
│  🔄 SCHEDULED - Läuft im Background nach User-Antwort          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SIGNATUR: prefetch_neighbors(e, n, radius_m=100)               │
│  ═══════════════════════════════════════════════════════════════│
│                                                                 │
│  EIN GDB-DURCHLAUF - ZWEI KATEGORIEN:                           │
│  ════════════════════════════════════                           │
│                                                                 │
│  1. Building_solid Layer EINMAL parsen (alle Gebäude)          │
│     └─ Distanz zu (e, n) berechnen                             │
│     └─ Nach Distanz aufteilen:                                 │
│                                                                 │
│      ┌─────────────────────┐    ┌─────────────────────┐        │
│      │  ENRICHED (≤100m)   │    │  BASIC (>100m)      │        │
│      │  ─────────────────  │    │  ─────────────      │        │
│      │  + Roof_solid Layer │    │  NUR Building       │        │
│      │  + Wall Layer       │    │  (Polygon, Zentrum) │        │
│      │  + Terrain-Sampling │    │  KEIN Roof/Wall     │        │
│      │  + Höhen-Berechnung │    │  KEIN Terrain       │        │
│      │                     │    │                     │        │
│      │  Sortiert: 5m zuerst│    │  Unsortiert         │        │
│      └──────────┬──────────┘    └──────────┬──────────┘        │
│                 │                          │                    │
│                 ▼                          ▼                    │
│          ┌────────────┐             ┌────────────┐             │
│          │ Parquet 1  │             │ Parquet 2  │             │
│          │ (enriched) │             │ (basic)    │             │
│          └─────┬──────┘             └─────┬──────┘             │
│                │                          │                    │
│                ▼                          ▼                    │
│           DuckDB Import              DuckDB Import             │
│           (ZUERST!)                  (DANACH)                  │
│           has_3d_layers=1            has_3d_layers=0           │
│                                                                 │
│  2. Terrain-Sampling (NUR für enriched)                        │
│     └─ 8 Polygon-Ecken via swissALTI3D                         │
│     └─ terrain_z_min, terrain_z_max, terrain_slope_m           │
│                                                                 │
│  3. Korrekte Höhen berechnen (NUR für enriched)                │
│     └─ traufhoehe = dach_min - terrain_z_min                   │
│     └─ UPDATE buildings_3d                                     │
│                                                                 │
│  4. CLEANUP                                                     │
│     └─ Parquets löschen                                        │
│     └─ GDB löschen (mark_tile_cleaned)                         │
│                                                                 │
│  VORTEILE:                                                      │
│  ─────────                                                      │
│  ✓ GDB nur 1× öffnen (schneller)                               │
│  ✓ Roof/Wall nur für ≤100m (spart ~80% Parsing)               │
│  ✓ Terrain nur für ≤100m (spart API-Calls)                    │
│  ✓ 5m-Nachbarn zuerst → blocked_facades sofort verfügbar      │
│  ✓ Ganzes Tile gecacht → spätere Anfragen sofort              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.4 BATCH-IMPORT: import_tiles.py (Parquet-Pipeline)

> **Stand 18.01.2026 03:55:** `scripts/batch/import_tiles.py` verwendet die
> Parquet-Pipeline mit ALLEN 3 Layern (Building + Roof + Wall).

**WICHTIG: STAC Tile-Versionen**
- Ältere Versionen (2016, 2018) haben oft KEINE EGIDs
- IMMER die NEUESTE Version wählen (2021+)
- Der Import wählt automatisch die neueste verfügbare Version

```
┌─────────────────────────────────────────────────────────────────┐
│  import_tiles.py --region <name>                                │
│  Batch-Import ohne User-Request                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STAC API: Tile-Discovery                                       │
│  ═══════════════════════════                                    │
│                                                                 │
│  1. Region-BBox → STAC API Query                                │
│  2. Alle Versionen pro Tile sammeln                             │
│  3. NEUESTE Version wählen (2021 > 2018 > 2016)                │
│     → Ältere Versionen haben keine EGIDs!                      │
│                                                                 │
│  PIPELINE: GDB → Stream → Parquet → DuckDB                      │
│  ══════════════════════════════════════════                     │
│                                                                 │
│  1. ALLE 3 Layer parallel streamen:                             │
│     ├─ Building_solid (Gebäude mit EGID)                        │
│     ├─ Roof_solid (Dachflächen)                                │
│     └─ Wall (Fassaden mit z_min/z_max)                         │
│                                                                 │
│  2. Layer → Parquet (parallel, je ~5-40s)                       │
│     └─ Gebäude OHNE EGID werden übersprungen                   │
│                                                                 │
│  3. Parquet → DuckDB (Bulk-UPSERT)                              │
│     └─ Bestehende Gebäude werden NICHT überschrieben           │
│        (WHERE has_3d_layers = 0 OR has_3d_layers IS NULL)      │
│                                                                 │
│  ENTHALTEN:                                                     │
│      ✓ Building_solid-Layer                                     │
│      ✓ Roof_solid-Layer (dach_min, dach_max)                   │
│      ✓ Wall-Layer (z_min, z_max)                               │
│                                                                 │
│  NICHT enthalten (wird bei User-Request hinzugefügt):          │
│      ✗ Terrain-Sampling (swissALTI3D)                          │
│      ✗ Fassaden-Höhen aus Wall-Matching                        │
│                                                                 │
│  PERFORMANCE (gemessen 18.01.2026):                             │
│      111 Gebäude/Sekunde (inkl. Roof + Wall)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Regionen-Definition (LV95 BBox):**

| Region | BBox | Tiles | Anmerkung |
|--------|------|-------|-----------|
| `test` | (2595000, 1198000, 2598000, 1200000) | ~2-4 | Knospenweg/Breitenrain (hat EGIDs!) |
| `bern` | (2596000, 1197000, 2604000, 1203000) | ~20 | Stadt Bern |
| `zurich` | (2676000, 1243000, 2690000, 1255000) | ~50 | Stadt Zürich |
| `basel` | (2608000, 1264000, 2616000, 1272000) | ~16 | Stadt Basel |

**ACHTUNG:** Die Bundeshaus-Region (E=2600000) hat in der STAC API keine Gebäude mit EGIDs!
Die `test`-Region verwendet daher den Knospenweg-Bereich (E=2595000-2598000).

### 11.5 Obsolete Funktionen (werden entfernt)

| Alte Funktion | Grund |
|---------------|-------|
| `load_neighbors_and_save()` | Ersetzt durch `prefetch_neighbors()` Parquet-Pipeline |
| `find_immediate_neighbors()` | Redundant - `prefetch_neighbors()` hat Radius-Filter |
| `schedule_prefetch_with_neighbors()` | Ersetzt durch `prefetch_neighbors(e, n, radius_m=100)` |

**NEU:** `prefetch_neighbors(e, n, radius_m=100)` - Signatur mit zwei parallelen Jobs (5m + radius_m), alle 3 Layer + Terrain

---

## 12. Daten-Vergleich: Objekt vs. Nachbarn vs. Rest

### 12.1 Vollständige Übersicht

| Datenfeld | Objekt | Nachbarn (100m) | Rest (Tile) | Quelle / Stufe |
|-----------|:------:|:---------------:|:-----------:|----------------|
| **IDENTIFIKATION** |||||
| egid | ✅ | ✅ | ✅ | GDB Building-Layer |
| gebaeudeeinheit | ✅ | ✅ | ✅ | GDB Building-Layer |
| tile_id | ✅ | ✅ | ✅ | Berechnet |
| **GEOMETRIE (Building-Layer)** |||||
| polygon | ✅ | ✅ | ✅ | GDB Building-Layer |
| center_e, center_n | ✅ | ✅ | ✅ | Berechnet |
| area_m2, perimeter_m | ✅ | ✅ | ✅ | Berechnet |
| sides[] (Fassaden) | ✅ | ❌ | ❌ | Berechnet (nur Objekt) |
| **HÖHEN AUS BUILDING-LAYER** |||||
| GELAENDEPUNKT | ✅ | ✅ | ✅ | GDB Building-Layer |
| DACH_MIN, DACH_MAX | ✅ | ✅ | ✅ | GDB Building-Layer |
| GESAMTHOEHE | ✅ | ✅ | ✅ | GDB Building-Layer |
| **HÖHEN (berechnet)** |||||
| traufhoehe_m | ✅ | ✅ | ⚠️ | Stufe 2: aus Roof + Terrain |
| firsthoehe_m | ✅ | ✅ | ⚠️ | Stufe 2: aus Roof + Terrain |
| gebaeudehoehe_m | ✅ | ✅ | ✅ | GESAMTHOEHE |
| **3D-LAYER (Roof_solid + Wall)** |||||
| has_3d_layers | ✅ | ✅ | ❌ | Flag (Stufe 2) |
| building_roofs | ✅ | ✅ | ❌ | GDB Roof_solid-Layer (Stufe 2) |
| └─ dach_min, dach_max (m ü.M.) | ✅ | ✅ | ❌ | GDB Roof_solid-Layer |
| └─ geometry_wkb (3D) | ✅ | ✅ | ❌ | GDB Roof_solid-Layer |
| building_walls | ✅ | ✅ | ❌ | GDB Wall-Layer (Stufe 2) |
| └─ z_min, z_max (m ü.M.) | ✅ | ✅ | ❌ | GDB Wall-Layer |
| └─ geometry_wkb (3D) | ✅ | ✅ | ❌ | GDB Wall-Layer |
| **TERRAIN (swissALTI3D)** |||||
| terrain_z_min | ✅ | ✅ | ❌ | swissALTI3D (Stufe 1+2) |
| terrain_z_max | ✅ | ✅ | ❌ | swissALTI3D (Stufe 1+2) |
| terrain_slope_m | ✅ | ✅ | ❌ | Berechnet |
| terrain_sampled_at | ✅ | ✅ | ❌ | Timestamp |
| facade_z_min (pro Seite) | ✅ | ❌ | ❌ | swissALTI3D (nur Objekt) |
| facade_z_max (pro Seite) | ✅ | ❌ | ❌ | swissALTI3D (nur Objekt) |
| **GWR-DATEN (swisstopo API)** |||||
| gwr_floors | ✅ | ❌ | ❌ | swisstopo GWR |
| gwr_area_m2 | ✅ | ❌ | ❌ | swisstopo GWR |
| gwr_category (GKAT) | ✅ | ❌ | ❌ | swisstopo GWR |
| gwr_baujahr | ✅ | ❌ | ❌ | swisstopo GWR |
| **DACH-ANALYSE** |||||
| roof_type | ✅ | ❌ | ❌ | Berechnet |
| roof_angle_deg | ✅ | ❌ | ❌ | Berechnet |
| roof_orientation | ✅ | ❌ | ❌ | Berechnet |
| roof_overhang_m | ✅ | ❌ | ❌ | Sonnendach.ch |
| **SONNENDACH.CH (BFE API)** |||||
| sonnendach_available | ✅ | ❌ | ❌ | BFE API |
| roof_surfaces[] | ✅ | ❌ | ❌ | BFE API |
| roof_tilt_deg | ✅ | ❌ | ❌ | BFE API |
| roof_azimuth_deg | ✅ | ❌ | ❌ | BFE API |
| **ZONEN** |||||
| zones[] | ✅ | ❌ | ❌ | Auto / Claude |
| complexity | ✅ | ❌ | ❌ | Berechnet |
| **RESEARCH** |||||
| building_name | ✅ | ❌ | ❌ | known_buildings / Claude |
| building_type | ✅ | ❌ | ❌ | Claude Recherche |
| architectural_style | ✅ | ❌ | ❌ | Claude Recherche |
| **SUVA** |||||
| access_points[] | ✅ | ❌ | ❌ | Berechnet |
| suva_compliant | ✅ | ❌ | ❌ | Berechnet |
| **QUALITÄT** |||||
| overall_quality | ✅ | ❌ | ❌ | Berechnet |
| warnings[] | ✅ | ❌ | ❌ | Berechnet |
| data_sources[] | ✅ | ❌ | ❌ | Tracking |

### 12.2 Legende

| Symbol | Bedeutung |
|--------|-----------|
| ✅ | Vollständig vorhanden (korrekt berechnet) |
| ⚠️ | Vorhanden, aber ungenau (GELAENDEPUNKT-basiert, ~1-2m Abweichung bei Hang) |
| ❌ | Nicht vorhanden |

### 12.3 Was hat Stufe 2 (Nachbarn) MEHR als Stufe 3 (Rest)?

| Daten | Nachbarn (Stufe 2) | Rest (Stufe 3) |
|-------|:------------------:|:--------------:|
| Building-Layer (polygon, GESAMTHOEHE) | ✅ | ✅ |
| **Roof_solid-Layer** (3D-Geometrie) | ✅ | ❌ |
| **Wall-Layer** (3D-Geometrie) | ✅ | ❌ |
| **Terrain-Sampling** (swissALTI3D) | ✅ | ❌ |
| **Korrekte Höhen** (aus Roof + Terrain) | ✅ | ❌ |
| has_3d_layers = 1 | ✅ | ❌ |

### 12.4 Was hat das Objekt MEHR als Nachbarn?

Das **Objekt** (Projekt-Gebäude) erhält diese zusätzlichen Daten:

1. **GWR-Daten** - Geschosse, Fläche, Kategorie, Baujahr
2. **Fassaden-Details** - sides[] mit Länge, Richtung, Höhe pro Fassade
3. **Facade-Terrain** - facade_z_min/z_max PRO SEITE (nicht nur global)
4. **Sonnendach.ch** - Dachneigung, Azimut, Überstand, Dachflächen
5. **Zonen-Analyse** - Auto-Zonen oder Claude-Analyse bei komplexen Gebäuden
6. **Research** - Gebäudename, Typ, Architekturstil
7. **SUVA-Zugänge** - Berechnete Zugangspunkte (max 50m Abstand)
8. **Qualitätsbewertung** - overall_quality, warnings, data_sources

---

## 13. Schema-Änderungen

### 13.1 buildings_3d.duckdb - Neue Felder

```sql
-- Terrain-Sampling Felder (NEU)
ALTER TABLE buildings_3d ADD COLUMN terrain_z_min DOUBLE;
ALTER TABLE buildings_3d ADD COLUMN terrain_z_max DOUBLE;
ALTER TABLE buildings_3d ADD COLUMN terrain_slope_m DOUBLE;
ALTER TABLE buildings_3d ADD COLUMN terrain_sampled_at TIMESTAMP;

-- Index für Enrichment-Status
CREATE INDEX idx_buildings_3d_enrichment
ON buildings_3d(terrain_sampled_at, has_3d_layers);
```

### 13.2 buildings_3d - Vollständiges Schema (nach Migration)

```sql
CREATE TABLE buildings_3d (
    -- Identifikation
    egid INTEGER PRIMARY KEY,
    gebaeudeeinheit TEXT,

    -- Geometrie (aus swissBUILDINGS3D Building Layer)
    polygon JSON,                     -- [[e1,n1], [e2,n2], ...]
    center_e DOUBLE,
    center_n DOUBLE,
    area_m2 DOUBLE,
    perimeter_m DOUBLE,

    -- Höhen (aus swissBUILDINGS3D - GELAENDEPUNKT basiert)
    traufhoehe_m DOUBLE,              -- DACH_MIN - GELAENDEPUNKT
    firsthoehe_m DOUBLE,              -- DACH_MAX - GELAENDEPUNKT
    gebaeudehoehe_m DOUBLE,           -- GESAMTHOEHE

    -- Terrain-Sampling [NEU - aus swissALTI3D]
    terrain_z_min DOUBLE,             -- Min. Terrain-Höhe (m ü.M.)
    terrain_z_max DOUBLE,             -- Max. Terrain-Höhe (m ü.M.)
    terrain_slope_m DOUBLE,           -- Höhendifferenz
    terrain_sampled_at TIMESTAMP,     -- Wann wurde Terrain gesampelt?

    -- Metadaten
    tile_id TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'swissBUILDINGS3D_3.0',
    objektart TEXT,
    name_komplett TEXT,
    gebaeude_nutzung TEXT,

    -- Dach-Analyse
    roof_form TEXT,
    roof_form_confidence DOUBLE,
    roof_orientation TEXT,

    -- 3D-Layer Status
    has_3d_layers INTEGER DEFAULT 0
);
```

### 13.3 building_roofs

```sql
CREATE TABLE building_roofs (
    gebaeudeeinheit TEXT PRIMARY KEY,
    egid INTEGER,
    dach_min DOUBLE,                  -- Traufhöhe (m ü.M.)
    dach_max DOUBLE,                  -- Firsthöhe (m ü.M.)
    roof_form TEXT,
    roof_angle_deg DOUBLE,
    roof_orientation TEXT,
    z_levels TEXT,                    -- JSON: distinct Z-Werte
    geometry_wkb BLOB,
    has_full_geometry INTEGER DEFAULT 0,
    calculated_at TIMESTAMP,
    calculation_method TEXT
);

CREATE INDEX idx_roofs_egid ON building_roofs(egid);
```

### 13.4 building_walls

```sql
CREATE TABLE building_walls (
    gebaeudeeinheit TEXT PRIMARY KEY,
    egid INTEGER,
    z_min DOUBLE,                     -- Terrain-Niveau (m ü.M.)
    z_max DOUBLE,                     -- Dach-Niveau (m ü.M.)
    geometry_wkb BLOB,
    created_at TIMESTAMP
);

CREATE INDEX idx_walls_egid ON building_walls(egid);
```

### 13.5 geruestbau.db - projects

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    status TEXT DEFAULT 'draft',

    -- Gebäude-Referenz
    egid TEXT,                        -- Referenz zu buildings_3d

    -- Kunde
    client_name TEXT,
    client_contact TEXT,
    deadline TEXT,
    description TEXT,

    -- Konfiguration (JSON)
    building_data TEXT,               -- Snapshot bei Erstellung
    scaffold_config TEXT,             -- Gerüst-Einstellungen

    -- Meta
    created_at TEXT,
    updated_at TEXT
);
```

---

## 14. API-Änderungen

### 14.1 GET /api/v1/smart-building/data

**Neuer Parameter:**

```
GET /api/v1/smart-building/data
    ?address=Knospenweg%204,%20Bern
    &include_terrain=true
    &neighbor_enrichment_radius_m=100    ← NEU
```

**Reihenfolge der Aufrufe:**
1. `collect_all_data()` für das Objekt
2. `collect_data_for_neighbors()` für Nachbarn im Radius
3. `prefetch_remaining_tile_buildings()` für Rest im Tile

### 14.2 GET /api/v1/geruestbau/building/{egid}/neighbors

**Erweiterte Response:**

```json
{
  "target_egid": "1243790",
  "neighbors": [
    {
      "egid": "1243788",
      "polygon": [[...]],
      "distance_m": 8.5,
      "direction": "NW",
      "traufhoehe_m": 5.54,
      "firsthoehe_m": 8.21,

      "terrain_z_min": 555.8,
      "terrain_z_max": 557.6,
      "terrain_slope_m": 1.8,
      "terrain_enriched": true,

      "has_3d_layers": true
    }
  ],
  "enrichment_status": {
    "total": 53,
    "enriched": 53,
    "pending": 0
  }
}
```

---

## 15. Geschätzte Performance

### 15.1 Stufe 1: collect_all_data (Objekt)

| Schritt | Zeit |
|---------|------|
| Geocoding | ~100ms |
| GWR | ~50ms |
| 3D-Daten (Cache) | ~50ms |
| 3D-Daten (Download) | ~5-10s |
| Terrain | ~200ms |
| Sonnendach | ~100ms |
| Zonen (Auto) | ~10ms |
| Zonen (Claude) | ~500ms |
| Research | ~100ms |
| **Total (Cache)** | **~600ms** |
| **Total (Download)** | **~6-11s** |

### 15.2 Stufe 2: collect_data_for_neighbors (53 Nachbarn)

| Schritt | Zeit pro Gebäude | 53 Nachbarn |
|---------|------------------|-------------|
| 3D-Layer (aus GDB) | ~50ms | ~2.5s |
| Terrain-Sampling | ~200ms | ~10.5s |
| **Total (sequentiell)** | ~250ms | **~13s** |
| **Total (5 parallel)** | - | **~3-4s** |

### 15.3 Stufe 3: prefetch_remaining (Rest im Tile)

| Schritt | Zeit |
|---------|------|
| GDB-Parsing (~200 Gebäude) | ~2s |
| DB-Speicherung | ~1s |
| **Total** | **~3s** |

### 15.4 Gesamt-Zeit (typisches Szenario)

| Szenario | Stufe 1 | Stufe 2 | Stufe 3 | Total |
|----------|---------|---------|---------|-------|
| Cache-Hit | 0.6s | 3s | 0s | **~4s** |
| Tile-Download | 8s | 3s | 3s | **~14s** |

---

## 16. Implementierungs-Checkliste

### 16.1 Schema-Migration
- [ ] Neue Felder in `buildings_3d` (terrain_z_min, terrain_z_max, terrain_slope_m, terrain_sampled_at)
- [ ] Index `idx_buildings_3d_enrichment`
- [ ] Migration-Script erstellen

### 16.2 STUFE 2: prefetch_neighbors() (NEUE Implementierung)
- [ ] Signatur: `prefetch_neighbors(e, n, radius_m=100)`
- [ ] Zwei parallele Jobs: 5m (hardcoded für blocked_facades) + radius_m (Parameter)
- [ ] Parquet-Pipeline:
    - [ ] GDB → Stream (Fiona, Radius-Filter)
    - [ ] Alle 3 Layer parallel parsen (Building, Roof_solid, Wall)
    - [ ] → Parquet-Dateien
    - [ ] Parquet → DuckDB Bulk-Load
- [ ] Terrain-Sampling NACH DB-Write:
    - [ ] 8 Polygon-Ecken pro Gebäude
    - [ ] swissALTI3D API aufrufen
    - [ ] UPDATE buildings_3d SET terrain_z_min, terrain_z_max, terrain_slope_m
- [ ] Korrekte Höhen berechnen:
    - [ ] traufhoehe = dach_min - terrain_z_min
    - [ ] firsthoehe = dach_max - terrain_z_min
    - [ ] UPDATE buildings_3d SET traufhoehe_m, firsthoehe_m
- [ ] OUTPUT: enriched_egids[] für Stufe 3

### 16.3 STUFE 3: prefetch_tile anpassen
- [ ] Parameter: `exclude_egids` (von Stufe 2)
- [ ] Filter: egid NOT IN exclude_egids beim Streaming
- [ ] NUR Building-Layer parsen (keine 3D-Layer)
- [ ] Parquet-Pipeline (bereits vorhanden, anpassen)

### 16.4 Scheduling (swissbuildings3d_fetcher.py)
- [ ] `prefetch_neighbors(e, n, radius_m=100)` - NEUE Implementierung
- [ ] Nach User-Antwort: schedule Stufe 2 (zwei parallele Jobs)
- [ ] Nach Stufe 2: schedule Stufe 3 mit enriched_egids

### 16.5 Obsolete Funktionen entfernen
- [ ] `load_neighbors_and_save()` → durch Stufe 2 ersetzt
- [ ] `find_immediate_neighbors()` → durch Stufe 2 ersetzt

### 16.6 API-Parameter
- [ ] `neighbor_enrichment_radius_m` in `/smart-building/data`
- [ ] Default: 100m

### 16.7 neighbors_service.py
- [ ] `terrain_z_min`, `terrain_z_max`, `terrain_slope_m` in Response
- [ ] `has_3d_layers` Flag
- [ ] `enrichment_status` (optional)

### 16.8 Tests
- [ ] Unit-Tests für `collect_data_for_neighbors`
- [ ] Integration-Tests für 3-Stufen-Flow
- [ ] Performance-Tests (Ketten-Verarbeitung vs. Gesamt)

---

## 17. Zusammenfassung

### 17.1 Zwei-Stufen Architektur (User-Flow)

| Stufe | Funktion | Daten | Timing |
|-------|----------|-------|--------|
| 1 | `collect_all_data` | Objekt: ALLE Daten | ✅ User erhält Antwort |
| 2 | `prefetch_neighbors(e, n, radius_m)` | Ganzes Tile (enriched + basic) | 🔄 Scheduled (Background) |

**Separat (Batch-Import):**

| Funktion | Verwendung | Daten |
|----------|------------|-------|
| `prefetch_tile(tile_id)` | scripts/import_tiles.py | NUR Building-Layer |

### 17.2 Ablauf

```
User-Request (Adresse)
    │
    ▼
STUFE 1: collect_all_data()
    │   └─ GWR, Polygon, Höhen, Terrain, Zonen, etc.
    │
    ├──────────────────────────────────────────────────────────────┐
    ▼                                                              │
✅ USER ERHÄLT ANTWORT                                             │
                                                                   │
    ▼ schedule()                                                   │
STUFE 2: prefetch_neighbors(e, n, radius_m=100)                   │
    │   └─ Ein GDB-Durchlauf: alle Gebäude parsen                 │
    │   └─ ENRICHED (≤100m): Building + Roof + Wall + Terrain    │
    │   └─ BASIC (>100m): NUR Building Layer                      │
    │   └─ Parquet-Pipeline: GDB → Parquet → DuckDB               │
    │   └─ Cleanup: Parquets + GDB löschen                        │
    │                                                              │
    └─ ✅ GANZES TILE GECACHT                                      │
```

### 17.3 Vorteile dieser Architektur

1. **Schnelle Antwort** - User wartet nur auf Stufe 1 (Objekt-Daten)
2. **Volle 3D-Daten** - Nachbarn (≤100m) bekommen Roof + Wall + Terrain
3. **Sortiert** - 5m-Nachbarn zuerst → blocked_facades sofort verfügbar
4. **Effizient** - GDB nur 1× durchlaufen (nicht 2× wie bei parallelen Jobs)
5. **Ganzes Tile** - Spätere Anfragen im Tile sind sofort aus Cache verfügbar
6. **Cleanup** - Parquets + GDB werden nach Import gelöscht (Speicher sparen)

### 17.4 Empfohlene Werte

| Use Case | `neighbor_enrichment_radius_m` |
|----------|--------------------------------|
| Schnelle Vorschau | 0 |
| Standard-Projekt | 50 |
| Komplexes Projekt | 100 (STANDARD) |
| Grossprojekt | 150 |
