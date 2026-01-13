# Batch-Import für swissBUILDINGS3D Tiles

> **Version:** 6.3 (Stand 14.01.2026 00:30)
> **Status:** Optimale Parallelisierungs-Architektur 🚀

## NEU: All-Layer-Import Strategie (13.01.2026 18:00)

**Kernidee:** Alle 3D-Layer (Building_solid, Roof_solid, Wall) werden **zusammen**
beim Batch-Import extrahiert. Danach wird das Tile **gelöscht**.

### Warum diese Änderung?

| Vorher (On-Demand) | Jetzt (All-Layer-Batch) |
|--------------------|-------------------------|
| Tile downloaden (~30MB) | Tile downloaden (~30MB) |
| Building_solid → DB | **Alle Layer → DB** |
| Tile bleibt liegen | **Tile löschen** 🗑️ |
| Später: Tile nochmal laden für Walls | Walls bereits in DB ✅ |

**Vorteile:**
- **Kein doppelter Download:** Tile wird nur 1x geladen
- **Weniger Speicher:** tiles/ Ordner bleibt leer
- **Schnellere Wall-Abfragen:** Sofort aus DB (<100ms statt 5-10s)
- **Sauberes Deployment:** Nur DB-Datei auf Railway deployen

### Import-Workflow (NEU)

```
┌─────────────────────────────────────────────────────────────────┐
│              ALL-LAYER BATCH IMPORT (NEU)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. DOWNLOAD                                                     │
│     Tile.gdb.zip herunterladen (~30MB)                          │
│                                                                  │
│  2. PARSE (ein Durchgang!)                                       │
│     ├─ Building_solid → buildings_3d                            │
│     ├─ Roof_solid → building_roofs                              │
│     └─ Wall → building_walls (NEU!)                             │
│                                                                  │
│  3. FLAGGEN                                                      │
│     has_3d_layers = 1 für alle Gebäude setzen                   │
│                                                                  │
│  4. CLEANUP                                                      │
│     Tile-Verzeichnis löschen (tiles/{tile_id}/)                 │
│     → Nur tiles.db Metadaten behalten                           │
│                                                                  │
│  5. DEPLOY                                                       │
│     building_3d.duckdb auf Railway deployen                     │
│     → Schnelle Antwortzeiten ohne On-Demand Downloads           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### DB-Deployment auf Railway

**Workflow für Produktions-Deployment:**

```bash
# 1. LOKAL: Batch-Import aller benötigten Tiles
cd backend
python scripts/import_tiles.py --region bern --all-layers

# 2. LOKAL: DB-Grösse prüfen
ls -lh app/data/building_3d.duckdb
# Erwartete Grösse: ~200-500MB für Kanton Bern

# 3. GIT: DB committen (oder via LFS bei grossen DBs)
git add app/data/building_3d.duckdb
git commit -m "chore: add pre-imported building DB for deployment"

# 4. RAILWAY: Deployment
git push origin main
# → Railway verwendet die vorbereitete DB
# → Keine On-Demand Downloads nötig
# → Schnelle Antwortzeiten ab dem ersten Request
```

**Railway Volume-Konfiguration:**
```
/app/data/
├── building_3d.duckdb    # Vom Git-Repo (read-only)
├── building_contexts.db  # Runtime-Daten (Volume)
├── geruestbau.db         # Projekte (Volume)
└── tiles.db              # Metadaten (Volume, minimal)
```

### Speicher-Kalkulation

| Daten | Pro Gebäude | 18'000 Gebäude | Bemerkung |
|-------|-------------|----------------|-----------|
| buildings_3d | ~2 KB | ~36 MB | Polygon JSON + Höhen |
| building_roofs | ~500 B | ~9 MB | Höhen + Metadaten |
| building_walls | ~50 KB | ~900 MB | WKB 3D-Geometrie |
| **DB Total** | - | **~1 GB** | Für Kanton Bern |

**Vergleich:**
| Ansatz | Speicher (Kanton Bern) |
|--------|------------------------|
| Alte Strategie (GDBs behalten) | ~3-5 GB (tiles/ Ordner) |
| Neue Strategie (nur DB) | ~1 GB |
| Einsparung | **~70-80%** |

### Implementierungs-TODO

| # | Task | Datei | Status |
|---|------|-------|--------|
| 1 | Wall-Import in tile_prefetch.py | `tile_prefetch.py` | ✅ 13.01.2026 |
| 2 | Tile-Cleanup nach Import | `tile_prefetch.py` | ✅ 13.01.2026 |
| 3 | import_tiles.py: --all-layers Flag | `scripts/import_tiles.py` | 📋 TODO |
| 4 | tiles.db: import_status Spalte | `tile_cache.py` | ✅ 13.01.2026 |
| 5 | Schema: gebaeudeeinheit als PRIMARY KEY | `building_3d_schema.py` | ✅ 13.01.2026 |

## DuckDB ist der Default

```bash
# Windows CMD/PowerShell (Standard - verwendet DuckDB):
".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000

# Nur falls SQLite benötigt wird (Legacy-Fallback):
set USE_DUCKDB=false && ".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
```

## Übersicht

Der Batch-Import ermöglicht das Vorladen aller Tiles vor einem Deployment.
Dies vermeidet lange Wartezeiten beim ersten User-Request.

### Anwendungsfälle

| Usecase | Beschreibung |
|---------|--------------|
| **Pre-Deployment** | Alle Tiles für Zielregion vorab laden |
| **Inkrementelles Update** | Nur neue/geänderte Tiles nachladen |
| **Regionales Deployment** | Nur bestimmte Kantone/Regionen |
| **Entwicklung** | Einzelne Tiles für Tests laden |

---

## Architektur

### Datenfluss (AKTUALISIERT 13.01.2026)

```
┌─────────────────────────────────────────────────────────────────┐
│              BATCH IMPORT PROZESS (All-Layer)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. DISCOVERY (STAC API)                                         │
│  ════════════════════════                                        │
│  GET /api/stac/v0.9/collections/ch.swisstopo.swissbuildings3d    │
│       │                                                          │
│       ▼                                                          │
│  Liste aller verfügbaren Tiles mit:                              │
│  - tile_id, download_url, datetime, bbox                         │
│                                                                  │
│  2. DIFF (tiles.db)                                              │
│  ══════════════════                                              │
│  Vergleich: STAC-Tiles vs. lokale tiles.db                       │
│       │                                                          │
│       ├── NEU: Tile nicht in DB                                  │
│       ├── UPDATE: stac_datetime > downloaded_at                  │
│       └── AKTUELL: Keine Änderung                                │
│                                                                  │
│  3. DOWNLOAD (parallel)                                          │
│  ══════════════════════                                          │
│  asyncio.gather() mit Semaphore (max 5 parallel)                 │
│       │                                                          │
│       ▼                                                          │
│  tiles/{tile_id}/ (temporär)                                     │
│                                                                  │
│  4. ALL-LAYER IMPORT (NEU!)                                      │
│  ══════════════════════════                                      │
│  Für jedes Tile in EINEM Durchgang:                              │
│       │                                                          │
│       ├─► Building_solid → buildings_3d (Polygon, Höhen)         │
│       ├─► Roof_solid → building_roofs (dach_min/max, WKB)        │
│       └─► Wall → building_walls (z_min/max, WKB) ← NEU!          │
│       │                                                          │
│       └─► has_3d_layers = 1 für alle Gebäude setzen              │
│                                                                  │
│  5. CLEANUP (WICHTIG!)                                           │
│  ═════════════════════                                           │
│       │                                                          │
│       ├─► Tile-Verzeichnis LÖSCHEN: tiles/{tile_id}/             │
│       │   → Spart Speicher (30MB+ pro Tile)                      │
│       │   → DB hat alle Daten, GDB nicht mehr nötig              │
│       │                                                          │
│       └─► tiles.db: import_status = 'imported', local_path=NULL  │
│                                                                  │
│  6. DEPLOYMENT                                                   │
│  ═════════════                                                   │
│  building_3d.duckdb committen + auf Railway deployen             │
│  → Schnelle Antwortzeiten ohne On-Demand Downloads               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Komponenten

