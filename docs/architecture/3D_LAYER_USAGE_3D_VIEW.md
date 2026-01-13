# 3D-Layer Verwendung: 3D-View & Nachbarn

> **Stand 13.01.2026 23:50**
> **Status:** ✅ IMPLEMENTIERT

## Übersicht

Dieses Dokument beschreibt, wie die 3D-Layer-Daten für die 3D-Visualisierung und Nachbar-Analyse verwendet werden.

**Kernkonzepte:**
1. **Nachbargebäude** - Gebäude im Umkreis für Kontext-Darstellung
2. **Blockierte Fassaden** - Fassaden wo kein Gerüst aufgestellt werden kann
3. **3D-View** - Isometrische Darstellung mit Nachbarn und Blockerungen

## Datenfluss: 3D-Daten → 3D-View

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DATENFLUSS: 3D-VIEW MIT NACHBARN                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    1. BUILDING_3D.DUCKDB                                 │  │
│  ├──────────────────────────────────────────────────────────────────────────┤  │
│  │  buildings_3d Tabelle:                                                   │  │
│  │    egid, polygon (JSON), center_e, center_n                             │  │
│  │    traufhoehe_m, firsthoehe_m, gebaeudehoehe_m                          │  │
│  │                                                                          │  │
│  │  → Enthält ALLE Gebäude aus heruntergeladenen Tiles (via tile_prefetch) │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│                     ┌────────────────┴────────────────┐                         │
│                     ▼                                  ▼                         │
│  ┌──────────────────────────────┐    ┌──────────────────────────────────────┐  │
│  │ NeighborsService             │    │ BlockedFacadesService                │  │
│  │ (neighbors_service.py)       │    │ (blocked_facades_service.py)         │  │
│  ├──────────────────────────────┤    ├──────────────────────────────────────┤  │
│  │                              │    │                                      │  │
│  │ get_neighbors(egid, radius)  │    │ calculate_blocked_facades(egid)      │  │
│  │                              │    │                                      │  │
│  │ 1. Zielgebäude laden         │    │ 1. Zielgebäude laden                 │  │
│  │ 2. Bounding-Box Query        │    │ 2. Nachbarn im Radius suchen         │  │
│  │ 3. Polygon-Distanz berechnen │    │ 3. Pro Fassade: min. Distanz prüfen  │  │
│  │ 4. Richtung berechnen        │    │ 4. Blockiert wenn < threshold_m      │  │
│  │                              │    │                                      │  │
│  │ Returns: NeighborsResult     │    │ Returns: BlockedFacadesResult        │  │
│  │   - neighbors[]              │    │   - blocked_indices[]                │  │
│  │   - distance_m               │    │   - blockers[] per facade            │  │
│  │   - direction (N,E,S,W...)   │    │   - free_facades count               │  │
│  └──────────────────────────────┘    └──────────────────────────────────────┘  │
│                     │                                  │                         │
│                     └────────────────┬─────────────────┘                         │
│                                      ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    2. API ENDPOINTS (geruestbau.py)                      │  │
│  ├──────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                          │  │
│  │  GET /api/v1/geruestbau/building/{egid}/neighbors                        │  │
│  │      ?radius_m=10                                                        │  │
│  │      &include_polygons=true                                              │  │
│  │                                                                          │  │
│  │  GET /api/v1/geruestbau/building/{egid}/blocked-facades                  │  │
│  │      ?threshold_m=2.0                                                    │  │
│  │      &exclude_egids=123,456 (Projekt-Gebäude)                            │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                           │
│                                      ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    3. FRONTEND (ConfiguratorPage.tsx)                    │  │
│  ├──────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                          │  │
│  │  State:                                                                  │  │
│  │    neighborsRadius: 0 | 20 | 50 | 100 (Slider)                          │  │
│  │    neighbors: NeighborBuilding[]                                         │  │
│  │    blockedSides: string[]                                                │  │
│  │    blockedFacadesData: Map<egid, BlockedFacadesResult>                   │  │
│  │                                                                          │  │
│  │  Data Loading:                                                           │  │
│  │    1. SSE Stream (Projekt mit mehreren Gebäuden)                        │  │
│  │    2. REST API Fallback (einzelne Adress-Suche)                         │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                           │
│                                      ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    4. 3D-VIEW (ScaffoldScene.tsx)                        │  │
│  ├──────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                          │  │
│  │  Props:                                                                  │  │
│  │    neighbors: NeighborBuilding[]                                         │  │
│  │    blockedSides: string[]                                                │  │
│  │    additionalBuildings: MultiBuildingData[] (Projekt-Gebäude)            │  │
│  │                                                                          │  │
│  │  Rendering:                                                              │  │
│  │    - Hauptgebäude (Farben nach Himmelsrichtung)                         │  │
│  │    - Nachbar-Gebäude (grau, 50% Opacity)                                │  │
│  │    - Blockierte Fassaden (rot markiert)                                 │  │
│  │    - Projekt-Gebäude (leichte Einfärbung)                               │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Komponenten-Übersicht

