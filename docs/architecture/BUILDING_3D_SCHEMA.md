# Building 3D Schema - Konzept

> **Version:** 2.4 (Stand 14.01.2026 00:15)
> **Status:** DuckDB-Migration abgeschlossen ✅
> **Basis:** SWISSBUILDINGS3D_ANALYSE.md + BATCH_IMPORT.md

## Aktueller Projektstand

### ✅ Abgeschlossen (13.01.2026)

| Task | Beschreibung |
|------|--------------|
| DuckDB-Migration | `building_3d.db` → `building_3d.duckdb` |
| Feature-Flag | DuckDB ist Default (SQLite mit `USE_DUCKDB=false`) |
| Dual-Mode Service | `building_3d_service.py` unterstützt beide Engines |
| INSERT OR REPLACE | Funktioniert für SQLite UND DuckDB (≥0.8) |
| Schema erweitert | Neue Felder: objektart, name_komplett, roof_form, etc. |

### 🔴 Offene Punkte

| Task | Priorität | Beschreibung |
|------|-----------|--------------|
| **Index-Deferred ALLE** | P1 | `drop_indexes()` nur 2 von 7! Siehe BATCH_IMPORT.md C.8 |
| 3D-Layer Integration | P2 | Floor/Wall/Roof Layer aus swissBUILDINGS3D extrahieren |
| Parquet-Pipeline | P3 | Optional für Batch-Import (aktuell nicht nötig) |
| Railway Deployment | P1 | DuckDB auf Railway.app testen |
| Legacy-Code entfernen | P3 | SQLite-spezifischen Code nach Testphase entfernen |

> **⚠️ Index-Inkonsistenz (14.01.2026):**
> - Schema (`building_3d_schema.py`): **7 Indexes** definiert
> - Service (`building_3d_service.py`): `drop_indexes()` und `create_indexes()` behandeln nur **2 Indexes**
> - **Impact:** Bei Batch-Import werden 5 Indexes nicht gedroppt → langsamerer Import
> - **Fix:** Siehe BATCH_IMPORT.md Anhang C Task C.8

### 📋 Geplant

| Task | Beschreibung |
|------|--------------|
| 3D-Viewer Integration | API-Endpunkte für Floor/Wall/Roof Geometrien |
| Dachwinkel aus 3D | `calculate_roof_angle_from_3d()` implementieren |
| Spatial Index | DuckDB Spatial Extension evaluieren |

---

## Executive Summary

swissBUILDINGS3D 3.0 liefert **komplette 3D-Modelle** mit 5 Layern.
Wir nutzen aktuell nur einen Bruchteil der Daten. Dieses Konzept beschreibt
ein neues DB-Schema mit DuckDB für die vollständige 3D-Nutzung.

---

## Wir haben ein komplettes 3D-Modell!

### Beispiel: Berner Münster (EGID 1230337)

```
AKTUELL (vereinfacht):                    MIT ALLEN LAYERN (exakt):

    ┌───────┐                                    ▲
    │       │  ← 1 Polygon               104m    │    TURM
    │       │    (2D Grundriss)                  │    (Building_solid)
    │       │    + Höhenattribute               ┌┴┐
    │       │                                   │█│
    └───────┘                                   │█│
                                          71m ──┼─┼── Wall Layer
                                                │ │   4'360 Punkte!
                                               ┌┴─┴┐
                                               │███│
                                               │███│ ← KIRCHENSCHIFF
                                               │███│
                                         ──────┴───┴────── Floor Layer
                                          87.7m × 41.1m    1'204 Punkte!
                                          (mit 15.3m Terrain-Variation)
```

### Verfügbare Daten pro Layer

| Layer | Punkte | X × Y | Z-Range | Verwendung |
|-------|--------|-------|---------|------------|
| **Floor** | 1'204 | 87.7m × 41.1m | 15.3m Terrain! | Exakter Grundriss |
| Wall** | 4'360 | 87.7m × 41.1m | 71.2m | Alle Fassaden 3D |
| **Roof** | 24 | 10.4m × 10.5m | 5.5m | Dach-Umriss |
| **Roof_solid** | 112 | 10.4m × 10.5m | 5.7m | 3D Dachkörper |
| **Building_solid** | 8'072 | 87.7m × 41.1m | 104.2m | Komplettes Modell |

---

## Warum DuckDB?

### Problem mit SQLite