| Komponente | Datei | Zweck |
|------------|-------|-------|
| **Import-Skript** | `scripts/import_tiles.py` | CLI für Batch-Import |
| **Tile-Cache** | `tile_cache.py` | Speichert GDB-Dateien + Metadaten |
| **Tile-Prefetch** | `tile_prefetch.py` | Parsed GDB → building_3d.duckdb |
| **Building-3D-Service** | `building_3d_service.py` | Bulk-Insert in DB |

---

## Datenbanken

### tiles.db (Tile-Metadaten)

Speichert Informationen über heruntergeladene Tiles für:
- Change-Detection (wann zuletzt aktualisiert?)
- Inkrementelle Updates (welche Tiles sind neu?)
- Import-Status (erfolgreich importiert?)

```sql
CREATE TABLE tiles (
    tile_id TEXT PRIMARY KEY,
    local_path TEXT NOT NULL,
    download_url TEXT,

    -- Zeitstempel
    downloaded_at TIMESTAMP,
    imported_at TIMESTAMP,
    last_check TIMESTAMP,

    -- Versionierung (für Change-Detection)
    stac_datetime TEXT,         -- Aus STAC API (Tile-Version)
    etag TEXT,                  -- HTTP ETag
    content_hash TEXT,          -- SHA256 der GDB

    -- Status
    import_status TEXT DEFAULT 'pending',
    -- Werte: pending, downloading, downloaded, importing, imported, failed
    error_message TEXT,

    -- Statistiken
    file_size_mb REAL,
    building_count INTEGER,
    import_duration_s REAL,

    -- BBox (für Region-Filter)
    bbox_west REAL,
    bbox_south REAL,
    bbox_east REAL,
    bbox_north REAL
);

CREATE INDEX idx_tiles_status ON tiles(import_status);
CREATE INDEX idx_tiles_bbox ON tiles(bbox_west, bbox_south, bbox_east, bbox_north);
```

### building_3d.duckdb (Gebäudedaten) - NEU: DuckDB

> **Migration 13.01.2026:** SQLite → DuckDB für bessere Bulk-Performance

Speichert alle Gebäude aus importierten Tiles:

```sql
CREATE TABLE buildings_3d (
    egid INTEGER PRIMARY KEY,
    polygon TEXT,               -- JSON: [[e,n], [e,n], ...]
    traufhoehe_m REAL,
    firsthoehe_m REAL,
    gebaeudehoehe_m REAL,
    area_m2 REAL,
    perimeter_m REAL,
    center_e REAL,              -- LV95 Zentroid
    center_n REAL,
    tile_id TEXT,               -- Referenz zum Tile
    source TEXT,
    -- NEU: Erweiterte Attribute
    objektart TEXT,
    name_komplett TEXT,
    gebaeude_nutzung TEXT,
    gebaeudeeinheit TEXT,
    roof_form TEXT,
    roof_form_confidence REAL,
    roof_orientation TEXT,
    has_3d_layers INTEGER DEFAULT 0
);

-- Indexes (definiert in building_3d_schema.py)
CREATE INDEX idx_buildings_3d_coords ON buildings_3d(center_e, center_n);
CREATE INDEX idx_buildings_3d_tile ON buildings_3d(tile_id);
CREATE INDEX idx_buildings_3d_objektart ON buildings_3d(objektart);
CREATE INDEX idx_buildings_3d_gebaeudeeinheit ON buildings_3d(gebaeudeeinheit);

-- Indexes für 3D-Layer Tabellen
CREATE INDEX idx_roofs_egid ON building_roofs(egid);
CREATE INDEX idx_walls_egid ON building_walls(egid);
CREATE INDEX idx_floors_egid ON building_floors(egid);
```

> **WICHTIG 14.01.2026:** Es gibt 7 Indexes insgesamt. Siehe `building_3d_schema.py:114-122`.

**DuckDB-Vorteile:**
- Multi-Threading für parallele Queries
- Bessere Bulk-Insert Performance (~5x schneller)
- Native JSON-Unterstützung
- `INSERT OR REPLACE` funktioniert (ab DuckDB ≥0.8)

---

## Was wird importiert? (Stand 13.01.2026 16:45)

### Pro Tile (aus STAC API)

| Feld | Quelle | Beschreibung |
|------|--------|--------------|
| `tile_id` | STAC | z.B. "2600-1199" (1km×1km Raster) |
| `download_url` | STAC | URL zur GDB-Datei |
| `stac_datetime` | STAC | Versionierung für Change-Detection |
| `bbox_*` | STAC | Bounding-Box (LV95) |
| `building_count` | Berechnet | Anzahl Gebäude nach Import |
| `import_duration_s` | Gemessen | Performance-Tracking |

### Pro Gebäude (aus GDB Building_solid Layer)

| Feld | GDB-Attribut | Beschreibung |
|------|--------------|--------------|
| `egid` | EGID | Eidg. Gebäudeidentifikator |
| `polygon` | Geometrie | JSON-Array der Polygon-Koordinaten |
| `traufhoehe_m` | DACH_MIN - GELAENDEPUNKT | Traufhöhe über Terrain |
| `firsthoehe_m` | DACH_MAX - GELAENDEPUNKT | Firsthöhe über Terrain |
| `gebaeudehoehe_m` | GESAMTHOEHE | Gebäudehöhe (direkt) |
| `area_m2` | Berechnet | Grundfläche aus Polygon |
| `perimeter_m` | Berechnet | Umfang aus Polygon |
| `center_e`, `center_n` | Berechnet | Zentroid (LV95) |
| `objektart` | OBJEKTART | z.B. "Gebaeude", "Sakrales Gebaeude" |
| `name_komplett` | NAME_KOMPLETT | z.B. "Berner Münster" |
| `gebaeude_nutzung` | GEBAEUDENUTZUNG | z.B. "Wohnen", "Industrie" |
| `gebaeudeeinheit` | GEBAEUDEEINHEIT | Verknüpft 3D-Layer |
| `roof_form` | Berechnet | Satteldach, Flachdach, etc. |
| `roof_orientation` | Berechnet | N-S, O-W, etc. |
| `has_3d_layers` | Flag | 1 wenn Wall/Roof extrahiert |

### Datenquellen-Mapping (swissBUILDINGS3D 3.0) - AKTUALISIERT 13.01.2026

