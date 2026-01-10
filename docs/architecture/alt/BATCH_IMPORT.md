# Batch-Import für swissBUILDINGS3D Tiles

> **Version:** 2.0 (09.01.2026)
> **Status:** Implementiert

---

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

### Datenfluss

```
┌─────────────────────────────────────────────────────────────────┐
│                    BATCH IMPORT PROZESS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. DISCOVERY (STAC API)                                        │
│  ════════════════════════                                       │
│  GET /api/stac/v0.9/collections/ch.swisstopo.swissbuildings3d   │
│       │                                                         │
│       ▼                                                         │
│  Liste aller verfügbaren Tiles mit:                             │
│  - tile_id, download_url, datetime, bbox                        │
│                                                                 │
│  2. DIFF (tiles.db)                                             │
│  ══════════════════                                             │
│  Vergleich: STAC-Tiles vs. lokale tiles.db                      │
│       │                                                         │
│       ├── NEU: Tile nicht in DB                                 │
│       ├── UPDATE: stac_datetime > downloaded_at                 │
│       └── AKTUELL: Keine Änderung                               │
│                                                                 │
│  3. DOWNLOAD (parallel)                                         │
│  ══════════════════════                                         │
│  asyncio.gather() mit Semaphore (max 5 parallel)                │
│       │                                                         │
│       ▼                                                         │
│  tiles/{tile_id}.gdb + tiles.db UPDATE                          │
│                                                                 │
│  4. IMPORT (fiona streaming)                                    │
│  ═══════════════════════════                                    │
│  Für jedes neue/geänderte Tile:                                 │
│  - GDB parsen mit fiona (streaming, kein DataFrame)             │
│  - building_3d.db befüllen (bulk insert)                        │
│  - tiles.db: import_status = 'imported'                         │
│                                                                 │
│  5. CLEANUP                                                     │
│  ═════════                                                      │
│  - Verwaiste Tiles entfernen (in DB aber nicht in STAC)         │
│  - Temporäre Dateien löschen                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Komponenten

| Komponente | Datei | Zweck |
|------------|-------|-------|
| **Import-Skript** | `scripts/import_tiles.py` | CLI für Batch-Import |
| **Tile-Cache** | `tile_cache.py` | Speichert GDB-Dateien + Metadaten |
| **Tile-Prefetch** | `tile_prefetch.py` | Parsed GDB → building_3d.db |
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

### building_3d.db (Gebäudedaten)

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
    imported_at TIMESTAMP,
    source TEXT
);

CREATE INDEX idx_buildings_3d_coords ON buildings_3d(center_e, center_n);
CREATE INDEX idx_buildings_3d_tile ON buildings_3d(tile_id);
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

### Implementierung

```python
# tile_prefetch.py - _parse_all_buildings_from_gdb()

import fiona
from shapely.geometry import shape

# 1. Layer finden (GDB kann mehrere Layer haben)
layers = fiona.listlayers(gdb_path)
target_layer = None
for layer in layers:
    if 'building' in layer.lower() and 'solid' in layer.lower():
        target_layer = layer
        break

# 2. Streaming-Iteration über alle Features
with fiona.open(gdb_path, layer=target_layer) as src:
    for feature in src:
        props = feature['properties']
        egid = props.get('EGID')

        # Geometrie mit shapely.geometry.shape() konvertieren
        # (Fiona-Dict → Shapely-Objekt)
        geom = shape(feature['geometry'])

        # Höhen aus Properties extrahieren
        terrain = props.get('GELAENDEPUNKT')
        dach_min = props.get('DACH_MIN')
        dach_max = props.get('DACH_MAX')

        # 3D → 2D Projektion (nur X,Y, kein Z)
        if hasattr(geom, 'exterior'):
            polygon = [[c[0], c[1]] for c in geom.exterior.coords]

        # Zentroid berechnen
        center_e = round(geom.centroid.x, 1)
        center_n = round(geom.centroid.y, 1)