### Backend Services

| Datei | Funktion | Datenbank |
|-------|----------|-----------|
| `neighbors_service.py` | Nachbarn im Radius finden | building_3d.duckdb |
| `blocked_facades_service.py` | Blockierte Fassaden berechnen | building_3d.duckdb |
| `geruestbau.py` (Router) | API Endpoints | - |

### Frontend Komponenten

| Datei | Funktion |
|-------|----------|
| `ConfiguratorPage.tsx` | State-Management, API-Calls |
| `ScaffoldScene.tsx` | Three.js 3D-Rendering |
| `ThreeDPanel.tsx` | UI-Container für 3D-View |
| `geruestbau.ts` (API) | `getNeighbors()`, `getBlockedFacades()` |

## NeighborsService Details

### Algorithmus

```
1. Zielgebäude aus building_3d.duckdb laden
   → egid, polygon, center_e, center_n

2. Bounding-Box Query (schnell, O(log n))
   → SELECT * FROM buildings_3d
     WHERE center_e BETWEEN (target_e - radius) AND (target_e + radius)
       AND center_n BETWEEN (target_n - radius) AND (target_n + radius)

3. Polygon-Distanz berechnen
   → Für jeden Kandidaten: minimale Distanz zwischen Polygonen
   → Punkt-zu-Segment Algorithmus

4. Filtern nach radius_m
   → Nur Gebäude mit distance_m <= radius_m

5. Richtung berechnen
   → atan2(delta_n, delta_e) → N, NE, E, SE, S, SW, W, NW
```

### Performance

| Operation | Zeit | Grund |
|-----------|------|-------|
| DB-Query (Bounding-Box) | ~1ms | Spatial Index |
| Polygon-Distanz (pro Nachbar) | ~0.1ms | O(n²) Punkte |
| Gesamt (10 Nachbarn) | ~2-5ms | |

### Datenstruktur

```typescript
interface NeighborBuilding {
  egid: string
  polygon?: [number, number][]  // Optional (include_polygons)
  distance_m: number            // Minimale Distanz zum Zielgebäude
  direction: string             // N, NE, E, SE, S, SW, W, NW
  center_e?: number
  center_n?: number
  traufhoehe_m?: number
  firsthoehe_m?: number
}

interface NeighborsResponse {
  target_egid: string
  target_polygon: [number, number][]
  neighbors: NeighborBuilding[]
  blocked_sides: string[]       // Legacy: Himmelsrichtungen
  query_time_ms: number
}
```

## BlockedFacadesService Details

### Konzept

Eine Fassade gilt als **blockiert** wenn:
- Ein externes Gebäude (nicht im Projekt) näher als `threshold_m` ist
- Kein Gerüst aufgestellt werden kann

**WICHTIG für Multi-Building-Projekte:**
- Projekt-Gebäude (in `exclude_egids`) blockieren sich NICHT gegenseitig
- Nur EXTERNE Gebäude werden als Blocker berücksichtigt

### Algorithmus