```
GDB-Datei (pro Tile)
│
├── Building_solid (Layer)     → buildings_3d Tabelle ✅ IMMER
│   ├── EGID                   → egid
│   ├── OBJEKTART              → objektart
│   ├── NAME_KOMPLETT          → name_komplett
│   ├── GEBAEUDENUTZUNG        → gebaeude_nutzung
│   ├── GEBAEUDEEINHEIT        → gebaeudeeinheit
│   ├── DACH_MAX               → (für firsthoehe_m)
│   ├── DACH_MIN               → (für traufhoehe_m)
│   ├── GELAENDEPUNKT          → (Terrain-Referenz)
│   ├── GESAMTHOEHE            → gebaeudehoehe_m
│   └── Geometrie (Polygon)    → polygon, area_m2, perimeter_m, center_*
│
├── Roof_solid (Layer)         → building_roofs Tabelle ✅ IMMER
│   ├── EGID                   → egid (Verknüpfung)
│   ├── GEBAEUDEEINHEIT        → gebaeudeeinheit
│   ├── DACH_MIN               → dach_min (m ü.M.)
│   ├── DACH_MAX               → dach_max (m ü.M.)
│   └── Geometrie (WKB)        → geometry_wkb (3D-Dachflächen)
│
├── Wall (Layer)               → building_walls Tabelle ✅ IMMER (NEU!)
│   ├── EGID                   → egid (Verknüpfung)
│   ├── GEBAEUDEEINHEIT        → gebaeudeeinheit
│   ├── GELAENDEPUNKT          → z_min (Terrain, m ü.M.)
│   ├── GESAMTHOEHE            → (für z_max Berechnung)
│   └── Geometrie (WKB)        → geometry_wkb (3D-Fassadenflächen)
│
└── Floor (Layer)              → ❌ NICHT importiert (redundant)
```

> **Änderung 13.01.2026:** Wall-Layer wird jetzt **IMMER** beim Batch-Import
> extrahiert (nicht mehr on-demand). Spart spätere Tile-Downloads.

### Beispiel: Tile "2600-1199" (Bern Zentrum)

```
Tile-ID:        2600-1199
BBox:           E 2600000-2601000, N 1199000-1200000
Gebäude:        ~150
Import-Zeit:    ~1.5s (DuckDB)
Dateigrösse:    ~15 MB (GDB)

Enthaltene Gebäude (Auswahl):
├── EGID 2242547  Bundeshaus (Arkaden, Kuppel)
├── EGID 1230337  Berner Münster (Turm 100m)
├── EGID 1017961  Zytglogge
└── ... ~147 weitere
```

---

## GDB-Parsing mit Fiona

### Was ist Fiona?

**Fiona** ist ein Python-Wrapper um OGR (Teil von GDAL) für das Lesen/Schreiben von Geodaten.
Der entscheidende Vorteil: **Streaming-Iteration** statt vollständiges Laden in den Speicher.

### Warum Fiona statt geopandas?

| Aspekt | geopandas | fiona (aktuell) |
|--------|-----------|-----------------|
| **Lademodus** | Alles in GeoDataFrame | Streaming (Feature für Feature) |
| **RAM-Verbrauch** | ~500MB für grosses Tile | ~10MB (nur aktives Feature) |
| **Geschwindigkeit** | 11.5ms/Gebäude | 9.8ms/Gebäude |
| **Dependencies** | pandas, geopandas, numpy | nur fiona, shapely |

### Streaming vs. Vollständiges Laden

```
geopandas (vorher - LANGSAM):
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  GDB-Datei (500MB)                                         │
│       │                                                     │
│       ▼ gpd.read_file() - LÄDT ALLES                       │
│       │                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  GeoDataFrame im RAM                                │   │
│  │  (500MB + pandas Overhead = ~800MB)                 │   │
│  │  - Alle 7000 Gebäude auf einmal                     │   │
│  │  - Speicher bleibt belegt bis Ende                  │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼ for _, row in gdf.iterrows() - LANGSAM             │
│       │                                                     │
│  Verarbeitung...                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘

fiona (jetzt - SCHNELL):
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  GDB-Datei (500MB)                                         │
│       │                                                     │
│       │ fiona.open() - ÖFFNET NUR HANDLE                   │
│       │                                                     │
│       ▼ for feature in src: - STREAMING                    │
│       │                                                     │
│  ┌─────────────┐                                           │
│  │ Feature #1  │ → Verarbeiten → Speichern → FREIGEBEN    │
│  └─────────────┘                                           │
│       │ next()                                              │
│  ┌─────────────┐                                           │
│  │ Feature #2  │ → Verarbeiten → Speichern → FREIGEBEN    │
│  └─────────────┘                                           │
│       │ next()                                              │
│      ...                                                   │
│       │                                                     │
│  (Nur ~10MB RAM für aktuelles Feature)                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Parallelisierungs-Architektur

### Producer/Consumer Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                PRODUCER/CONSUMER ARCHITEKTUR                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRODUCER (ProcessPoolExecutor)                                 │
│  ═══════════════════════════════                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │Worker 1 │ │Worker 2 │ │Worker 3 │ │Worker 4 │               │
│  │Tile A   │ │Tile B   │ │Tile C   │ │Tile D   │               │
│  │ fiona   │ │ fiona   │ │ fiona   │ │ fiona   │               │
│  │shapely  │ │shapely  │ │shapely  │ │shapely  │               │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘               │
│       │           │           │           │                     │
│       └───────────┴─────┬─────┴───────────┘                     │
│                         │                                       │
│                         ▼                                       │
│              ┌──────────────────┐                               │
│              │  Result Queue    │  List[Dict] pro Tile          │
│              │  (im RAM)        │                               │
│              └────────┬─────────┘                               │
│                       │                                         │
│  CONSUMER (Main Thread)                                         │
│  ══════════════════════                                         │
│                       ▼                                         │
│              ┌──────────────────┐                               │
│              │  SQLite Writer   │  Bulk-INSERT                  │
│              │  (single thread) │  1000 rows/transaction        │
│              └──────────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Empfohlene Worker-Anzahl

| System | CPU-Kerne | Empfohlene Worker | RAM-Bedarf |
|--------|-----------|-------------------|------------|
| Laptop | 4-8 | **4** | ~400 MB |
| Desktop | 8-16 | **6-8** | ~800 MB |
| Server | 16-32 | **12-16** | ~1.6 GB |
| Railway.app | ~2 (shared) | **2** | ~200 MB |

**Formel:** `workers = min(cpu_count - 1, num_tiles, 8)`

### Speedup-Tabelle (aktuell)

| Szenario | Zeit (1 Tile) | Zeit (20 Tiles) | Speedup |
|----------|---------------|-----------------|---------|
| Sequentiell | 70s | 1400s (23min) | 1x |
| 4 Worker | 70s | ~400s (7min) | **~3.5x** |
| 8 Worker | 70s | ~350s (6min) | ~4x |

> Ab ~6 Workern wird SQLite zum Flaschenhals, nicht mehr das Parsing.

---

# ANHANG A: SQLite-Optimierungen (Quick Wins)

> **Ziel:** Maximale Performance ohne Technologie-Wechsel
> **Aufwand:** 2-4 Stunden
> **Erwarteter Speedup:** ~2-3x
> **Status:** ✅ Implementiert (10.01.2026)

## A.1 TODO-Liste SQLite-Optimierung

| # | Task | Datei                    | Aufwand | Speedup | Status |
|---|------|--------------------------|---------|---------|--------|
| 1 | Aggressive PRAGMAs | `building_3d_service.py` | 15 min | ~1.5x | ✅ |
| 2 | Batch-Size erhöhen (5000) | `building_3d_service.py` | 5 min | ~1.2x | ✅ |
| 3 | Index nachträglich | `import_tiles.py`        | 30 min | ~1.5x | ✅ C.8 |
| 4 | Prepared Statements | aktualisrvice.py`        | 30 min | ~1.1x | ✅ |
| 5 | Connection Pooling | `building_3d_service.py` | 1h | ~1.2x | ✅ |