```

### swissBUILDINGS3D GDB-Struktur

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| `EGID` | Integer | Eidg. Gebäudeidentifikator |
| `GELAENDEPUNKT` | Float | Terrain-Höhe (m ü.M.) |
| `DACH_MIN` | Float | Traufhöhe absolut (m ü.M.) |
| `DACH_MAX` | Float | Firsthöhe absolut (m ü.M.) |
| `GESAMTHOEHE` | Float | Gebäudehöhe (m) |
| `geometry` | MultiPolygonZ | 3D-Polygon |

**Höhenberechnung:**
```python
traufhoehe_m = DACH_MIN - GELAENDEPUNKT  # Relative Traufhöhe
firsthoehe_m = DACH_MAX - GELAENDEPUNKT  # Relative Firsthöhe
```

### Performance-Logging

```
[PREFETCH] GDB-Parsing: 7197 Gebäude | 70000ms (9.8ms/Gebäude) | Methode: fiona_direct
```

### Dependencies

```
# requirements.txt
fiona>=1.9.0      # GDB/Shapefile Reader (GDAL-basiert)
shapely>=2.0.0    # Geometrie-Operationen (Centroid, Area, etc.)
```

> **Hinweis:** Fiona benötigt GDAL. Auf Windows am einfachsten via `pip install fiona`
> (bringt GDAL-Binaries mit). Auf Linux: `apt install libgdal-dev` zuerst.

---

## CLI-Verwendung

```bash
# Ganze Schweiz importieren (~800 Tiles, ~8h)
python scripts/import_tiles.py --all

# Nur Region Bern (~20 Tiles, ~10min)
python scripts/import_tiles.py --region bern

# Bounding Box (LV95)
python scripts/import_tiles.py --bbox 2590000,1190000,2610000,1210000

# Nur neue/geänderte Tiles
python scripts/import_tiles.py --update

# Einzelnes Tile
python scripts/import_tiles.py --tile 1322-21

# Import-Status anzeigen
python scripts/import_tiles.py --status

# Fehlgeschlagene neu versuchen
python scripts/import_tiles.py --retry-failed

# Parallelität einstellen (default: 5)
python scripts/import_tiles.py --all --parallel 10
```

### Regionen

| Region | BBox (LV95) | Tiles | Gebäude |
|--------|-------------|-------|---------|
| bern | 2585000,1195000,2615000,1215000 | ~20 | ~50'000 |
| zurich | 2676000,1243000,2696000,1263000 | ~25 | ~80'000 |
| basel | 2607000,1262000,2627000,1272000 | ~10 | ~30'000 |
| genf | 2495000,1115000,2510000,1125000 | ~15 | ~40'000 |

---

## Optimierungen

### Implementiert

| ID | Optimierung | Speedup |
|----|-------------|---------|
| OPT-001 | egid_tile_index entfernt | 1.9x |
| OPT-002 | Fiona statt geopandas | 1.17x |
| **OPT-003** | **Parallel-Parsing (multiprocessing)** | **~3.5x** |

**Sequentiell:** 158.9s → 70.0s (2.2x schneller)
**Mit Parallelisierung:** ~20s pro Tile effektiv (~7x schneller als Original)

---

## Parallelisierungs-Architektur (OPT-003)

### Engpass-Analyse

```
Tile-Verarbeitung (pro Tile, ~7000 Gebäude):
─────────────────────────────────────────────
├── Fiona Disk-Read:     ~20% (I/O-bound)
├── Shapely Geometrie:   ~50% (CPU-bound) ← Hauptlast
├── SQLite INSERT:       ~25% (I/O-bound)
└── Python Overhead:     ~5%
```

| Engpass | Bei N Workern | Lösung |
|---------|---------------|--------|
| **CPU (Shapely)** | 1-4 Worker | multiprocessing.Pool |
| **SQLite Writer** | >6 Worker | Single Writer + Bulk-Insert |

### Producer-Consumer Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                   PARALLEL-PARSING                              │
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

### Speedup-Tabelle

| Szenario | Zeit (1 Tile) | Zeit (20 Tiles) | Speedup |
|----------|---------------|-----------------|---------|
| Sequentiell | 70s | 1400s (23min) | 1x |
| 4 Worker | 70s | ~400s (7min) | **~3.5x** |
| 8 Worker | 70s | ~350s (6min) | ~4x |

> Ab ~6 Workern wird SQLite zum Flaschenhals, nicht mehr das Parsing.

### SQLite-Optimierungen

```python
# WAL-Mode für bessere Parallelität
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA cache_size=-64000")  # 64MB Cache

# Bulk-Insert (1000 Rows pro Transaction)
cursor.executemany(INSERT_SQL, batch_of_1000)
conn.commit()
```

| Optimierung | Beschreibung | Speedup |
|-------------|--------------|---------|
| WAL-Mode | Write-Ahead Logging | ~1.5x |
| Batch-Insert | 1000+ Rows pro Transaction | ~2x |
| PRAGMA synchronous=NORMAL | Reduzierte fsync-Calls | ~1.3x |

### Implementierung

Siehe `scripts/import_tiles.py`:

```python
# Phase 1: Downloads (parallel mit asyncio)
async with httpx.AsyncClient() as client:
    download_tasks = [download_tile(tile, semaphore, client) for tile in tiles]
    results = await asyncio.gather(*download_tasks)

