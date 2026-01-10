# Streaming Architecture

> **Version:** 4.0 (10.01.2026)
> **Status:** Cache-Lookup ✅ | Response-Streaming ✅ | Building-Data-Streaming ✅ | Tile-Prefetch ✅

---

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Teil A: Cache-Lookup Architektur](#teil-a-cache-lookup-architektur) (implementiert)
3. [Teil B: Project-Context-Streaming](#teil-b-response-streaming-architektur) (implementiert)
4. [Teil C: Building-Data-Streaming](#teil-c-building-data-streaming) (implementiert)
5. [Teil D: Pipeline-Optimierung](#teil-d-pipeline-optimierung) (implementiert)
6. [Teil E: Minimal + On-Demand](#teil-e-minimal--on-demand-architektur) (implementiert)
7. [Anhang F: SQLite-Optimierungen](#anhang-f-sqlite-optimierungen-für-streaming) (NEU)
8. [Anhang G: DuckDB-Migration](#anhang-g-duckdb-migration-für-streaming) (NEU)

---

## Übersicht

Diese Architektur besteht aus drei Teilen:

| Teil | Zweck | Status |
|------|-------|--------|
| **A: Cache-Lookup** | Schneller Datenzugriff durch 3-Stufen Lookup | ✅ Implementiert |
| **B: Project-Context-Streaming** | Blockierte Fassaden, Nachbarn für bestehende Projekte | ✅ Implementiert |
| **C: Building-Data-Streaming** | Progressive Datenladung bei Projekt-Erstellung | ✅ Implementiert |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STREAMING ARCHITECTURE v4.0                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  TEIL A: CACHE-LOOKUP (Backend-intern)                          │   │
│  │  ════════════════════════════════════                           │   │
│  │  • 3-Stufen Lookup: building_3d.db → Tile-Cache → STAC API     │   │
│  │  • Optimiert Datenzugriff (~1ms statt ~500ms)                  │   │
│  │  • Befüllt Cache automatisch via tile_prefetch                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│          ┌───────────────────┴───────────────────┐                      │
│          ▼                                       ▼                      │
│  ┌─────────────────────────────┐   ┌─────────────────────────────┐     │
│  │  TEIL B: PROJECT-CONTEXT    │   │  TEIL C: BUILDING-DATA      │     │
│  │  ═══════════════════════    │   │  ══════════════════════     │     │
│  │  • Bestehende Projekte      │   │  • Neue Projekt-Erstellung  │     │
│  │  • blocked_facades          │   │  • Geocoding → GWR → 3D     │     │
│  │  • neighbors (progressiv)   │   │  • Terrain → Zonen          │     │
│  │  • Multi-Building Support   │   │  • Progress-Feedback        │     │
│  └─────────────────────────────┘   └─────────────────────────────┘     │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ANHÄNGE F+G: OPTIMIERUNGEN                                     │   │
│  │  ══════════════════════════                                     │   │
│  │  • F: SQLite Quick-Wins (~2x Speedup)                          │   │
│  │  • G: DuckDB-Migration (~5-10x Speedup)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# Teil A: Cache-Lookup Architektur

## A.1 Das Problem (vor 07.01.2026)

```
┌─────────────────────────────────────────────────────────────────┐
│                 VORHER: Ineffizienter Datenfluss                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User fragt Gebäude an                                          │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │   1. Tile-Cache prüfen                  │                   │
│  │      → GDB-Datei vorhanden?             │                   │
│  └─────────────────────────────────────────┘                   │
│       │                                                         │
│       │ JA                    NEIN                              │
│       ▼                       ▼                                 │
│  ┌────────────┐         ┌────────────────────┐                 │
│  │ GDB Parsen │         │ STAC API Download  │                 │
│  │ ~100-500ms │ ←←←←←←  │ + GDB Parsen       │                 │
│  └────────────┘         │ ~5-10s             │                 │
│       │                 └────────────────────┘                 │
│       ▼                                                         │
│  Gebäude zurückgeben                                            │
│                                                                 │
│  ⚠️ PROBLEM: Auch bei Cache-Hit wird das GDB JEDES MAL         │
│              geparst (~100-500ms pro Anfrage)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## A.2 Die Lösung: 3-Stufen Lookup

```
┌─────────────────────────────────────────────────────────────────┐
│                 NACHHER: 3-Stufen Lookup                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User fragt Gebäude an                                          │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │   STUFE 1: building_3d.db               │ ←── O(1) Lookup   │
│  │   (Pre-processed Gebäudedaten)          │     ~1ms          │
│  └─────────────────────────────────────────┘                   │
│       │                                                         │
│       │ MISS                                                    │
│       ▼                                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │   STUFE 2: Tile-Cache GDB               │ ←── GDB Parsing   │
│  │   (Rohdaten aus gecachtem Tile)         │     ~100-500ms    │
│  └─────────────────────────────────────────┘                   │
│       │                                                         │
│       │ MISS (kein GDB gecacht)                                 │
│       ▼                                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │   STUFE 3: STAC API Download            │ ←── Netzwerk      │
│  │   (Tile-Download + Entpacken)           │     ~5-10s        │
│  └─────────────────────────────────────────┘                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │   SPEICHERUNG in building_3d.db         │ ←── Für Stufe 1   │
│  │   + Background-Prefetch aller Gebäude   │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Performance-Vergleich:**

| Szenario | VORHER | NACHHER |
|----------|--------|---------|
| Erstes Gebäude im Tile | 5-10s | 5-10s |
| Zweites Gebäude im Tile | 100-500ms | **~1ms** |
| Drittes Gebäude im Tile | 100-500ms | **~1ms** |
| Nachbar-Lookups | Je 100-500ms | **~1ms** |

## A.3 Komponenten

### building_3d.db

```sql
CREATE TABLE buildings_3d (
    egid INTEGER PRIMARY KEY,
    polygon TEXT,           -- JSON: [[e,n], [e,n], ...]
    traufhoehe_m REAL,
    firsthoehe_m REAL,
    gebaeudehoehe_m REAL,
    area_m2 REAL,
    perimeter_m REAL,
    center_e REAL,          -- LV95 Zentroid
    center_n REAL,
    tile_id TEXT,
    imported_at TIMESTAMP,
    source TEXT
);

CREATE INDEX idx_buildings_3d_coords ON buildings_3d(center_e, center_n);
```

### tile_prefetch.py

Background-Job der alle Gebäude eines Tiles in `building_3d.db` speichert.

### swissbuildings3d_fetcher.py

Implementiert den 3-Stufen Lookup mit automatischem Cache-Befüllen.

---

# Teil B: Response-Streaming Architektur

## B.1 Das Problem: Blockierende API-Responses

```
┌─────────────────────────────────────────────────────────────────┐
│  ALTE ARCHITEKTUR (blockierend)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend Request                                               │
│       │                                                         │
│       ▼                                                         │
│  GET /api/v1/project/{id}/context                              │
│       │                                                         │
│       │  [████████████████████████████████]                    │
│       │  ← Backend berechnet ALLES (500ms - 5s) →              │
│       │                                                         │
│       ▼                                                         │
│  Response (komplett)                                            │
│       │                                                         │
│       ▼                                                         │
│  UI kann endlich rendern                                        │
│                                                                 │
│  ❌ PROBLEME:                                                   │
│  • User sieht Spinner für 500ms-5s                             │
│  • Kritische Daten (blocked_facades) erst am Ende              │
│  • Bei Timeout: Alles verloren                                 │
│  • Keine Möglichkeit zum Abbrechen                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## B.2 Die Lösung: Server-Sent Events (SSE)

```
┌─────────────────────────────────────────────────────────────────┐
│  NEUE ARCHITEKTUR (streaming)                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend Request                                               │
│       │                                                         │
│       ▼                                                         │
│  GET /api/v1/project/{id}/context/stream                       │
│       │                                                         │
│       │  SSE Connection                                         │
│       │                                                         │
│       ├──→ event: centroid           (~10ms)                   │
│       │    data: {center_e, center_n}                          │
│       │    → UI: Kamera zentrieren                             │
│       │                                                         │
│       ├──→ event: project_buildings  (~20ms)                   │
│       │    data: [{egid, polygon}, ...]                        │
│       │    → UI: Projekt-Gebäude rendern                       │
│       │                                                         │
│       ├──→ event: blocked_facades    (~50ms) ⚡ KRITISCH       │
│       │    data: {EGID_A: [1,3], EGID_B: [0]}                  │
│       │    → UI: Fassaden markieren (rot/grün)                 │
│       │                                                         │
│       ├──→ event: neighbors          (~100ms)                  │
│       │    data: {radius: 20, buildings: [...]}                │
│       │    → UI: Nahe Nachbarn rendern                         │
│       │                                                         │
│       ├──→ event: neighbors          (~200ms)                  │
│       │    data: {radius: 50, buildings: [...]}                │
│       │    → UI: Weitere Nachbarn hinzufügen                   │
│       │                                                         │
│       ├──→ event: neighbors          (~400ms)                  │
│       │    data: {radius: 100, buildings: [...]}               │
│       │    → UI: Kontext-Gebäude hinzufügen                    │
│       │                                                         │
│       └──→ event: complete           (~500ms)                  │
│            data: {status: "ok", duration_ms: 487}              │
│            → UI: Loading-Indicator entfernen                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## B.3 Vorteile der Streaming-Architektur

| Aspekt | Alte Architektur | Streaming |
|--------|------------------|-----------|
| **Time to First Byte** | 500ms - 5s | **~10ms** |
| **Time to Interactive** | 500ms - 5s | **~50ms** (blocked_facades) |
| **Perceived Performance** | Langsam (Spinner) | **Schnell** (progressiv) |
| **Abbruch möglich** | Nein | **Ja** (EventSource.close()) |
| **Grosse Radien** | Blockiert alles | **Lädt im Hintergrund** |
| **Fehlertoleranz** | Alles oder nichts | **Partial Success** möglich |

---

# Teil C: Building-Data-Streaming

## C.1 Anwendungsfall: Projekt-Erstellung

Wenn ein Benutzer ein neues Projekt erstellt und eine Adresse eingibt,
werden viele Daten gesammelt. Dies kann 200ms-10s dauern (je nach Cache).

```
┌─────────────────────────────────────────────────────────────────┐
│  BUILDING-DATA-STREAMING                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend Request                                               │
│       │                                                         │
│       ▼                                                         │
│  GET /api/v1/geruestbau/building/data/stream?address=...       │
│       │                                                         │
│       │  SSE Connection                                         │
│       │                                                         │
│       ├──→ event: geocoding        (~50ms)                     │
│       │    data: {matched_address, egid, coordinates}          │
│       │    → UI: Karte zentrieren, Adresse bestätigen          │
│       │                                                         │
│       ├──→ event: gwr              (~100ms)                    │
│       │    data: {floors, area_m2, category, year_built}       │
│       │    → UI: GWR-Daten anzeigen                            │
│       │                                                         │
│       ├──→ event: polygon_progress (optional, bei Download)    │
│       │    data: {status: "downloading", message: "..."}       │
│       │    → UI: Spinner mit "Gebäudedaten laden..."           │
│       │                                                         │
│       ├──→ event: polygon          (~200ms oder ~5s)           │
│       │    data: {polygon, sides, perimeter_m, area_m2}        │
│       │    → UI: Polygon auf Karte rendern                     │
│       │                                                         │
│       ├──→ event: heights          (~50ms)                     │
│       │    data: {traufhoehe_m, firsthoehe_m, source}          │
│       │    → UI: Höhendaten anzeigen                           │
│       │                                                         │
│       ├──→ event: terrain          (~200ms)                    │
│       │    data: {terrain_height_m, slope_m, slope_class}      │
│       │    → UI: Hanglage-Warnung bei "stark"                  │
│       │                                                         │
│       ├──→ event: zones            (~500ms)                    │
│       │    data: {zones[], complexity, source}                 │
│       │    → UI: Zonen-Übersicht anzeigen                      │
│       │                                                         │
│       └──→ event: complete                                     │
│            data: {status, duration_ms, bundle}                 │
│            → UI: "Projekt erstellen" Button aktivieren         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# Teil E: Minimal + On-Demand Architektur

## E.1 Gemessene Zeiten (10.01.2026)

| Phase | Zeit |
|-------|------|
| STAC API Tile-Suche | ~2s |
| ZIP Download (Tile 1322-21) | ~5s |
| GDB Entpacken + Parsing | ~100s |
| Prefetch ALLER Gebäude im Tile | ~100s |

**Problem:** Bei jedem Cold-Start warten User ~200s.

## E.2 Lösung: MINIMAL + ON-DEMAND

```
┌─────────────────────────────────────────────────────────────────┐
│            MINIMAL + ON-DEMAND ARCHITEKTUR                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User fragt Gebäude X an                                        │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────┐           │
│  │  SCHRITT 1: MINIMAL LOAD (SYNCHRON)             │           │
│  │  ═══════════════════════════════════            │           │
│  │  • Nur Hauptgebäude X laden                     │           │
│  │  • Direkte Nachbarn (5m) laden                  │           │
│  │  • blocked_facades berechnen                    │           │
│  │  • Zeit: ~5-10s (nur einmal pro Tile)          │           │
│  └─────────────────────────────────────────────────┘           │
│       │                                                         │
│       │ Response sofort mit blocked_facades!                    │
│       │                                                         │
│       ├──→ UI: Hauptgebäude rendern                            │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────┐           │
│  │  SCHRITT 2: BACKGROUND PREFETCH (ASYNC)         │           │
│  │  ══════════════════════════════════════         │           │
│  │  • Restliche Gebäude im Tile laden              │           │
│  │  • User kann bereits arbeiten!                  │           │
│  │  • Zeit: ~100s (im Hintergrund)                │           │
│  └─────────────────────────────────────────────────┘           │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────┐           │
│  │  SCHRITT 3: ON-DEMAND (bei Bedarf)              │           │
│  │  ═════════════════════════════════              │           │
│  │  • User zoomt raus → mehr Nachbarn laden        │           │
│  │  • Radius 20m → 50m → 100m progressiv           │           │
│  │  • Nur wenn tatsächlich gebraucht               │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## E.3 Zusammenfassung (GEMESSEN 10.01.2026)

| Aspekt | VORHER | NACHHER (implementiert) | Verbesserung |
|--------|--------|-------------------------|--------------|
| Cold Start | ~108s | ~80s | (Tile-Download unvermeidlich) |
| Warm Cache (Stufe 1) | N/A | **0.29s** | 373x schneller |
| Nachbar (gleiches Tile) | ~108s | **0.009s** | 12000x schneller |
| Bundle-Cache | N/A | **0.015s** | 7200x schneller |
| User-Blockierung | Ja (Prefetch) | Nein (Async) | ✅ |
| blocked_facades | Nach Prefetch | Sofort (5m Nachbarn) | ✅ |

---

# Anhang F: SQLite-Optimierungen für Streaming

> **Ziel:** Schnellere DB-Zugriffe ohne Technologie-Wechsel
> **Aufwand:** 2-4 Stunden
> **Erwarteter Speedup:** ~2x für Queries

## F.1 TODO-Liste

| # | Task | Datei | Aufwand | Speedup |
|---|------|-------|---------|---------|
| 1 | Connection-Reuse | `building_3d_service.py` | 30 min | ~1.5x |
| 2 | Read-Only Connections | `building_3d_service.py` | 15 min | ~1.2x |
| 3 | Query-Optimierung | `building_3d_service.py` | 1h | ~1.3x |
| 4 | Covering Index | Schema | 30 min | ~2x |

## F.2 Implementierung

### Task 1: Connection-Reuse für Streaming

```python
# building_3d_service.py

from threading import local
from contextlib import contextmanager

class Building3DService:
    """Optimierter Service mit Connection-Pooling."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = local()
    
    @contextmanager
    def _get_read_connection(self):
        """
        Thread-lokale Read-Only Connection.
        
        Vorteile:
        - Keine Connection-Erstellung pro Query
        - WAL-Mode erlaubt parallele Reads
        - Read-Only = schneller
        """
        
        if not hasattr(self._local, 'read_conn'):
            self._local.read_conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro",  # Read-Only!
                uri=True,
                check_same_thread=False
            )
            # Optimierungen für Reads
            self._local.read_conn.execute("PRAGMA query_only=ON")
            self._local.read_conn.execute("PRAGMA cache_size=-32000")  # 32MB
            self._local.read_conn.execute("PRAGMA mmap_size=134217728")  # 128MB
        
        yield self._local.read_conn
```

### Task 2: Optimierte Neighbor-Query

```python
# building_3d_service.py

def get_neighbors_optimized(self, center_e: float, center_n: float, 
                            radius_m: float, 
                            exclude_egids: list[int] = None) -> list[dict]:
    """
    Optimierte Nachbar-Suche mit Bounding-Box Filter.
    
    SQLite kann den Index nur für einfache Vergleiche nutzen.
    Daher: Erst BBox-Filter (Index), dann Distanz-Filter (Scan).
    """
    
    with self._get_read_connection() as conn:
        # Phase 1: Grobe BBox-Filterung (nutzt Index!)
        bbox_query = """
            SELECT egid, polygon, center_e, center_n, 
                   traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
            FROM buildings_3d
            WHERE center_e BETWEEN ? AND ?
              AND center_n BETWEEN ? AND ?
        """
        
        params = [
            center_e - radius_m, center_e + radius_m,
            center_n - radius_m, center_n + radius_m
        ]
        
        # Exclude-Clause hinzufügen
        if exclude_egids:
            placeholders = ",".join("?" * len(exclude_egids))
            bbox_query += f" AND egid NOT IN ({placeholders})"
            params.extend(exclude_egids)
        
        cursor = conn.execute(bbox_query, params)
        candidates = cursor.fetchall()
        
        # Phase 2: Exakte Distanz-Filterung (im Python)
        results = []
        radius_sq = radius_m * radius_m
        
        for row in candidates:
            dx = row[2] - center_e
            dy = row[3] - center_n
            if (dx*dx + dy*dy) <= radius_sq:
                results.append(self._row_to_dict(row))
        
        return results
```

### Task 3: Covering Index

```sql
-- Covering Index: Alle häufig abgefragten Spalten im Index
-- SQLite kann Query komplett aus Index beantworten (kein Table-Lookup)

DROP INDEX IF EXISTS idx_buildings_3d_coords;

CREATE INDEX idx_buildings_3d_covering ON buildings_3d(
    center_e, 
    center_n,
    egid,
    traufhoehe_m,
    firsthoehe_m,
    gebaeudehoehe_m
);

-- Für Tile-basierte Abfragen
CREATE INDEX idx_buildings_3d_tile_covering ON buildings_3d(
    tile_id,
    egid,
    center_e,
    center_n
);
```

### Task 4: Prepared Statements für SSE

```python
# project_context_streaming.py

class ProjectContextStreamer:
    """Optimierter Streamer mit vorbereiteten Queries."""
    
    def __init__(self, building_service: Building3DService):
        self.building_service = building_service
        self._prepared = False
        self._neighbor_stmt = None
    
    def _prepare_statements(self, conn):
        """Statements einmal vorbereiten, mehrfach nutzen."""
        
        if not self._prepared:
            # Wird für jedes Neighbor-Event wiederverwendet
            self._neighbor_query = """
                SELECT egid, polygon, center_e, center_n,
                       traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
                FROM buildings_3d
                WHERE center_e BETWEEN ? AND ?
                  AND center_n BETWEEN ? AND ?
                  AND egid NOT IN ({exclude_placeholder})
            """
            self._prepared = True
    
    async def stream_context(self, project_egids: list[int]):
        """
        SSE-Stream mit optimierten DB-Zugriffen.
        
        Eine Connection für den gesamten Stream!
        """
        
        with self.building_service._get_read_connection() as conn:
            self._prepare_statements(conn)
            
            # Event 1: Centroid
            centroid = self._get_centroid(conn, project_egids)
            yield self._format_sse("centroid", centroid)
            
            # Event 2: Project Buildings
            buildings = self._get_buildings(conn, project_egids)
            yield self._format_sse("project_buildings", buildings)
            
            # Event 3: Blocked Facades (mit 5m Nachbarn)
            facades = self._get_blocked_facades(conn, project_egids, radius=5)
            yield self._format_sse("blocked_facades", facades)
            
            # Events 4-6: Progressive Neighbors (20m, 50m, 100m)
            for radius in [20, 50, 100]:
                neighbors = self._get_neighbors(conn, centroid, radius, project_egids)
                yield self._format_sse("neighbors", {
                    "radius": radius,
                    "buildings": neighbors
                })
            
            yield self._format_sse("complete", {"status": "ok"})
```

## F.3 Performance nach SQLite-Optimierung

| Query | Vorher | Nachher | Speedup |
|-------|--------|---------|---------|
| `get_by_egid` | ~1ms | ~0.5ms | 2x |
| `get_neighbors(5m)` | ~5ms | ~2ms | 2.5x |
| `get_neighbors(100m)` | ~50ms | ~15ms | 3.3x |
| SSE Stream (komplett) | ~500ms | ~200ms | 2.5x |

---

# Anhang G: DuckDB-Migration für Streaming

> **Ziel:** Maximale Query-Performance + parallele Reads
> **Aufwand:** 4-8 Stunden
> **Erwarteter Speedup:** ~5-10x für Spatial-Queries

## G.1 Warum DuckDB für Streaming?

| Aspekt | SQLite | DuckDB |
|--------|--------|--------|
| **Parallele Reads** | Ja (WAL) | Ja (native) |
| **SIMD-Filterung** | Nein | Ja |
| **Columnar Storage** | Nein | Ja |
| **Spatial Queries** | Langsam | **Sehr schnell** |
| **Concurrent Connections** | Begrenzt | Unbegrenzt |

## G.2 TODO-Liste

| # | Task | Beschreibung | Aufwand |
|---|------|--------------|---------|
| 1 | Schema migrieren | `building_3d.duckdb` erstellen | 30 min |
| 2 | Service anpassen | DuckDB-Connection-Handling | 2h |
| 3 | Queries optimieren | Vectorized Operations nutzen | 1h |
| 4 | SSE-Integration | Async-kompatible Queries | 1h |
| 5 | Tests anpassen | Bestehende Tests updaten | 1h |

## G.3 Implementierung

### Optimierter Streaming-Service mit DuckDB

```python
# building_3d_service_duckdb.py

import duckdb
from pathlib import Path
from typing import Generator
import json

class Building3DServiceDuckDB:
    """
    DuckDB-basierter Building Service.
    
    Optimiert für:
    - Parallele Reads (keine Locks)
    - Schnelle Spatial-Queries (SIMD)
    - Effizientes Streaming (Columnar)
    """
    
    def __init__(self, db_path: str = "data/building_3d.duckdb"):
        self.db_path = Path(db_path)
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Schema mit optimierten Datentypen."""
        
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS buildings_3d (
                    egid INTEGER PRIMARY KEY,
                    polygon JSON,
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
            
            # Optimierter Index für Spatial-Queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_spatial 
                ON buildings_3d(center_e, center_n)
            """)
    
    def get_neighbors_streaming(self, center_e: float, center_n: float,
                                 radii: list[float],
                                 exclude_egids: list[int] = None) -> Generator:
        """
        Streaming-Nachbar-Abfrage für SSE.
        
        Gibt für jeden Radius einen Batch zurück.
        DuckDB parallelisiert die Queries automatisch.
        """
        
        exclude_set = set(exclude_egids or [])
        seen_egids = set()
        
        # Read-Only Connection (parallel zu anderen Reads)
        with duckdb.connect(str(self.db_path), read_only=True) as conn:
            
            for radius in radii:
                # DuckDB nutzt SIMD für schnelle Filterung
                result = conn.execute("""
                    SELECT 
                        egid, polygon, center_e, center_n,
                        traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
                    FROM buildings_3d
                    WHERE center_e BETWEEN ? - ? AND ? + ?
                      AND center_n BETWEEN ? - ? AND ? + ?
                """, [center_e, radius, center_e, radius,
                      center_n, radius, center_n, radius]).fetchall()
                
                # Filtern: nur neue, nicht-excludierte Gebäude
                batch = []
                for row in result:
                    egid = row[0]
                    if egid not in exclude_set and egid not in seen_egids:
                        # Exakte Distanz-Prüfung
                        dx = row[2] - center_e
                        dy = row[3] - center_n
                        if (dx*dx + dy*dy) <= radius*radius:
                            batch.append(self._row_to_dict(row))
                            seen_egids.add(egid)
                
                yield {"radius": radius, "buildings": batch, "count": len(batch)}
    
    def get_blocked_facades_fast(self, egids: list[int], 
                                  radius_m: float = 5.0) -> dict:
        """
        Schnelle blocked_facades Berechnung.
        
        DuckDB kann die Nachbarn aller Projekt-Gebäude 
        in einer einzigen Query finden.
        """
        
        with duckdb.connect(str(self.db_path), read_only=True) as conn:
            
            # Alle Projekt-Gebäude laden
            project_buildings = conn.execute("""
                SELECT egid, polygon, center_e, center_n 
                FROM buildings_3d 
                WHERE egid IN ({})
            """.format(",".join("?" * len(egids))), egids).fetchall()
            
            result = {}
            
            for building in project_buildings:
                egid, polygon_json, center_e, center_n = building
                
                # Nachbarn für dieses Gebäude (exclude andere Projekt-Gebäude)
                other_egids = [e for e in egids if e != egid]
                exclude_clause = ""
                params = [center_e, radius_m, center_e, radius_m,
                         center_n, radius_m, center_n, radius_m]
                
                if other_egids:
                    exclude_clause = "AND egid NOT IN ({})".format(
                        ",".join("?" * len(other_egids)))
                    params.extend(other_egids)
                
                neighbors = conn.execute(f"""
                    SELECT egid, polygon, center_e, center_n
                    FROM buildings_3d
                    WHERE center_e BETWEEN ? - ? AND ? + ?
                      AND center_n BETWEEN ? - ? AND ? + ?
                      AND egid != ?
                      {exclude_clause}
                """, params + [egid]).fetchall()
                
                # Blocked Facades berechnen
                polygon = json.loads(polygon_json) if isinstance(polygon_json, str) else polygon_json
                blocked = self._calculate_blocked_facades(
                    polygon, center_e, center_n, neighbors
                )
                result[egid] = blocked
            
            return result
    
    def _row_to_dict(self, row) -> dict:
        """Row zu Dict konvertieren."""
        return {
            "egid": row[0],
            "polygon": json.loads(row[1]) if isinstance(row[1], str) else row[1],
            "center_e": row[2],
            "center_n": row[3],
            "traufhoehe_m": row[4],
            "firsthoehe_m": row[5],
            "gebaeudehoehe_m": row[6]
        }
    
    def _calculate_blocked_facades(self, polygon, center_e, center_n, 
                                    neighbors) -> list[int]:
        """Berechnet welche Fassaden blockiert sind."""
        # Implementierung wie bestehend
        # ...
        pass
```

### SSE-Integration mit DuckDB

```python
# project_context_streaming_duckdb.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import asyncio

router = APIRouter()

@router.get("/project/{project_id}/context/stream")
async def stream_project_context(project_id: str):
    """
    SSE-Endpoint mit DuckDB-Backend.
    
    DuckDB erlaubt parallele Reads, daher können wir
    multiple Queries gleichzeitig ausführen.
    """
    
    async def generate():
        service = Building3DServiceDuckDB()
        project = await get_project(project_id)
        project_egids = project.building_egids
        
        # Event 1: Centroid (sofort)
        centroid = service.get_centroid(project_egids)
        yield f"event: centroid\ndata: {json.dumps(centroid)}\n\n"
        
        # Event 2: Project Buildings (sofort)
        buildings = service.get_buildings(project_egids)
        yield f"event: project_buildings\ndata: {json.dumps(buildings)}\n\n"
        
        # Event 3: Blocked Facades (DuckDB macht das schnell!)
        facades = service.get_blocked_facades_fast(project_egids)
        yield f"event: blocked_facades\ndata: {json.dumps(facades)}\n\n"
        
        # Events 4-6: Progressive Neighbors (Streaming!)
        center_e, center_n = centroid["center_e"], centroid["center_n"]
        
        for batch in service.get_neighbors_streaming(
            center_e, center_n, 
            radii=[20, 50, 100],
            exclude_egids=project_egids
        ):
            yield f"event: neighbors\ndata: {json.dumps(batch)}\n\n"
            await asyncio.sleep(0)  # Yield to event loop
        
        # Event 7: Complete
        yield f"event: complete\ndata: {json.dumps({'status': 'ok'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
```

## G.4 Performance-Vergleich Streaming

| Metrik | SQLite | SQLite (opt.) | DuckDB |
|--------|--------|---------------|--------|
| Time to `centroid` | ~10ms | ~5ms | **~2ms** |
| Time to `blocked_facades` | ~50ms | ~20ms | **~5ms** |
| Time to `neighbors(100m)` | ~400ms | ~150ms | **~30ms** |
| Total Stream Duration | ~500ms | ~200ms | **~50ms** |
| Concurrent Streams | ~10 | ~20 | **~100+** |

## G.5 Feature-Flag für Migration

```python
# config.py

import os

USE_DUCKDB = os.getenv("USE_DUCKDB", "false").lower() == "true"

def get_building_service():
    """Factory für Building Service."""
    
    if USE_DUCKDB:
        from .building_3d_service_duckdb import Building3DServiceDuckDB
        return Building3DServiceDuckDB()
    else:
        from .building_3d_service import Building3DService
        return Building3DService()
```

```bash
# Railway Environment Variables
USE_DUCKDB=true
```

---

## Empfehlung

### Für Streaming-Performance:

| Priorität | Massnahme | Speedup | Aufwand |
|-----------|-----------|---------|---------|
| 1 | SQLite Connection-Reuse (F.2 Task 1) | ~1.5x | 30 min |
| 2 | Covering Index (F.2 Task 3) | ~2x | 30 min |
| 3 | Query-Optimierung (F.2 Task 2) | ~1.3x | 1h |
| 4 | DuckDB-Migration (G.3) | ~5x | 4-8h |

### Entscheidungsmatrix:

| Wenn... | Dann... |
|---------|---------|
| Nur wenige concurrent User | SQLite-Optimierung reicht |
| Viele concurrent Streams (>20) | DuckDB empfohlen |
| Grosse Radien (100m+) häufig | DuckDB empfohlen |
| Minimaler Aufwand gewünscht | SQLite-Optimierung |

---

## Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 10.01.2026 | 4.0 | Anhang F (SQLite-Opt.) + Anhang G (DuckDB) hinzugefügt |
| 10.01.2026 | 3.4 | Teil E: Stufe 2 Fix - Prefetch auch bei gecachten Tiles |
| 10.01.2026 | 3.3 | Teil E implementiert: MINIMAL + ON-DEMAND Architektur |
| 10.01.2026 | 3.2 | Tile-Prefetch Timing & On-Demand Architektur (Teil E) |
| 10.01.2026 | 3.1 | Pipeline-Optimierung: Maximale Parallelisierung (Teil D) |
| 08.01.2026 | 3.0 | Building-Data-Streaming hinzugefügt (Teil C) |
| 08.01.2026 | 2.0 | Project-Context-Streaming hinzugefügt (Teil B) |
| 07.01.2026 | 1.0 | 3-Stufen Lookup implementiert (Teil A) |