> **✅ Task 3 GEFIXT (14.01.2026 00:30):** `drop_indexes()` und `create_indexes()` behandeln
> jetzt **ALLE 7 Indexes**. Implementiert in C.8. Keine partielle Implementierung mehr!

**Gesamter erwarteter Speedup:** ~2.5-3x

## A.2 Implementierung

### Task 1: Aggressive PRAGMAs

```python
# building_3d_service.py - In __init__ oder connection setup

def _setup_connection(self, conn: sqlite3.Connection):
    """Optimierte SQLite-Konfiguration für Batch-Import."""
    
    # WAL-Mode: Bessere Parallelität (Reads während Write)
    conn.execute("PRAGMA journal_mode=WAL")
    
    # NORMAL statt FULL: Weniger fsync, ~30% schneller
    # Risiko: Bei Crash können letzte Transaktionen verloren gehen
    # Für Batch-Import OK, da wir bei Fehler sowieso neu starten
    conn.execute("PRAGMA synchronous=NORMAL")
    
    # Grösserer Cache: 64MB statt default 2MB
    conn.execute("PRAGMA cache_size=-64000")
    
    # Temp-Tabellen im RAM
    conn.execute("PRAGMA temp_store=MEMORY")
    
    # Memory-Mapped I/O: 256MB
    conn.execute("PRAGMA mmap_size=268435456")
    
    # Page-Size optimieren (nur bei neuer DB!)
    # conn.execute("PRAGMA page_size=4096")
```

### Task 2: Batch-Size erhöhen

```python
# building_3d_service.py

# VORHER
BATCH_SIZE = 1000

# NACHHER - Grössere Batches = weniger Commits
BATCH_SIZE = 5000

def bulk_save(self, buildings: list[dict]) -> int:
    """Bulk-Insert mit grösseren Batches."""
    
    with self._get_connection() as conn:
        cursor = conn.cursor()
        
        for i in range(0, len(buildings), BATCH_SIZE):
            batch = buildings[i:i + BATCH_SIZE]
            cursor.executemany(INSERT_SQL, [
                self._building_to_tuple(b) for b in batch
            ])
        
        conn.commit()
    
    return len(buildings)
```

### Task 3: Index nachträglich erstellen

```python
# import_tiles.py - Neue Funktion

def import_with_deferred_index(tiles: list[dict], db_path: str):
    """Import ohne Index, dann Index erstellen."""
    
    conn = sqlite3.connect(db_path)
    
    # 1. Index droppen (falls existiert)
    print("[OPTIMIZE] Dropping indexes for faster import...")
    conn.execute("DROP INDEX IF EXISTS idx_buildings_3d_coords")
    conn.execute("DROP INDEX IF EXISTS idx_buildings_3d_tile")
    
    # 2. Bulk-Import OHNE Index-Overhead
    print("[IMPORT] Importing buildings...")
    for tile in tiles:
        bulk_insert(tile)  # Bestehende Funktion
    
    # 3. Index am Ende erstellen (einmalig, schnell)
    print("[OPTIMIZE] Creating indexes...")
    conn.execute("""
        CREATE INDEX idx_buildings_3d_coords 
        ON buildings_3d(center_e, center_n)
    """)
    conn.execute("""
        CREATE INDEX idx_buildings_3d_tile 
        ON buildings_3d(tile_id)
    """)
    
    conn.close()
    print("[OPTIMIZE] Indexes created successfully")
```

### Task 4: Prepared Statements wiederverwenden

```python
# building_3d_service.py

class Building3DService:
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._prepared_insert = None
    
    def bulk_save(self, buildings: list[dict]) -> int:
        """Bulk-Insert mit wiederverwendetem Prepared Statement."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Prepared Statement nur einmal erstellen
            if self._prepared_insert is None:
                self._prepared_insert = """
                    INSERT OR REPLACE INTO buildings_3d 
                    (egid, polygon, traufhoehe_m, firsthoehe_m, 
                     gebaeudehoehe_m, area_m2, perimeter_m,
                     center_e, center_n, tile_id, imported_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            
            # Batch-Insert
            data = [self._building_to_tuple(b) for b in buildings]
            cursor.executemany(self._prepared_insert, data)
            conn.commit()
        
        return len(buildings)
```

### Task 5: Connection Pooling (optional)

```python
# building_3d_service.py

from contextlib import contextmanager
from threading import local

class Building3DService:
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = local()
    
    @contextmanager
    def _get_connection(self):
        """Thread-lokale Connection für bessere Performance."""
        
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None  # Autocommit für bessere Control
            )
            self._setup_connection(self._local.conn)
        
        try:
            yield self._local.conn
        except Exception:
            self._local.conn.rollback()
            raise
```

## A.3 Performance nach SQLite-Optimierung

| Phase | Vorher | Nachher | Verbesserung |
|-------|--------|---------|--------------|
| Bulk-Insert 7000 Gebäude | ~30s | ~10s | **3x** |
| Index-Erstellung | (während Insert) | ~2s (am Ende) | **15x** |
| Gesamtzeit 1 Tile | ~70s | ~45s | **1.6x** |
| Gesamtzeit 20 Tiles (4 Worker) | ~400s | ~180s | **2.2x** |

---

# ANHANG B: DuckDB-Migration (Maximale Performance)

> **Status:** ✅ Implementiert (13.01.2026 16:30)
> **Ziel:** Maximale Performance + bessere Parallelität
> **Erreichter Speedup:** ~5x für Bulk-Import

## B.1 Warum DuckDB?

### Technologie-Vergleich

| Aspekt | SQLite | DuckDB |
|--------|--------|--------|
| **Optimiert für** | OLTP (viele kleine Transaktionen) | OLAP (Analytics, Bulk) |
| **Parallelität** | Single-Writer | Multi-Threaded |
| **Bulk-Insert** | ~500-1000 rows/s | ~50'000 rows/s |
| **Columnar Storage** | Nein | Ja |
| **Parquet-Support** | Nein (extern) | Native |
| **Spatial-Queries** | Langsam | Schnell (SIMD) |
| **Railway.app** | ✅ | ✅ (embedded) |

### Railway-Kompatibilität

DuckDB ist wie SQLite **embedded** – keine externe Datenbank nötig:

```bash
# Installation
pip install duckdb

# Keine zusätzlichen Services auf Railway!
# Persistenz über Volume: /app/data/building_3d.duckdb
```

## B.2 TODO-Liste DuckDB-Migration

| # | Task | Beschreibung | Status |
|---|------|--------------|--------|
| 1 | Dependencies | `pip install duckdb` | ✅ |
| 2 | Schema erstellen | `building_3d.duckdb` mit optimiertem Schema | ✅ |
| 3 | Service anpassen | `building_3d_service.py` Dual-Mode (SQLite/DuckDB) | ✅ |
| 4 | Feature-Flag | DuckDB ist Default (SQLite mit `USE_DUCKDB=false`) | ✅ |
| 5 | INSERT OR REPLACE | Funktioniert für beide Engines (DuckDB ≥0.8) | ✅ |
| 6 | Tests | Bulk-Save, Single-Save, Update getestet | ✅ |