# Phase 2: Parsing (parallel mit multiprocessing)
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(parse_tile_worker, args): args[0] for args in tiles}
    for future in as_completed(futures):
        tile_id, buildings, duration, error = future.result()

# Phase 3: DB-Write (sequentiell, Bulk-Insert)
for tile_id, buildings in parsed_results:
    bulk_insert_buildings(buildings, tile_id)
```

---

## Server-Ausführung (Railway.app)

Der Batch-Import kann auch auf dem Server ausgeführt werden.

### Option 1: Railway CLI (One-Off Command)

```bash
# Via Railway CLI lokal
railway run python scripts/import_tiles.py --region bern --workers 2
```

| Aspekt | Details |
|--------|---------|
| **Max Worker** | 2 (shared CPU) |
| **Timeout** | 1h (Free/Hobby Plan) |
| **Persistenz** | Volume unter `/app/data` |

### Option 2: API-Endpoint (geplant)

```python
# Trigger Import
POST /api/v1/admin/import-tiles
{
  "region": "bern",      # oder "tile": "1332-22"
  "workers": 2,
  "background": true
}

# Status abfragen
GET /api/v1/admin/import-status
{
  "status": "running",
  "progress": "12/20 tiles",
  "buildings_imported": 45000
}
```

### Option 3: Scheduled Job (Cron)

```yaml
# railway.toml
[cron]
  schedule = "0 3 * * 0"  # Jeden Sonntag 3:00 Uhr
  command = "python scripts/import_tiles.py --update --workers 2"
```

### Empfehlung

| Usecase | Lösung |
|---------|--------|
| **Initiales Setup** | Lokal ausführen (schneller) |
| **Inkrementelle Updates** | Cron oder API-Endpoint |
| **Einzelne Tiles** | API-Endpoint |
| **Debugging** | Railway CLI |

---

## Geschätzte Zeiten

| Region | Tiles | Lokal (4 Worker) | Server (2 Worker) |
|--------|-------|------------------|-------------------|
| Bern Stadt | 20 | ~7 min | ~12 min |
| Kanton Bern | 200 | ~70 min | ~120 min |
| Ganze Schweiz | 800 | ~5 h | ~10 h |

---

## Reset-Prozedur

Bei Problemen: **ALLE** Caches zusammen loeschen + Backend neu starten!

```bash
# 1. Backend stoppen (Windows)
taskkill /F /IM python.exe
# oder: powershell -Command "Stop-Process -Name python -Force"

# 2. ALLE Caches loeschen (WICHTIG: zusammen!)
rm backend/app/data/building_3d.db
rm backend/app/data/tiles.db
rm -rf backend/app/data/tiles/

# 3. Backend neu starten
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**FALSCH:**
```bash
rm backend/app/data/building_3d.db  # Tiles bleiben, Prefetch laeuft nicht!
```

**Grund:** Singleton-Services werden beim Start initialisiert. Wenn `tiles.db` existiert aber `building_3d.db` waehrend der Laufzeit geloescht wird, bleibt der Service im alten Zustand (mit `_initialized = True`) und die Tabelle wird nicht neu erstellt.

---

## Progress-Output

```
[IMPORT] Discovering tiles from STAC API...
[IMPORT] Found 823 tiles for Switzerland
[IMPORT] Checking for updates...
[IMPORT] 12 new tiles, 3 updated tiles, 808 current

[DOWNLOAD] Tile 1322-21: Downloading... (15.2 MB)
[DOWNLOAD] Tile 1322-22: Downloading... (12.8 MB)
[DOWNLOAD] Tile 1322-21: Complete (2.3s)
[PREFETCH] Tile 1322-21: Parsing GDB...
[PREFETCH] Tile 1322-21: 4901 buildings | 49000ms (10.0ms/Geb.) | fiona_direct

Progress: [================----] 12/15 tiles (80%)
Buildings: 52,341 imported
Time: 12:34 elapsed, ~3:00 remaining
```

---

## Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 10.01.2026 | 2.1 | Fiona Streaming-Dokumentation erweitert |
| 09.01.2026 | 2.0 | Parallelisierungs-Architektur (OPT-003) |
| 09.01.2026 | 1.0 | Initiales Design |