```
SQLite Bottleneck bei 3D-Daten:

  GDB Tile (500MB)
       │
       ▼ Parse (parallel möglich)
  ┌─────────────────────────────────────────────┐
  │ Worker 1 │ Worker 2 │ Worker 3 │ Worker 4  │
  └─────┬────┴────┬─────┴────┬─────┴─────┬─────┘
        │         │          │           │
        └────────►├◄─────────┴───────────┘
                  │
                  ▼ FLASCHENHALS!
           ┌──────────────┐
           │   SQLite     │ ← Single Writer Lock
           │  (1 Thread)  │
           └──────────────┘
```

### Lösung: DuckDB + Parquet Pipeline

```
DuckDB 3D-Import Pipeline:

  GDB Tile                GDB Tile                GDB Tile
       │                       │                       │
       ▼                       ▼                       ▼
  ┌─────────┐            ┌─────────┐            ┌─────────┐
  │ Parse   │            │ Parse   │            │ Parse   │
  │ Floor   │            │ Floor   │            │ Floor   │
  │ Wall    │            │ Wall    │            │ Wall    │
  │ Roof    │            │ Roof    │            │ Roof    │
  └────┬────┘            └────┬────┘            └────┬────┘
       │                      │                      │
       ▼                      ▼                      ▼
  ┌─────────┐            ┌─────────┐            ┌─────────┐
  │.parquet │            │.parquet │            │.parquet │
  │ (Floor) │            │ (Floor) │            │ (Floor) │
  │ (Wall)  │            │ (Wall)  │            │ (Wall)  │
  │ (Roof)  │            │ (Roof)  │            │ (Roof)  │
  └────┬────┘            └────┬────┘            └────┬────┘
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │     DuckDB       │
                    │  (Multi-Thread)  │  ← KEIN Bottleneck!
                    │                  │
                    │  read_parquet()  │  ← Bulk-Load aller Files
                    └──────────────────┘
```

### Performance-Vergleich