**Hinweis:** Parquet-Pipeline wurde nicht implementiert - `INSERT OR REPLACE` direkt ist ausreichend schnell.

## B.3 Migrations-Anleitung

### Schritt 1: Dependencies

```bash
# requirements.txt
duckdb>=0.9.0
pyarrow>=14.0.0
```

### Schritt 2: Schema erstellen

```python
# building_3d_service.py - Neue DuckDB-Version

import duckdb
from pathlib import Path

class Building3DServiceDuckDB:
    """DuckDB-basierter Building Service."""
    
    def __init__(self, db_path: str = "data/building_3d.duckdb"):
        self.db_path = Path(db_path)
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Schema erstellen falls nicht vorhanden."""
        
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS buildings_3d (
                    egid INTEGER PRIMARY KEY,
                    polygon JSON,           -- Native JSON-Typ!
                    traufhoehe_m DOUBLE,
                    firsthoehe_m DOUBLE,
                    gebaeudehoehe_m DOUBLE,
                    area_m2 DOUBLE,
                    perimeter_m DOUBLE,
                    center_e DOUBLE,
                    center_n DOUBLE,
                    tile_id VARCHAR,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source VARCHAR
                )
            """)
            
            # Spatial Index (R-Tree äquivalent)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_coords 
                ON buildings_3d(center_e, center_n)
            """)
```

### Schritt 3: Bulk-Import mit Parquet-Pipeline

```python
# tile_import_duckdb.py

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import fiona
from shapely.geometry import shape

def parse_tile_to_parquet(gdb_path: str, output_dir: str, tile_id: str) -> str:
    """
    Parse GDB → Parquet (parallelisierbar, kein DB-Lock).
    
    Returns: Pfad zur Parquet-Datei
    """
    
    buildings = []
    
    with fiona.open(gdb_path, layer="Building") as src:
        for feature in src:
            geom = shape(feature["geometry"])
            props = feature["properties"]
            
            buildings.append({
                "egid": int(props.get("EGID", 0)),
                "polygon": list(geom.exterior.coords),
                "traufhoehe_m": props.get("TRAUFHOEHE"),
                "firsthoehe_m": props.get("FIRSTHOEHE"),
                "gebaeudehoehe_m": props.get("GEBAEUDEHOEHE"),
                "area_m2": geom.area,
                "perimeter_m": geom.length,
                "center_e": geom.centroid.x,
                "center_n": geom.centroid.y,
                "tile_id": tile_id,
                "source": "swissBUILDINGS3D"
            })
    
    # Als Parquet speichern (extrem schnell)
    output_path = Path(output_dir) / f"{tile_id}.parquet"
    table = pa.Table.from_pylist(buildings)
    pq.write_table(table, output_path, compression="snappy")
    
    return str(output_path)


def import_parquets_to_duckdb(parquet_dir: str, db_path: str):
    """
    Alle Parquet-Dateien → DuckDB (ein Befehl!).
    
    DuckDB kann Parquet nativ lesen und parallelisiert automatisch.
    """
    
    with duckdb.connect(db_path) as conn:
        # Glob-Pattern für alle Parquets
        conn.execute(f"""
            INSERT INTO buildings_3d 
            SELECT * FROM read_parquet('{parquet_dir}/*.parquet')
        """)
        
        # Statistik
        count = conn.execute("SELECT COUNT(*) FROM buildings_3d").fetchone()[0]
        print(f"[DUCKDB] {count} buildings imported")


def parallel_import(tile_paths: list[tuple[str, str]], 
                    parquet_dir: str,
                    db_path: str,
                    workers: int = 4):
    """
    Kompletter Import-Prozess mit maximaler Parallelität.
    
    Phase 1: Tiles → Parquet (parallel, kein DB-Lock)
    Phase 2: Parquets → DuckDB (ein Befehl)
    """
    
    Path(parquet_dir).mkdir(parents=True, exist_ok=True)
    
    # Phase 1: Parallel Parsing (kein DB-Bottleneck!)
    print(f"[PHASE 1] Parsing {len(tile_paths)} tiles with {workers} workers...")
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(parse_tile_to_parquet, gdb_path, parquet_dir, tile_id)
            for gdb_path, tile_id in tile_paths
        ]
        
        for future in futures:
            parquet_path = future.result()
            print(f"  → {parquet_path}")
    
    # Phase 2: Bulk-Load (DuckDB parallelisiert intern)
    print(f"[PHASE 2] Loading parquets into DuckDB...")
    import_parquets_to_duckdb(parquet_dir, db_path)
    
    print("[DONE] Import complete!")
```

### Schritt 4: Query-Anpassungen

```python
# building_3d_service.py - Query-Methoden

class Building3DServiceDuckDB:
    
    def get_by_egid(self, egid: int) -> dict | None:
        """Einzelnes Gebäude laden."""
        
        with duckdb.connect(str(self.db_path), read_only=True) as conn:
            result = conn.execute("""
                SELECT * FROM buildings_3d WHERE egid = ?
            """, [egid]).fetchone()
            
            if result:
                return self._row_to_dict(result)
            return None
    
    def get_neighbors(self, center_e: float, center_n: float, 
                      radius_m: float, exclude_egids: list[int] = None) -> list[dict]:
        """
        Nachbarn im Radius finden.
        
        DuckDB nutzt automatisch den Index und SIMD für schnelle Filterung.
        """
        
        exclude_clause = ""
        params = [center_e, radius_m, center_e, center_n, radius_m, center_n, radius_m]
        
        if exclude_egids:
            placeholders = ",".join(["?" for _ in exclude_egids])
            exclude_clause = f"AND egid NOT IN ({placeholders})"
            params.extend(exclude_egids)
        
        with duckdb.connect(str(self.db_path), read_only=True) as conn:
            results = conn.execute(f"""
                SELECT * FROM buildings_3d
                WHERE center_e BETWEEN ? - ? AND ? + ?
                  AND center_n BETWEEN ? - ? AND ? + ?
                  {exclude_clause}
            """, params).fetchall()
            
            return [self._row_to_dict(r) for r in results]
    
    def get_buildings_in_bbox(self, west: float, south: float, 
                               east: float, north: float) -> list[dict]:
        """Gebäude in Bounding-Box (für Tile-basierte Abfragen)."""
        
        with duckdb.connect(str(self.db_path), read_only=True) as conn:
            results = conn.execute("""
                SELECT * FROM buildings_3d
                WHERE center_e BETWEEN ? AND ?
                  AND center_n BETWEEN ? AND ?
            """, [west, east, south, north]).fetchall()
            
            return [self._row_to_dict(r) for r in results]
```

### Schritt 5: Environment-Switch

```python
# config.py (Stand 13.01.2026 17:45)

import os

# DuckDB ist DEFAULT - nur mit USE_DUCKDB=false wird SQLite verwendet
USE_DUCKDB = os.getenv("USE_DUCKDB", "true").lower() != "false"

# Service-Factory
def get_building_3d_connection(read_only: bool = False):
    """Factory für DB-Connection (DuckDB default, SQLite fallback)."""
    if USE_DUCKDB:
        import duckdb
        return duckdb.connect(str(DUCKDB_PATH), read_only=read_only)
    else:
        import sqlite3
        return sqlite3.connect(str(BUILDING_3D_DB_PATH))
```

## B.4 Performance-Vergleich

### Bulk-Import (20 Tiles, ~140'000 Gebäude)