```
1. Zielgebäude laden (Polygon mit n Kanten = n Fassaden)

2. Fassaden extrahieren
   → Jede Kante des Polygons = 1 Fassade (0-indexed)

3. Nachbarn im erweiterten Radius suchen
   → radius = threshold_m + 20m (Puffer für grosse Gebäude)

4. Für jede Fassade:
   → Minimale Distanz zu jedem Nachbar-Polygon berechnen
   → Wenn distance < threshold_m → Fassade blockiert
   → Blocker-Info speichern (EGID, Distanz, Richtung)

5. Ergebnis: Liste der blockierten Fassaden-Indizes
```

### Default-Schwellenwert

```python
DEFAULT_THRESHOLD_M = 2.0  # Gerüstbreite (0.7m) + Arbeitsraum (1.3m)
```

### Datenstruktur

```typescript
interface BlockedFacadesResponse {
  egid: string
  blocked_indices: number[]      // [0, 2, 5] = Fassaden 0, 2, 5 blockiert
  total_facades: number          // Gesamtzahl Fassaden
  free_facades: number           // Anzahl freie Fassaden
  blocked_facades: BlockedFacadeInfo[]
  query_time_ms: number
}

interface BlockedFacadeInfo {
  facade_index: number
  egid: string | null            // Blockierendes Gebäude
  distance_m: number
  direction: string | null
}
```

## Frontend Integration

### Neighbors Slider (ConfiguratorPage)

```
┌─────────────────────────────────────────┐
│  Nachbarn:  [Aus] [20m] [50m] [100m]   │
└─────────────────────────────────────────┘

- Aus (0): Keine Nachbarn anzeigen
- 20m: Direkte Nachbarn (Gerüstplanung)
- 50m: Nahe Umgebung
- 100m: Kontext (Orthofoto-Ersatz)
```

### Data Loading Strategie

```typescript
// 1. SSE Stream (für Projekte)
useProjectContextStream({
  onNeighbors: (data) => setNeighbors(data),
  onBlockedFacades: (data) => setBlockedFacadesData(data)
})

// 2. REST API Fallback (für Adress-Suche)
useEffect(() => {
  if (neighborsRadius > 0) {
    geruestbauApi.getNeighbors(egid, neighborsRadius)
      .then(response => {
        setNeighbors(response.neighbors)
        setBlockedSides(response.blocked_sides)
      })
  }
}, [egid, neighborsRadius])
```

### 3D-Scene Rendering

```typescript
// ScaffoldScene.tsx
function renderNeighbors(neighbors: NeighborBuilding[]) {
  return neighbors.map(neighbor => (
    <mesh key={neighbor.egid}>
      <extrudeGeometry args={[shape, { depth: neighbor.traufhoehe_m }]} />
      <meshStandardMaterial
        color="#888888"
        opacity={0.5}
        transparent
      />
    </mesh>
  ))
}

function renderBlockedFacades(blockedIndices: number[]) {
  return blockedIndices.map(idx => (
    <mesh key={idx}>
      {/* Rote Markierung auf blockierter Fassade */}
      <planeGeometry args={[facadeLength, facadeHeight]} />
      <meshBasicMaterial color="#ff0000" opacity={0.3} transparent />
    </mesh>
  ))
}
```

## API Endpoints

### GET /api/v1/geruestbau/building/{egid}/neighbors

```bash
curl "http://localhost:8000/api/v1/geruestbau/building/1243787/neighbors?radius_m=20&include_polygons=true"
```

**Response:**
```json
{
  "target_egid": "1243787",
  "target_polygon": [[2596299, 1199805], ...],
  "neighbors": [
    {
      "egid": "1243789",
      "distance_m": 5.2,
      "direction": "N",
      "polygon": [[2596300, 1199820], ...],
      "traufhoehe_m": 6.5
    }
  ],
  "blocked_sides": ["N"],
  "query_time_ms": 3.5
}
```

### GET /api/v1/geruestbau/building/{egid}/blocked-facades

```bash
curl "http://localhost:8000/api/v1/geruestbau/building/1243787/blocked-facades?threshold_m=2.0&exclude_egids=1243789,1243791"
```

**Response:**
```json
{
  "egid": "1243787",
  "blocked_indices": [0, 2],
  "total_facades": 4,
  "free_facades": 2,
  "blocked_facades": [
    {
      "facade_index": 0,
      "egid": "1243795",
      "distance_m": 1.8,
      "direction": "N"
    }
  ],
  "query_time_ms": 5.2
}
```

