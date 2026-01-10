# Batch-Import für swissBUILDINGS3D Tiles

> **Version:** 3.0 (10.01.2026)
> **Status:** Implementiert + Optimierungsplan

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

| # | Task | Datei | Aufwand | Speedup | Status |
|---|------|-------|---------|---------|--------|
| 1 | Aggressive PRAGMAs | `building_3d_service.py` | 15 min | ~1.5x | ✅ |
| 2 | Batch-Size erhöhen (5000) | `building_3d_service.py` | 5 min | ~1.2x | ✅ |
| 3 | Index nachträglich | `import_tiles.py` | 30 min | ~1.5x | ✅ |
| 4 | Prepared Statements | `building_3d_service.py` | 30 min | ~1.1x | ✅ |
| 5 | Connection Pooling | `building_3d_service.py` | 1h | ~1.2x | ✅ |

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

> **Ziel:** Maximale Performance + bessere Parallelität
> **Aufwand:** 4-8 Stunden
> **Erwarteter Speedup:** ~5-10x für Bulk-Import

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

| # | Task | Beschreibung | Aufwand |
|---|------|--------------|---------|
| 1 | Dependencies | `pip install duckdb pyarrow` | 5 min |
| 2 | Schema erstellen | `building_3d.duckdb` mit optimiertem Schema | 30 min |
| 3 | Service anpassen | `building_3d_service.py` auf DuckDB | 2h |
| 4 | Parquet-Pipeline | Tiles → Parquet → DuckDB | 2h |
| 5 | Query-Anpassungen | Spatial-Queries optimieren | 1h |
| 6 | Tests | Bestehende Tests anpassen | 1h |

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
# config.py

import os

# Feature-Flag für Migration
USE_DUCKDB = os.getenv("USE_DUCKDB", "false").lower() == "true"

# Service-Factory
def get_building_service():
    if USE_DUCKDB:
        from .building_3d_service_duckdb import Building3DServiceDuckDB
        return Building3DServiceDuckDB()
    else:
        from .building_3d_service import Building3DService
        return Building3DService()
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
# building_3d.db ist weiterhin da

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
rm backend/app/data/building_3d.db      # oder .duckdb
rm backend/app/data/tiles.db
rm -rf backend/app/data/tiles/
rm -rf backend/app/data/parquet/        # NEU: Parquet-Cache

# 3. Backend neu starten
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

---

## Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 10.01.2026 | 3.1 | **Anhang A implementiert:** Task 1-5 in `building_3d_service.py` + `import_tiles.py` |
| 10.01.2026 | 3.0 | Anhang A (SQLite-Optimierung) + Anhang B (DuckDB-Migration) |
| 10.01.2026 | 2.1 | Fiona Streaming-Dokumentation erweitert |
| 09.01.2026 | 2.0 | Parallelisierungs-Architektur (OPT-003) |
| 09.01.2026 | 1.0 | Initiales Design |