| Metrik | SQLite (optimiert) | DuckDB | Speedup |
|--------|-------------------|--------|---------|
| Parse → DB | 180s | 35s | **5x** |
| Parallelität | 4 Worker (DB-Limit) | 8+ Worker | **2x** |
| RAM-Peak | ~400MB | ~200MB | **2x** |
| Disk I/O | Viele kleine Writes | Bulk-Write | **10x** |

### Query-Performance

| Query | SQLite | DuckDB | Speedup |
|-------|--------|--------|---------|
| `get_by_egid` | ~1ms | ~0.5ms | 2x |
| `get_neighbors(5m)` | ~5ms | ~1ms | **5x** |
| `get_neighbors(100m)` | ~50ms | ~5ms | **10x** |
| `count(*)` | ~100ms | ~2ms | **50x** |

## B.5 Rollback-Plan

Falls DuckDB Probleme macht:

```bash
# 1. Feature-Flag deaktivieren
export USE_DUCKDB=false

# 2. SQLite-DB verwenden (bleibt parallel erhalten)
# building_3d.duckdb ist weiterhin da (oder .db bei SQLite-Modus)

# 3. Neustart
railway up
```

---

## Geschätzte Zeiten (nach Optimierung)

| Region | Tiles | SQLite (optimiert) | DuckDB |
|--------|-------|-------------------|--------|
| Bern Stadt | 20 | ~3 min | **~40s** |
| Kanton Bern | 200 | ~30 min | **~6 min** |
| Ganze Schweiz | 800 | ~2 h | **~25 min** |

---

## Empfehlung

### Kurzfristig (diese Woche)

→ **SQLite-Optimierungen (Anhang A)** implementieren
- Aufwand: 2-4 Stunden
- Speedup: ~2-3x
- Risiko: Minimal

### Mittelfristig (nächste 2 Wochen)

→ **DuckDB-Migration (Anhang B)** durchführen
- Aufwand: 4-8 Stunden
- Speedup: ~5-10x
- Risiko: Gering (Feature-Flag + Rollback)

### Entscheidungskriterien

| Wenn... | Dann... |
|---------|---------|
| Nur Bern-Region deployen | SQLite-Optimierung reicht |
| Ganze Schweiz deployen | DuckDB empfohlen |
| Häufige inkrementelle Updates | DuckDB empfohlen |
| Minimaler Änderungsaufwand | SQLite-Optimierung |

---

## Reset-Prozedur

Bei Problemen: **ALLE** Caches zusammen löschen + Backend neu starten!

```bash
# 1. Backend stoppen (Windows)
taskkill /F /IM python.exe

# 2. ALLE Caches löschen (WICHTIG: zusammen!)
rm backend/app/data/building_3d.duckdb  # oder .db bei SQLite-Modus
rm backend/app/data/tiles.db
rm -rf backend/app/data/tiles/
rm -rf backend/app/data/parquet/        # NEU: Parquet-Cache

# 3. Backend neu starten
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

---

---

# ANHANG C: Optimale Parallelisierungs-Architektur (NEU)

> **Status:** 📋 Geplant (Stand 13.01.2026 20:00)
> **Ziel:** Maximale Performance durch 3-Ebenen-Parallelisierung + Parquet-Pipeline
> **Erwarteter Speedup:** 10-15x gegenüber aktuellem Stand

## C.1 Parallelisierungs-Ebenen

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PARALLELISIERUNGS-EBENEN                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  EBENE 1: Layer-Parallelisierung (innerhalb eines Tiles)                │
│  ════════════════════════════════════════════════════════               │
│  Pro Tile werden 3 Layer GLEICHZEITIG geparst:                          │
│                                                                         │
│  ┌────────────────────┐                                                 │
│  │      Tile A        │                                                 │
│  │  ┌──────────────┐  │                                                 │
│  │  │ Building     │──┼──► parquet/buildings/tile_a.parquet             │
│  │  │ (40-70s)     │  │                                                 │
│  │  └──────────────┘  │                                                 │
│  │  ┌──────────────┐  │    ⎫                                            │
│  │  │ Roof_solid   │──┼──► parquet/roofs/tile_a.parquet                 │
│  │  │ (10-20s)     │  │    ⎬ parallel (ThreadPool)                      │
│  │  └──────────────┘  │    ⎭                                            │
│  │  ┌──────────────┐  │                                                 │
│  │  │ Wall         │──┼──► parquet/walls/tile_a.parquet                 │
│  │  │ (20-30s)     │  │                                                 │
│  │  └──────────────┘  │                                                 │
│  └────────────────────┘                                                 │
│                                                                         │
│  Speedup Ebene 1: ~1.5-1.7x (begrenzt durch längsten Layer)             │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  EBENE 2: Tile-Parallelisierung (mehrere Tiles gleichzeitig)            │
│  ════════════════════════════════════════════════════════════           │
│                                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                       │
│  │ Tile A  │ │ Tile B  │ │ Tile C  │ │ Tile D  │   ... (N Workers)     │
│  │ Worker1 │ │ Worker2 │ │ Worker3 │ │ Worker4 │                       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                       │
│       │          │          │          │                               │
│       └──────────┴────┬─────┴──────────┘                               │
│                       ▼                                                 │
│              parquet/*.parquet (kein DB-Lock!)                          │
│                                                                         │
│  Speedup Ebene 2: ~3-4x (bei 4 Workern)                                 │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  EBENE 3: Parquet-Pipeline (eliminiert DB-Bottleneck)                   │
│  ══════════════════════════════════════════════════════                 │
│                                                                         │
│  PHASE 1: Parse → Parquet (parallel, KEIN DB-Lock!)                     │
│                                                                         │
│  Worker 1 ──► parquet/buildings/tile_a.parquet                          │
│  Worker 2 ──► parquet/buildings/tile_b.parquet                          │
│  Worker 3 ──► parquet/buildings/tile_c.parquet                          │
│  Worker 4 ──► parquet/buildings/tile_d.parquet                          │
│                                                                         │
│  PHASE 2: Parquet → DuckDB (ein Befehl, ~5-10s!)                        │
│                                                                         │
│  DuckDB: INSERT INTO buildings_3d                                       │
│          SELECT * FROM read_parquet('parquet/buildings/*.parquet')      │
│                                                                         │
│  Speedup Ebene 3: ~2-3x (eliminiert Write-Contention)                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## C.2 Kombinierter Speedup

| Optimierung | Einzeln | Kumulativ | Status |
|-------------|---------|-----------|--------|
| **Baseline (aktuell)** | 1x | 1x | ✅ |
| + Layer-Parallel | 1.5x | 1.5x | 📋 TODO |
| + Tile-Parallel (4 Worker) | 3.5x | 5x | ✅ Teilweise |
| + Parquet-Pipeline | 2x | **10x** | 📋 TODO |
| + Download-Parallel | 1.5x | **15x** | 📋 TODO |

## C.3 Das DB-Contention Problem

```
AKTUELL (ohne Parquet-Pipeline):
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  Worker 1: Parse ████████████ → DB Write ▓▓▓▓ (WARTET auf Lock)         │
│  Worker 2: Parse ████████████ → DB Write ▓▓▓▓ (WARTET auf Lock)         │
│  Worker 3: Parse ████████████ → DB Write ████ (HAT Lock)                │
│  Worker 4: Parse ████████████ → DB Write ▓▓▓▓ (WARTET auf Lock)         │
│                                                                         │
│  → Alle wollen gleichzeitig in DuckDB schreiben = BOTTLENECK!           │
│  → Speedup begrenzt auf ~3-4x egal wie viele Worker                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