## Datenbank-Schema

### buildings_3d (DuckDB)

```sql
CREATE TABLE buildings_3d (
    egid INTEGER PRIMARY KEY,
    polygon JSON,           -- [[e1,n1], [e2,n2], ...]
    center_e DOUBLE,        -- Zentrum E-Koordinate (LV95)
    center_n DOUBLE,        -- Zentrum N-Koordinate (LV95)
    traufhoehe_m DOUBLE,    -- Traufhöhe in Metern
    firsthoehe_m DOUBLE,    -- Firsthöhe in Metern
    gebaeudehoehe_m DOUBLE, -- Gebäudehöhe (DACH_MAX - GELAENDEPUNKT)
    tile_id VARCHAR,        -- Quell-Tile ID
    created_at TIMESTAMP DEFAULT current_timestamp
);

-- Spatial Index für schnelle Bounding-Box Queries
CREATE INDEX idx_buildings_3d_coords ON buildings_3d(center_e, center_n);
```

## Test-Beispiele

### Knospenweg, Bern (Reihenhäuser)

```
Gebäude: Knospenweg 2 (EGID 1243788)
Nachbarn im 10m Radius:
  - Knospenweg 4 (EGID 1243790): 2.5m N
  - Knospenweg 6 (EGID 1243792): 4.8m N
  - Fremdes Gebäude (EGID 9999): 8.2m W

Blockierte Fassaden:
  - Fassade 0 (Nord): blockiert durch 1243790 (2.5m)
  - Fassade 2 (Süd): frei
  - Fassade 1 (Ost): frei
  - Fassade 3 (West): blockiert durch 9999 (1.8m < 2.0m threshold)
```

### Multi-Building Projekt

```
Projekt: Knospenweg 2-6 (EGIDs: 1243788, 1243790, 1243792)

exclude_egids für Blocked-Facades:
  → [1243788, 1243790, 1243792]
  → Diese blockieren sich NICHT gegenseitig

Nur externes Gebäude 9999 blockiert Fassaden.
```

## Performance-Optimierungen

### 1. Bounding-Box statt Radius-Suche

```sql
-- SCHNELL: Rechteckige Bounding-Box (Index-Nutzung)
WHERE center_e BETWEEN ? AND ? AND center_n BETWEEN ? AND ?

-- LANGSAM: Radius-Berechnung in SQL
WHERE SQRT(POW(center_e - ?, 2) + POW(center_n - ?, 2)) < ?
```

### 2. Polygon-Distanz nur für Kandidaten

```
1. Bounding-Box Query → ~100 Kandidaten
2. Polygon-Distanz nur für Kandidaten → ~10 finale Nachbarn
```

### 3. include_polygons=false für schnelle Übersicht

```
Mit Polygonen:    ~5ms (JSON parsing)
Ohne Polygone:    ~2ms (nur Koordinaten)
```

## Implementierte Dateien

| Datei | Zeilen | Status |
|-------|--------|--------|
| `backend/app/services/neighbors_service.py` | 347 | ✅ |
| `backend/app/services/blocked_facades_service.py` | 462 | ✅ |
| `backend/app/routers/geruestbau.py` | Endpoints | ✅ |
| `geruestbau-app/src/api/geruestbau.ts` | API-Funktionen | ✅ |
| `geruestbau-app/src/pages/ConfiguratorPage.tsx` | State + Effects | ✅ |
| `geruestbau-app/src/features/.../ScaffoldScene.tsx` | 3D-Rendering | ✅ |

---

## Analyse: Neue Möglichkeiten mit 3D-Layer-Daten (13.01.2026)