| Metrik | SQLite | DuckDB | Speedup |
|--------|--------|--------|---------|
| Import 1 Tile (8'000 Gebäude) | ~70s | ~15s | **5x** |
| Import 20 Tiles parallel | ~180s | ~35s | **5x** |
| Nachbar-Query (100m Radius) | ~50ms | ~5ms | **10x** |
| 3D-Geometrie laden | ~20ms | ~2ms | **10x** |

---

## Neues DB-Schema

### Übersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                        building_3d.duckdb                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    buildings (Haupttabelle)                  │   │
│  │  ───────────────────────────────────────────────────────────│   │
│  │  egid              INTEGER PRIMARY KEY                       │   │
│  │  objektart         VARCHAR        ← NEU!                     │   │
│  │  name_komplett     VARCHAR        ← NEU!                     │   │
│  │  gebaeude_nutzung  VARCHAR        ← NEU!                     │   │
│  │  gebaeudeeinheit   VARCHAR        ← NEU! (verknüpft Layer)   │   │
│  │  ───────────────────────────────────────────────────────────│   │
│  │  dach_max          DOUBLE         (Firsthöhe absolut)        │   │
│  │  dach_min          DOUBLE         (Traufhöhe absolut)        │   │
│  │  gelaendepunkt     DOUBLE         (Terrain absolut)          │   │
│  │  gesamthoehe       DOUBLE         (Gebäudehöhe relativ)      │   │
│  │  ───────────────────────────────────────────────────────────│   │
│  │  center_e, center_n DOUBLE        (LV95 Zentroid)            │   │
│  │  tile_id           VARCHAR        (Referenz zum Tile)        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              │ 1:1 (via EGID oder GEBAEUDEEINHEIT) │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    building_floors                           │   │
│  │  ───────────────────────────────────────────────────────────│   │
│  │  gebaeudeeinheit   VARCHAR PRIMARY KEY ← NEU 13.01.2026     │   │
│  │  egid              INTEGER                                   │   │
│  │  gelaendepunkt     DOUBLE         (Terrain m ü.M.)           │   │
│  │  geometry_wkb      BLOB           ← WKB 3D-Geometrie         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    building_walls                            │   │
│  │  ───────────────────────────────────────────────────────────│   │
│  │  gebaeudeeinheit   VARCHAR PRIMARY KEY ← NEU 13.01.2026     │   │
│  │  egid              INTEGER                                   │   │
│  │  z_min             DOUBLE         (Terrain m ü.M.)           │   │
│  │  z_max             DOUBLE         (Traufe m ü.M.)            │   │
│  │  geometry_wkb      BLOB           ← WKB 3D-MultiPolygon      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    building_roofs                            │   │
│  │  ───────────────────────────────────────────────────────────│   │
│  │  gebaeudeeinheit   VARCHAR PRIMARY KEY ← NEU 13.01.2026     │   │
│  │  egid              INTEGER                                   │   │
│  │  dach_min          DOUBLE         (Traufe m ü.M.)            │   │
│  │  dach_max          DOUBLE         (First m ü.M.)             │   │
│  │  roof_angle_deg    DOUBLE         ← Berechnet aus 3D         │   │
│  │  geometry_wkb      BLOB           ← WKB 3D-Geometrie         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### SQL Schema Definition

```sql
-- ============================================================
-- HAUPTTABELLE: buildings
-- ============================================================

CREATE TABLE buildings (
    -- Identifikation
    egid                INTEGER PRIMARY KEY,
    gebaeudeeinheit     VARCHAR,            -- Verknüpft alle Layer

    -- Neue Attribute aus swissBUILDINGS3D 3.0
    objektart           VARCHAR,            -- "Gebaeude Einzelhaus", "Sakrales Gebaeude"
    name_komplett       VARCHAR,            -- "Berner Münster"
    gebaeude_nutzung    VARCHAR,            -- "Stadion", "Parkhaus"

    -- Höhen (absolut, m ü.M.)
    dach_max            DOUBLE,             -- Firsthöhe
    dach_min            DOUBLE,             -- Traufhöhe
    gelaendepunkt       DOUBLE,             -- Terrain
    gesamthoehe         DOUBLE,             -- Gebäudehöhe (relativ)

    -- Zentroid (LV95)
    center_e            DOUBLE NOT NULL,
    center_n            DOUBLE NOT NULL,

    -- Tile-Referenz
    tile_id             VARCHAR NOT NULL,

    -- Metadaten
    herkunft            VARCHAR DEFAULT 'swisstopo',
    herkunft_jahr       INTEGER,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES (vollständige Liste aus building_3d_schema.py:114-122)
-- ============================================================
CREATE INDEX idx_buildings_3d_coords ON buildings_3d(center_e, center_n);
CREATE INDEX idx_buildings_3d_tile ON buildings_3d(tile_id);
CREATE INDEX idx_buildings_3d_objektart ON buildings_3d(objektart);
CREATE INDEX idx_buildings_3d_gebaeudeeinheit ON buildings_3d(gebaeudeeinheit);
CREATE INDEX idx_roofs_egid ON building_roofs(egid);
CREATE INDEX idx_walls_egid ON building_walls(egid);
CREATE INDEX idx_floors_egid ON building_floors(egid);

-- ============================================================
-- FLOOR LAYER: Gebäude-Grundriss mit Terrain
-- NEU 13.01.2026 21:30: gebaeudeeinheit als PRIMARY KEY
-- ============================================================

CREATE TABLE building_floors (
    gebaeudeeinheit     VARCHAR PRIMARY KEY,  -- NEU: Natürlicher Schlüssel
    egid                INTEGER,
    gelaendepunkt       DOUBLE,               -- Terrain-Höhe (m ü.M.)
    geometry_wkb        BLOB,                 -- WKB 3D-Geometrie
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index auf egid für Abfragen nach Gebäude-ID
CREATE INDEX idx_floors_egid ON building_floors(egid);

-- ============================================================
-- WALL LAYER: Fassaden als 3D-Flächen
-- NEU 13.01.2026 21:30: gebaeudeeinheit als PRIMARY KEY
-- ============================================================

CREATE TABLE building_walls (
    gebaeudeeinheit     VARCHAR PRIMARY KEY,  -- NEU: Natürlicher Schlüssel
    egid                INTEGER,
    z_min               DOUBLE,               -- Terrain (m ü.M.)
    z_max               DOUBLE,               -- Traufe (m ü.M.)
    geometry_wkb        BLOB,                 -- WKB 3D-MultiPolygon
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index auf egid für Abfragen nach Gebäude-ID
CREATE INDEX idx_walls_egid ON building_walls(egid);

-- ============================================================
-- ROOF LAYER: Dach als 3D-Körper
-- NEU 13.01.2026 21:30: gebaeudeeinheit als PRIMARY KEY
-- ============================================================

CREATE TABLE building_roofs (
    gebaeudeeinheit     VARCHAR PRIMARY KEY,  -- NEU: Natürlicher Schlüssel
    egid                INTEGER,
    dach_min            DOUBLE,               -- Traufe (m ü.M.)
    dach_max            DOUBLE,               -- First (m ü.M.)
    roof_form           VARCHAR,              -- Satteldach, Flachdach, etc.
    roof_angle_deg      DOUBLE,               -- Dachneigung in Grad
    roof_orientation    VARCHAR,              -- N-S, O-W, etc.
    z_levels            VARCHAR,              -- JSON: Z-Ebenen für Analyse
    geometry_wkb        BLOB,                 -- WKB 3D-Geometrie
    has_full_geometry   INTEGER DEFAULT 0,    -- Flag: Vollständige Geometrie
    calculated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calculation_method  VARCHAR               -- Quelle: '3d_geometry', 'heuristic'
);

-- Index auf egid für Abfragen nach Gebäude-ID
CREATE INDEX idx_roofs_egid ON building_roofs(egid);

-- ============================================================
-- VIEWS für einfachen Zugriff
-- ============================================================

-- Komplett-Ansicht eines Gebäudes mit allen Layern
CREATE VIEW building_complete AS
SELECT
    b.*,
    f.geometry AS floor_geometry,
    f.z_terrain_diff,
    f.area_m2 AS floor_area_m2,
    w.geometry AS wall_geometry,
    w.wall_height,
    w.surface_area_m2 AS wall_area_m2,
    r.geometry AS roof_geometry,
    r.roof_angle_deg,
    r.roof_azimuth_deg,
    r.roof_area_m2
FROM buildings b
LEFT JOIN building_floors f ON b.egid = f.egid
LEFT JOIN building_walls w ON b.egid = w.egid
LEFT JOIN building_roofs r ON b.egid = r.egid;

-- Gebäude mit hoher Komplexität (für spezielle Behandlung)
CREATE VIEW complex_buildings AS
SELECT *
FROM buildings
WHERE objektart IN ('Sakrales Gebaeude', 'Sakraler Turm', 'Hochhaus')
   OR (dach_max - dach_min) > 20
   OR name_komplett IS NOT NULL;
```

---

## Import-Pipeline

### Ablauf

```
┌─────────────────────────────────────────────────────────────────────┐
│                    3D IMPORT PIPELINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PHASE 1: DOWNLOAD (parallel, asyncio)                              │
│  ═══════════════════════════════════                                │
│                                                                     │
│    STAC API → Tile URLs → Download → tiles/{tile_id}.gdb            │
│                                                                     │
│  PHASE 2: PARSE (parallel, ProcessPoolExecutor)                     │
│  ═══════════════════════════════════════════════                    │
│                                                                     │
│    Für jedes Tile, für jeden Layer:                                 │
│                                                                     │
│    ┌───────────────────────────────────────────────────────────┐   │
│    │  GDB Tile                                                  │   │
│    │      │                                                     │   │
│    │      ├── Building_solid → buildings.parquet                │   │
│    │      │   (EGID, Höhen, Attribute)                          │   │
│    │      │                                                     │   │
│    │      ├── Floor → building_floors.parquet                   │   │
│    │      │   (3D Geometrie, Terrain)                           │   │
│    │      │                                                     │   │
│    │      ├── Wall → building_walls.parquet                     │   │
│    │      │   (3D Geometrie, Fassaden)                          │   │
│    │      │                                                     │   │
│    │      └── Roof_solid → building_roofs.parquet               │   │
│    │          (3D Geometrie + Winkelberechnung!)                │   │
│    └───────────────────────────────────────────────────────────┘   │
│                                                                     │
│  PHASE 3: LOAD (DuckDB bulk-load)                                   │
│  ═════════════════════════════════                                  │
│                                                                     │
│    DuckDB:                                                          │
│      INSERT INTO buildings                                          │
│      SELECT * FROM read_parquet('parquet/buildings_*.parquet')      │
│                                                                     │
│      INSERT INTO building_floors                                    │
│      SELECT * FROM read_parquet('parquet/floors_*.parquet')         │
│                                                                     │
│      INSERT INTO building_walls                                     │
│      SELECT * FROM read_parquet('parquet/walls_*.parquet')          │
│                                                                     │
│      INSERT INTO building_roofs                                     │
│      SELECT * FROM read_parquet('parquet/roofs_*.parquet')          │
│                                                                     │
│  PHASE 4: POST-PROCESS                                              │
│  ═════════════════════                                              │
│                                                                     │
│    - Indizes erstellen                                              │
│    - Statistiken berechnen (ANALYZE)                                │
│    - Parquet-Temp-Dateien löschen                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Dachwinkel aus 3D berechnen

```python
def calculate_roof_angle_from_3d(geometry_coords: list) -> tuple[float, float]:
    """
    Berechnet Dachwinkel und Azimut aus echter 3D-Geometrie.

    Returns:
        (roof_angle_deg, roof_azimuth_deg)
    """
    import math

    # Alle Z-Werte extrahieren
    all_points = []
    def extract(coords):
        if isinstance(coords[0], (int, float)):
            if len(coords) >= 3:
                all_points.append(coords)
        else:
            for c in coords:
                extract(c)
    extract(geometry_coords)

    if not all_points:
        return 0.0, 0.0

    # Z-Bereich
    zs = [p[2] for p in all_points]
    z_min, z_max = min(zs), max(zs)
    z_diff = z_max - z_min

    if z_diff < 0.5:
        return 0.0, 0.0  # Flachdach

    # Punkte bei Min und Max Z
    min_z_points = [(p[0], p[1]) for p in all_points if p[2] < z_min + 0.5]
    max_z_points = [(p[0], p[1]) for p in all_points if p[2] > z_max - 0.5]

    if not min_z_points or not max_z_points:
        return 0.0, 0.0

    # Zentren berechnen
    min_center = (
        sum(p[0] for p in min_z_points) / len(min_z_points),
        sum(p[1] for p in min_z_points) / len(min_z_points)
    )
    max_center = (
        sum(p[0] for p in max_z_points) / len(max_z_points),
        sum(p[1] for p in max_z_points) / len(max_z_points)
    )

    # Horizontale Distanz
    dx = max_center[0] - min_center[0]
    dy = max_center[1] - min_center[1]
    horiz_dist = math.sqrt(dx*dx + dy*dy)

    if horiz_dist < 0.1:
        return 90.0, 0.0  # Vertikales Element (Turm?)

    # Dachwinkel
    roof_angle = math.degrees(math.atan(z_diff / horiz_dist))

    # First-Azimut (senkrecht zur Neigungsrichtung)
    azimuth = math.degrees(math.atan2(dx, dy))
    if azimuth < 0:
        azimuth += 360
    first_azimuth = (azimuth + 90) % 360

    return round(roof_angle, 1), round(first_azimuth, 1)
```

---

## 3D-Viewer Integration

### API-Endpunkte

```python
# Komplettes 3D-Modell für ein Gebäude
GET /api/v1/building/{egid}/3d
{
    "egid": 1230337,
    "name": "Berner Münster",
    "objektart": "Sakrales Gebaeude",

    "floor": {
        "geometry": [[x,y,z], ...],  # 1'204 Punkte
        "z_terrain_diff": 15.3
    },

    "walls": {
        "geometry": [[x,y,z], ...],  # 4'360 Punkte
        "wall_height": 71.2
    },

    "roof": {
        "geometry": [[x,y,z], ...],  # 112 Punkte
        "roof_angle_deg": 30.7,
        "roof_azimuth_deg": 45.0
    },

    "bounds": {
        "x": [2600943.0, 2601030.7],
        "y": [1199552.4, 1199593.5],
        "z": [531.1, 635.2]
    }
}

# 3D-Modelle für Nachbarn (für Kontext)
GET /api/v1/building/{egid}/3d/neighbors?radius_m=50
```

### Three.js Rendering

```javascript
// BuildingViewer3D.tsx

async function loadBuilding3D(egid: number) {
    const data = await fetch(`/api/v1/building/${egid}/3d`).then(r => r.json());

    const group = new THREE.Group();

    // Floor (mit Terrain-Variation!)
    const floorGeometry = createGeometryFromPoints(data.floor.geometry);
    const floorMesh = new THREE.Mesh(floorGeometry, new THREE.MeshStandardMaterial({
        color: 0x8B7355,  // Erde
        side: THREE.DoubleSide
    }));
    group.add(floorMesh);

    // Walls (alle Fassaden)
    const wallGeometry = createGeometryFromPoints(data.walls.geometry);
    const wallMesh = new THREE.Mesh(wallGeometry, new THREE.MeshStandardMaterial({
        color: 0xE8DCC8,  // Sandstein
        side: THREE.DoubleSide
    }));
    group.add(wallMesh);

    // Roof (echte 3D-Form)
    const roofGeometry = createGeometryFromPoints(data.roof.geometry);
    const roofMesh = new THREE.Mesh(roofGeometry, new THREE.MeshStandardMaterial({
        color: 0x8B4513,  // Dachziegel
        side: THREE.DoubleSide
    }));
    group.add(roofMesh);

    return group;
}
```

---

## Speicherbedarf

### Pro Gebäude (geschätzt)

| Tabelle | Ø Bytes/Gebäude | Beschreibung |
|---------|-----------------|--------------|
| buildings | ~200 | Attribute |
| building_floors | ~5'000 | ~100 Punkte × 48 Bytes |
| building_walls | ~15'000 | ~300 Punkte × 48 Bytes |
| building_roofs | ~2'000 | ~50 Punkte × 48 Bytes |
| **Total** | **~22 KB** | |

### Hochrechnung Schweiz

| Region | Gebäude | buildings | + 3D Layer | Gesamt |
|--------|---------|-----------|------------|--------|
| Bern Stadt | ~50'000 | ~10 MB | ~1.1 GB | ~1.1 GB |
| Kanton Bern | ~300'000 | ~60 MB | ~6.6 GB | ~6.7 GB |
| Ganze Schweiz | ~2'000'000 | ~400 MB | ~44 GB | ~45 GB |

> **Hinweis:** Für Railway.app (10 GB Volume) reicht Kanton Bern + Nachbarkantone.
> Für Schweiz-weit: Cloud-Storage oder selektives Laden.

---

## Migration von SQLite

### Phase 1: Parallelbetrieb ✅ (Abgeschlossen 13.01.2026 17:45)

```python
# config.py - AKTUELL IMPLEMENTIERT (Stand 13.01.2026 17:45)

# DuckDB ist DEFAULT - nur mit USE_DUCKDB=false wird SQLite verwendet
USE_DUCKDB = os.getenv("USE_DUCKDB", "true").lower() != "false"

def get_building_3d_connection(read_only: bool = False):
    """Factory für DB-Connection (DuckDB default, SQLite fallback)."""
    if USE_DUCKDB:
        import duckdb
        return duckdb.connect(str(DUCKDB_PATH), read_only=read_only)
    else:
        import sqlite3
        return sqlite3.connect(str(BUILDING_3D_DB_PATH))
```

**Backend starten:**
```bash
# Standard - DuckDB ist der Default:
".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000

# Nur falls SQLite benötigt wird (Legacy-Fallback):
set USE_DUCKDB=false && ".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
```

### Phase 2: Feature-Flags

| Flag | Beschreibung | Status |
|------|--------------|--------|
| `USE_DUCKDB` | DuckDB ist Default, SQLite mit `=false` | ✅ Implementiert (Default: true) |
| `LOAD_3D_LAYERS` | Floor/Wall/Roof laden | 🔴 Noch nicht implementiert |
| `CALC_ROOF_FROM_3D` | Dachwinkel aus 3D | 🔴 Noch nicht implementiert |

### Phase 3: Vollständige Migration (Geplant)

1. ✅ DuckDB produktiv setzen
2. 🔴 3D-Layer aktivieren
3. ⏸️ SQLite-Code entfernen (nach Testphase)
4. ⏸️ Alte DB-Dateien löschen

---

## Nächste Schritte (Stand 13.01.2026 17:45)

### ✅ Erledigt
1. [x] DuckDB in Requirements aufnehmen
2. [x] Schema-Erstellung implementieren
3. [x] `building_3d_service.py` Dual-Mode (SQLite/DuckDB)
4. [x] DuckDB als Default (Flag invertiert)
5. [x] INSERT OR REPLACE für beide Engines

### 🔴 Offen
6. [ ] tile_prefetch.py erweitern (alle Layer parsen)
7. [ ] API-Endpunkte für 3D-Daten (Floor/Wall/Roof)
8. [ ] 3D-Viewer Integration mit echten Layer-Daten
9. [ ] Railway.app Deployment mit DuckDB testen

### ⏸️ Zurückgestellt
- Parquet-Pipeline: Nicht nötig, INSERT OR REPLACE ist schnell genug

---

## Referenzen

- [SWISSBUILDINGS3D_ANALYSE.md](SWISSBUILDINGS3D_ANALYSE.md) - Layer-Details
- [BATCH_IMPORT.md](BATCH_IMPORT.md) - DuckDB-Konzept (Anhang B)
- [swisstopo Dokumentation](https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta)