MIT PARQUET-PIPELINE:
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  PHASE 1: Parallel Parsing → Parquet (KEIN Lock, KEIN Warten!)          │
│                                                                         │
│  Worker 1: Parse ████ → parquet/tile_a.parquet ✓                        │
│  Worker 2: Parse ████ → parquet/tile_b.parquet ✓                        │
│  Worker 3: Parse ████ → parquet/tile_c.parquet ✓                        │
│  Worker 4: Parse ████ → parquet/tile_d.parquet ✓                        │
│  Worker 5: Parse ████ → parquet/tile_e.parquet ✓                        │
│  Worker 6: Parse ████ → parquet/tile_f.parquet ✓                        │
│  ...                                                                    │
│                                                                         │
│  PHASE 2: Bulk Load (EIN Befehl, ~5-10s für 100'000 Gebäude!)           │
│                                                                         │
│  DuckDB: INSERT INTO ... SELECT * FROM 'parquet/*.parquet'              │
│          ████████████████ FERTIG                                        │
│                                                                         │
│  → Perfekte Skalierung: Mehr Worker = Linear schneller                  │
│  → Speedup: 8-15x je nach Worker-Anzahl                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## C.4 Optimale Architektur (Ziel)

```
┌─────────────────────────────────────────────────────────────────────────┐
│              OPTIMALE BATCH-IMPORT ARCHITEKTUR                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PHASE 1: Paralleler Download (asyncio, 5 Connections)                  │
│  ═══════════════════════════════════════════════════                    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  asyncio.gather() mit Semaphore(5)                          │       │
│  │                                                              │       │
│  │  Download Tile A ──┐                                         │       │
│  │  Download Tile B ──┤                                         │       │
│  │  Download Tile C ──┼──► tiles/{tile_id}.gdb.zip             │       │
│  │  Download Tile D ──┤    ~30s für 20 Tiles (statt 10 min)    │       │
│  │  Download Tile E ──┘                                         │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  PHASE 2: Paralleles Layer-Parsing → Parquet                            │
│  ═══════════════════════════════════════════════                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  ProcessPoolExecutor(max_workers=CPU_COUNT)                  │       │
│  │                                                              │       │
│  │  ┌─────────────────────────────────────────────────────┐    │       │
│  │  │ Worker 1: Tile A                                    │    │       │
│  │  │   ThreadPool(3):                                    │    │       │
│  │  │     Building ──► parquet/buildings/tile_a.pq        │    │       │
│  │  │     Roof     ──► parquet/roofs/tile_a.pq            │    │       │
│  │  │     Wall     ──► parquet/walls/tile_a.pq            │    │       │
│  │  └─────────────────────────────────────────────────────┘    │       │
│  │  ┌─────────────────────────────────────────────────────┐    │       │
│  │  │ Worker 2: Tile B                                    │    │       │
│  │  │   ThreadPool(3): [Building | Roof | Wall]           │    │       │
│  │  └─────────────────────────────────────────────────────┘    │       │
│  │  ...                                                        │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  PHASE 3: DuckDB Bulk Load (ein Befehl pro Tabelle)                     │
│  ═════════════════════════════════════════════════                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  DuckDB (multi-threaded, SIMD-optimiert):                    │       │
│  │                                                              │       │
│  │  INSERT INTO buildings_3d                                    │       │
│  │    SELECT * FROM read_parquet('parquet/buildings/*.pq')      │       │
│  │    → ~5s für 50'000 Gebäude                                  │       │
│  │                                                              │       │
│  │  INSERT INTO building_roofs                                  │       │
│  │    SELECT * FROM read_parquet('parquet/roofs/*.pq')          │       │
│  │    → ~2s für 50'000 Dächer                                   │       │
│  │                                                              │       │
│  │  INSERT INTO building_walls                                  │       │
│  │    SELECT * FROM read_parquet('parquet/walls/*.pq')          │       │
│  │    → ~3s für 50'000 Wände                                    │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  PHASE 4: Cleanup                                                       │
│  ═════════════════                                                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  rm -rf tiles/          # GDB-Dateien (nicht mehr benötigt)  │       │
│  │  rm -rf parquet/        # Parquet-Cache (in DB geladen)      │       │
│  │  UPDATE tiles SET local_path = NULL WHERE imported = 1       │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## C.5 Performance-Schätzungen

### Pro Tile (Vergleich)

| Phase | Aktuell | Mit Optimierung | Speedup |
|-------|---------|-----------------|---------|
| Download | ~30s | ~30s | 1x |
| Parse Building | ~50s | ~50s | 1x |
| Parse Roof | ~15s | parallel | - |
| Parse Wall | ~25s | parallel | - |
| **Parse Total** | **~90s** | **~50s** | **1.8x** |
| DB Write | ~10s | ~0s (Parquet) | ∞ |
| **Tile Total** | **~130s** | **~80s** | **1.6x** |

### Batch (20 Tiles, ~3000 Gebäude)

| Szenario | Zeit | Speedup |
|----------|------|---------|
| Aktuell (sequentiell) | ~45 min | 1x |
| + Tile-Parallel (4 Worker) | ~12 min | 3.8x |
| + Layer-Parallel | ~8 min | 5.6x |
| + Parquet-Pipeline | **~3 min** | **15x** |

### Grosser Batch (200 Tiles, Kanton Bern)

| Szenario | Zeit | Speedup |
|----------|------|---------|
| Aktuell | ~7 Stunden | 1x |
| Optimal (8 Worker) | **~25-30 min** | **14-17x** |

## C.6 Implementierungs-TODO

| # | Task | Datei | Aufwand | Priorität |
|---|------|-------|---------|-----------|
| **C.1** | Layer-Parallel Parser | `tile_prefetch.py` | 1h | 🔴 Hoch |
| **C.2** | Parquet-Writer pro Layer | `parquet_writer.py` (NEU) | 2h | 🔴 Hoch |
| **C.3** | DuckDB Bulk-Load Funktion | `building_3d_service.py` | 1h | 🔴 Hoch |
| **C.4** | Import-Script anpassen | `import_tiles.py` | 2h | 🔴 Hoch |
| **C.5** | Paralleler Download | `import_tiles.py` | 1h | 🟡 Mittel |
| **C.6** | Progress-Tracking | `import_tiles.py` | 30min | 🟢 Nice-to-have |
| **C.7** | Cleanup-Integration | `tile_prefetch.py` | 30min | 🟢 Nice-to-have |
| **C.8** | **Alle 7 Indexes deferred** | `building_3d_service.py` | 30min | ✅ 14.01.2026 |

> **C.8 IMPLEMENTIERT (14.01.2026 00:30):** `drop_indexes()` und `create_indexes()` behandeln
> jetzt ALLE 7 Indexes (vorher nur 2). Beide Funktionen iterieren durch die Index-Liste
> mit Error-Handling und Logging.

**Geschätzter Gesamtaufwand:** 9-11 Stunden

## C.7 Neue Dateien

```
backend/
├── app/
│   └── services/
│       └── parquet_writer.py      # NEU: Parquet-Export pro Layer
└── scripts/
    └── batch/
        ├── import_tiles.py        # Angepasst: Parquet-Pipeline
        └── parallel_parser.py     # NEU: Layer-Parallelisierung
```

## C.8 Parquet-Schema (für DuckDB Bulk-Load)

### buildings.parquet

```python
schema = pa.schema([
    ('egid', pa.int64()),
    ('polygon', pa.string()),           # JSON-String
    ('traufhoehe_m', pa.float64()),
    ('firsthoehe_m', pa.float64()),
    ('gebaeudehoehe_m', pa.float64()),
    ('area_m2', pa.float64()),
    ('perimeter_m', pa.float64()),
    ('center_e', pa.float64()),
    ('center_n', pa.float64()),
    ('tile_id', pa.string()),
    ('objektart', pa.string()),
    ('name_komplett', pa.string()),
    ('gebaeude_nutzung', pa.string()),
    ('gebaeudeeinheit', pa.string()),
    ('roof_form', pa.string()),
    ('roof_form_confidence', pa.float64()),
    ('roof_orientation', pa.string()),
])
```

### roofs.parquet

```python
schema = pa.schema([
    ('gebaeudeeinheit', pa.string()),
    ('egid', pa.string()),
    ('dach_min', pa.float64()),
    ('dach_max', pa.float64()),
    ('roof_form', pa.string()),
    ('roof_angle_deg', pa.float64()),
    ('roof_orientation', pa.string()),
    ('roof_form_confidence', pa.float64()),
    ('z_levels', pa.string()),          # JSON-String
    ('calculation_method', pa.string()),
])
```

### walls.parquet

```python
schema = pa.schema([
    ('gebaeudeeinheit', pa.string()),
    ('egid', pa.string()),
    ('z_min', pa.float64()),
    ('z_max', pa.float64()),
    ('geometry_wkb', pa.binary()),      # WKB als Bytes
])
```

## C.9 Beispiel-Code: Optimaler Import

```python
# scripts/batch/import_tiles_optimized.py

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

async def import_region_optimized(region: str, workers: int = 4):
    """
    Optimierter Batch-Import mit 3-Ebenen-Parallelisierung.
    """

    # 1. Tile-Liste für Region ermitteln
    tiles = get_tiles_for_region(region)

    # 2. PHASE 1: Paralleler Download
    print(f"[PHASE 1] Downloading {len(tiles)} tiles...")
    await download_tiles_parallel(tiles, max_concurrent=5)

    # 3. PHASE 2: Paralleles Parsing → Parquet
    print(f"[PHASE 2] Parsing with {workers} workers...")
    parquet_dir = Path("parquet")
    parquet_dir.mkdir(exist_ok=True)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(parse_tile_all_layers, tile_id, gdb_path, parquet_dir)
            for tile_id, gdb_path in tiles
        ]
        for future in as_completed(futures):
            tile_id, counts = future.result()
            print(f"  ✓ {tile_id}: {counts}")

    # 4. PHASE 3: DuckDB Bulk-Load
    print("[PHASE 3] Loading into DuckDB...")
    load_parquets_to_duckdb(parquet_dir)

    # 5. PHASE 4: Cleanup
    print("[PHASE 4] Cleanup...")
    cleanup_after_import(tiles, parquet_dir)

    print("[DONE] Import complete!")