### Verfügbare Datenquellen

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VERFÜGBARE 3D-DATEN                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │ WALL-LAYER      │  │ ROOF-LAYER      │  │ TERRAIN (swissALTI3D)       │ │
│  │ (building_walls)│  │ (building_roofs)│  │                             │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────────────────┤ │
│  │ z_min pro Wand  │  │ dach_min/max    │  │ facade_z_min pro Richtung   │ │
│  │ z_max pro Wand  │  │ Dach-Geometrie  │  │ slope_m (Gefälle)           │ │
│  │ Azimut          │  │ Roof_solid 3D   │  │ Höhe an jedem Punkt         │ │
│  │ Wand-Polygon    │  │ Dachform        │  │ Hanglage-Erkennung          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │ NACHBARN        │  │ BLOCKED FACADES │  │ POLYGON (vereinfacht)       │ │
│  │ (neighbors_svc) │  │ (blocked_svc)   │  │ (Douglas-Peucker)           │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────────────────┤ │
│  │ Distanz (m)     │  │ Index blockiert │  │ Fassaden-Längen             │ │
│  │ Richtung        │  │ Blocker-EGID    │  │ Himmelsrichtung             │ │
│  │ Polygon + Höhen │  │ Min-Distanz     │  │ Start/End Koordinaten       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Bereits Implementiert ✅

| Feature | Datenquelle | Datei |
|---------|-------------|-------|
| Fassaden-Höhen pro Richtung | Terrain-Sampling | `service.py` |
| Hanglage-Erkennung | facade_z_min Differenz | `useScaffoldConfig.ts` |
| Stellspindel-Berechnung | terrain_diff_m | `layher_catalog.py` |
| Ausnivellierung in Materialliste | calculate_leveling_materials() | `layher_catalog.py` |
| 2D-Editor Visualisierung | terrain_diff_m | `ScaffoldGrid.tsx` |
| Nachbarn in 3D-View | neighbors_service | `ScaffoldScene.tsx` |
| Blockierte Fassaden | blocked_facades_service | `ConfiguratorPage.tsx` |

### Feature-Roadmap

#### P1: Wall-Layer Fassaden-Höhen (HÖCHSTE PRIORITÄT)

**Problem:** Aktuell wird Terrain-Sampling (swissALTI3D an Polygon-Ecken) verwendet.
Das ist eine Approximation mit ±0.5m Genauigkeit.

**Lösung:** Wall-Layer direkt nutzen (building_walls.z_min/z_max).
Exakte Höhe PRO WAND-SEGMENT mit ±0.1m Genauigkeit aus Laser-Scan.

```python
# Aktuell (Terrain-Sampling):
z_min["N"] = terrain_height_at_north_corner  # Approximation

# Neu (Wall-Layer):
z_min["N"] = building_walls.z_min WHERE azimuth ~ 0°  # Exakt
z_max["N"] = building_walls.z_max WHERE azimuth ~ 0°
```

**Vorteil:** Bei komplexen Gebäuden (L-Form, Staffelung) liefert der Wall-Layer
die ECHTE Wandhöhe, nicht interpolierte Terrain-Höhe.

**Dateien:**
- `backend/app/services/smart_building/service.py` - `_get_facade_heights()`
- `backend/app/services/smart_building/wall_facade_matcher.py` - Wall-zu-Fassade Mapping

**Aufwand:** 1-2h

---

#### P2a: Automatische Dachform-Erkennung

**Konzept:** Roof-Layer Geometrie analysieren um Dachform zu erkennen.

```
Erkennungs-Logik:
  - Satteldach: 2 Dachflächen, First in Mitte
  - Walmdach: 4 Dachflächen, alle zur Mitte geneigt
  - Pultdach: 1 Dachfläche, Neigung einseitig
  - Flachdach: dach_max - dach_min < 1m
  - Mansarddach: Gebrochene Dachflächen (>60°)
```

**Nutzen:**
- Dachgerüst-Planung (Dachschutz vs. Fassadengerüst)
- First-Position für Arbeitsbühnen
- Dachneigung für Sicherheitsausrüstung (PSA)
- Automatische Empfehlung: "Dachfanggerüst empfohlen (Neigung >45°)"

**Dateien:**
- `backend/app/services/roof_analyzer.py` (NEU)
- `backend/app/services/smart_building/models.py` - RoofAnalysis Dataclass

**Aufwand:** 2-3h

---

#### P2b: Exakte 3D-Dachform im Viewer

**Problem:** Aktuell wird ein einfaches Satteldach heuristisch gerendert.