def parse_tile_all_layers(tile_id: str, gdb_path: Path, parquet_dir: Path):
    """
    Parst alle 3 Layer PARALLEL und schreibt Parquet-Dateien.
    """

    # ThreadPool für Layer-Parallelisierung
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_buildings = executor.submit(
            parse_and_write_parquet,
            gdb_path, "Building_solid", parquet_dir / "buildings" / f"{tile_id}.pq"
        )
        future_roofs = executor.submit(
            parse_and_write_parquet,
            gdb_path, "Roof_solid", parquet_dir / "roofs" / f"{tile_id}.pq"
        )
        future_walls = executor.submit(
            parse_and_write_parquet,
            gdb_path, "Wall", parquet_dir / "walls" / f"{tile_id}.pq"
        )

        # Auf alle warten
        b_count = future_buildings.result()
        r_count = future_roofs.result()
        w_count = future_walls.result()

    return tile_id, {"buildings": b_count, "roofs": r_count, "walls": w_count}


def load_parquets_to_duckdb(parquet_dir: Path):
    """
    Lädt alle Parquet-Dateien in DuckDB (ein Befehl pro Tabelle).
    """

    conn = duckdb.connect("app/data/building_3d.duckdb")

    # Buildings
    conn.execute(f"""
        INSERT INTO buildings_3d
        SELECT * FROM read_parquet('{parquet_dir}/buildings/*.pq')
    """)

    # Roofs
    conn.execute(f"""
        INSERT INTO building_roofs
        SELECT * FROM read_parquet('{parquet_dir}/roofs/*.pq')
    """)

    # Walls
    conn.execute(f"""
        INSERT INTO building_walls
        SELECT * FROM read_parquet('{parquet_dir}/walls/*.pq')
    """)

    # has_3d_layers Flag setzen
    conn.execute("""
        UPDATE buildings_3d SET has_3d_layers = 1
        WHERE egid IN (SELECT DISTINCT egid FROM building_walls)
    """)

    conn.close()
```

---

## Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 14.01.2026 00:30 | 6.3 | **C.8 IMPLEMENTIERT:** `drop_indexes()` und `create_indexes()` behandeln jetzt ALLE 7 Indexes. Anhang A Task 3 auf ✅ gesetzt. |
| 14.01.2026 00:15 | 6.2 | **Index-Dokumentation:** Alle 7 Indexes dokumentiert (vorher nur 2). Warnung bei Anhang A Task 3 hinzugefügt. Neuer Task C.8 für vollständige Index-Implementierung. |
| 13.01.2026 21:30 | 6.1 | **Schema-Konsolidierung:** 3D-Layer-Tabellen verwenden jetzt `gebaeudeeinheit` als PRIMARY KEY (statt `id INTEGER`). DuckDB hat keine AUTOINCREMENT. Implementierungs-TODO aktualisiert. |
| 13.01.2026 20:00 | 6.0 | **ANHANG C: Optimale Parallelisierungs-Architektur:** 3-Ebenen-Parallelisierung (Layer, Tile, Parquet-Pipeline) dokumentiert. Performance-Schätzungen und Implementierungs-TODO erstellt. |
| 13.01.2026 18:00 | 5.0 | **All-Layer-Import Strategie:** Wall-Layer wird jetzt IMMER importiert (nicht on-demand). Tiles werden nach Import gelöscht. DB-Deployment Workflow für Railway dokumentiert. |
| 13.01.2026 17:45 | 4.1 | **DuckDB ist Default:** Kein `USE_DUCKDB=true` mehr nötig, SQLite-Fallback mit `USE_DUCKDB=false` |
| 13.01.2026 16:30 | 4.0 | **DuckDB-Migration abgeschlossen:** `building_3d.db` → `building_3d.duckdb` |
| 10.01.2026 | 3.1 | **Anhang A implementiert:** Task 1-5 in `building_3d_service.py` + `import_tiles.py` |
| 10.01.2026 | 3.0 | Anhang A (SQLite-Optimierung) + Anhang B (DuckDB-Migration) |
| 10.01.2026 | 2.1 | Fiona Streaming-Dokumentation erweitert |
| 09.01.2026 | 2.0 | Parallelisierungs-Architektur (OPT-003) |
| 09.01.2026 | 1.0 | Initiales Design |