**Lösung:** Roof_solid Geometrie direkt aus building_roofs laden und rendern.

```typescript
// Aktuell:
createRoofFromPolygon(polygon, traufhoehe, firsthoehe)  // Heuristik

// Neu:
createRoofFromGeometry(roof_solid_geometry)  // Echte 3D-Form
```

**Vorteile:**
- Gauben, Kamine, Dachfenster sichtbar
- Echte Dachüberstände
- Korrekte Dachform für Export

**Dateien:**
- `geruestbau-app/src/features/.../ScaffoldScene.tsx` - `createRoofMesh()`
- `backend/app/services/roof_3d_service.py` - `get_roof_geometry()`

**Aufwand:** 3-4h

---

#### P3a: Intelligente Zugangs-Vorschläge

**Konzept:** Kombiniere alle Datenquellen um optimalen Gerüst-Zugang zu empfehlen.

```
Analyse-Faktoren:
  ┌─────────────────────────────────────────────────────────┐
  │  Blockierte Fassaden  → Wo KEIN Gerüst möglich         │
  │  Nachbar-Distanzen    → Wo es ENG ist                  │
  │  Terrain-Höhen        → Wo es STEIL ist                │
  │  Strassenanbindung    → Wo ZUFAHRT für Material        │
  │  Gebäude-Eingänge     → Wo Durchgang bleiben muss      │
  └─────────────────────────────────────────────────────────┘
                              │
                              ▼
  "Empfohlener Zugang: Westseite (frei, eben, Strassennähe)"
```

**UI:**
- Grüne Markierung: Empfohlener Zugang
- Gelbe Markierung: Alternativ-Zugänge
- Rote Markierung: Nicht empfohlen (blockiert, steil, eng)

**Dateien:**
- `backend/app/services/access_analyzer.py` (NEU)
- `geruestbau-app/src/features/.../AccessSuggestions.tsx` (NEU)

**Aufwand:** 2-3h

---

#### P3b: Gefährdungszonen-Analyse

**Konzept:** Automatische Erkennung von Bereichen die besondere Massnahmen erfordern.

```
Gefährdungszonen:
  ┌───────────────────────────────────────────────────────────────┐
  │  Öffentlicher Gehweg < 2m  → Schutzgerüst/Schutzdach nötig   │
  │  Strasse < 5m              → Absperrung, Signalisation       │
  │  Nachbar-Fenster < 3m      → Sichtschutz/Staubschutz         │
  │  Einfahrt < 3m             → Durchfahrtshöhe beachten        │
  │  Spielplatz in Nähe        → Erhöhte Sicherheit              │
  └───────────────────────────────────────────────────────────────┘
```

**Output:** Automatische SUVA-Checkliste mit erkannten Gefährdungen.

**Dateien:**
- `backend/app/services/hazard_analyzer.py` (NEU)
- `backend/app/models/suva_checklist.py` (NEU)

**Aufwand:** 4-6h

---

#### P4: Weitere Ideen (Backlog)

| Feature | Beschreibung | Aufwand |
|---------|--------------|---------|
| Material-Transport-Optimierung | Kürzester Weg LKW → Gerüst, Kranposition | 6-8h |
| Schatten-Analyse | Nordseite = Moos, Südseite = schnell trocknend | 2-3h |
| Wetter-Exposition | Windrichtung, offene Seiten markieren | 2-3h |
| Kollisions-Erkennung | Gerüst vs. Balkon, Vordach, Leitungen | 4-6h |
| Export für LayPLAN | IFC/DXF mit 3D-Gerüstdaten | 8-12h |

### Priorisierte Umsetzung

| Phase | Features | Status |
|-------|----------|--------|
| **Phase 1** | P1: Wall-Layer Höhen | 🔄 In Arbeit |
| **Phase 2** | P2a: Dachform-Erkennung, P2b: 3D-Dachform | ⏳ Geplant |
| **Phase 3** | P3a: Zugangs-Vorschläge, P3b: Gefährdungszonen | ⏳ Geplant |
| **Phase 4** | Transport, Schatten, Export | 📋 Backlog |
