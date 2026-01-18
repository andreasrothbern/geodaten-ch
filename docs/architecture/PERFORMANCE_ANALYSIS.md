# Performance-Analyse: Storage-Strategien

**Stand: 18.01.2026 (aktualisiert)**

## Übersicht

Diese Analyse vergleicht verschiedene Strategien für die Speicherung von Gebäudedaten
und deren Auswirkung auf Performance und Speicherbedarf.

---

## AKTUELLE MESSUNGEN (18.01.2026)

### Nachbarn-Suche: DuckDB Koordinaten-Query

Gemessen mit EGID 1243901 (Knospenweg-Bereich, 6409 Gebäude in DB):

| Radius | Zeit | Nachbarn |
|--------|------|----------|
| 5m | ~0.8ms | 31 |
| 10m | ~0.8ms | 38 |
| 20m | ~0.8ms | 50 |
| 50m | ~0.9ms | 91 |
| 100m | ~0.9ms | 135 |

**Ergebnis:** DuckDB ist bereits extrem schnell (~1ms), Redis würde **keinen messbaren Vorteil** bringen!

### Speicherbedarf (aktuell)

```
building_3d.duckdb:     51.76 MB (6409 Gebäude)
building_contexts.db:    0.18 MB
geruestbau.db:           0.02 MB
tiles.db:                0.01 MB
────────────────────────────────────────────
Total:                  ~52 MB
```

| Metrik | Wert |
|--------|------|
| Gebäude in DB | 6409 |
| Tiles (distinct) | 2 |
| **KB pro Gebäude** | **8.27 KB** |
| **MB pro 1000 Gebäude** | **8.08 MB** |

### Prefetch-Reihenfolge (VERIFIZIERT)

```
schedule_prefetch_with_neighbors() in tile_prefetch.py:1261-1325

1. ZUERST (synchron im Thread): 5m Radius Nachbarn
   └─ load_neighbors_and_save(..., radius_m=5.0)
   └─ Sofort in building_3d.duckdb gespeichert

2. DANACH (async, fire-and-forget): Restlicher Tile via Parquet-Pipeline
   └─ asyncio.create_task(prefetch_tile_buildings_async(...))
   └─ Im Hintergrund parallel zum User-Request
```

**BESTÄTIGT:** Die 5m-Nachbarn landen ZUERST in der DB, bevor der volle 100m-Tile importiert wird.

## Aktuelle Architektur (DuckDB)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AKTUELLER DATENFLUSS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. STAC API → Tile-Download (ZIP ~50-200 MB)                   │
│     └─ ~5-15s Download                                          │
│                                                                 │
│  2. GDB → Parquet (parallel, streaming)                         │
│     └─ ~30-60s für 5000 Gebäude                                 │
│                                                                 │
│  3. Parquet → DuckDB (bulk load)                                │
│     └─ ~5-10s für 5000 Gebäude                                  │
│                                                                 │
│  4. DuckDB → API Response                                       │
│     └─ ~1-5ms pro Gebäude (EGID-Lookup)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Gemessene Performance (Knospenweg 4, Bern)

| Phase | Zeit | Bemerkung |
|-------|------|-----------|
| Tile-Download | ~8-12s | Abhängig von Tile-Grösse |
| GDB Parsing | ~40-80s | 4900 Gebäude pro Tile |
| DuckDB Import | ~5-10s | Parquet-Pipeline |
| **Gesamt First-Load** | **~60-100s** | Einmalig pro Tile |
| DB-Lookup | ~1-3ms | Nach Import |
| Projekt laden (SQLite) | ~5-15ms | Aus geruestbau.db |

### Endpunkte für Performance-Messung

```bash
# Import-Metriken (letzer Tile-Import)
GET /api/v1/import/metrics

# Vergleich DB vs. API-Call
GET /api/v1/performance/compare?egid=1243790&address=Knospenweg%204,%20Bern
```

## Storage-Strategien Vergleich

### Option A: DuckDB (Aktuell)

**Beschreibung:** Alle Gebäudedaten werden in DuckDB gespeichert.

```
Speicher:
├─ building_3d.duckdb    ~50-150 MB (je nach Region)
├─ tiles.db              ~1 MB (Metadaten)
└─ geruestbau.db         ~1-5 MB (Projekte + GeruestbauData)
```

| Aspekt | Bewertung |
|--------|-----------|
| Read-Performance | ⭐⭐⭐⭐⭐ (~1-3ms) |
| Write-Performance | ⭐⭐⭐⭐ (~5-10s bulk) |
| Speicherbedarf | ⭐⭐⭐ (~50-150 MB) |
| Komplexität | ⭐⭐⭐⭐ (Parquet-Pipeline) |
| Railway-Tauglich | ⭐⭐⭐⭐ (Ephemeral OK, Volume empfohlen) |

**Vorteile:**
- Extrem schnelle Lookups (~1ms)
- SQL-Queries auf 3D-Daten
- Bulk-Import via Parquet
- Keine externe Dependency

**Nachteile:**
- Speicherbedarf (~50-150 MB)
- Initialer Import langsam
- Bei Ephemeral Storage: Daten weg nach Restart

---

### Option B: Parquet-Only (ohne DuckDB)

**Beschreibung:** Daten bleiben in Parquet-Dateien, Queries via PyArrow.

```
Speicher:
├─ parquet/
│   ├─ buildings_3d/      ~30-80 MB (partitioniert nach Tile)
│   ├─ building_roofs/    ~10-30 MB
│   └─ building_walls/    ~15-40 MB
└─ tiles.db               ~1 MB (Metadaten + Index)
```

| Aspekt | Bewertung |
|--------|-----------|
| Read-Performance | ⭐⭐⭐ (~10-50ms mit Predicate Pushdown) |
| Write-Performance | ⭐⭐⭐⭐⭐ (~1-2s streaming) |
| Speicherbedarf | ⭐⭐⭐⭐ (~55-150 MB, komprimiert) |
| Komplexität | ⭐⭐⭐ (PyArrow Queries) |
| Railway-Tauglich | ⭐⭐⭐ (viele kleine Files) |

**Vorteile:**
- Schnellerer Import (kein DB-Overhead)
- Streaming-fähig
- Kompression eingebaut

**Nachteile:**
- Langsamere Lookups (~10-50ms statt ~1ms)
- Komplexere Query-Logik
- Kein SQL

**Implementierungs-Aufwand:** ~4-8 Stunden

---

### Option C: In-Memory Cache (Redis/Memcached)

**Beschreibung:** Hot Data im Memory, Cold Data in DB/Parquet.

```
Architektur:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Request    │ ──▶ │  Redis Cache │ ──▶ │   DuckDB     │
│              │     │  (Hot Data)  │     │ (Cold Data)  │
└──────────────┘     └──────────────┘     └──────────────┘
                           │
                     Cache Miss → Load from DB → Cache
```

| Aspekt | Bewertung |
|--------|-----------|
| Read-Performance | ⭐⭐⭐⭐⭐ (~0.5ms Cache Hit) |
| Write-Performance | ⭐⭐⭐⭐ (async) |
| Speicherbedarf | ⭐⭐ (~100-300 MB RAM) |
| Komplexität | ⭐⭐ (Redis Dependency) |
| Railway-Tauglich | ⭐⭐ (Redis Add-on ~$5-20/Monat) |

**Vorteile:**
- Extrem schnelle Reads bei Cache Hit
- Skalierbar
- TTL-basierte Invalidierung

**Nachteile:**
- Zusätzliche Dependency (Redis)
- RAM-Verbrauch
- Kosten auf Railway (~$5-20/Monat)
- Cache-Invalidierung komplex

**Implementierungs-Aufwand:** ~8-16 Stunden

---

### ⚠️ Redis vs. DuckDB Vergleich (18.01.2026)

**Frage:** Lohnt sich Redis mit 0.5ms Antwortzeit für Koordinaten-Suche?

| Metrik | DuckDB (aktuell) | Redis (theoretisch) |
|--------|------------------|---------------------|
| Koordinaten-Query (10m) | **0.8ms** | ~0.5ms |
| Koordinaten-Query (100m) | **0.9ms** | ~0.5ms |
| Speicher | ~8 KB/Gebäude (Disk) | ~8 KB/Gebäude (RAM) |
| Kosten Railway | $0 (in Volume) | $5-20/Monat |
| Komplexität | Einfach | Redis-Cluster, TTL, Invalidierung |

**Fazit:** DuckDB ist bereits so schnell (~1ms), dass Redis **keinen spürbaren Vorteil** bringt:
- Unterschied: 0.3ms (0.5ms vs. 0.8ms) - **nicht wahrnehmbar** für User
- Redis bräuchte zusätzliche Infrastruktur + Kosten
- Koordinaten-Suche mit BBox ist in DuckDB optimal (nutzt Index)

**Empfehlung:** **KEIN Redis nötig!** DuckDB reicht völlig aus.

---

### Option D: Hybrid (Buildings in Projekt) ✅ AKTUELL IMPLEMENTIERT

**Beschreibung:** GeruestbauData direkt im Projekt speichern.

**Was ist "buildings_data"?**
```
geruestbau.db → projects Tabelle → buildings_data Spalte (JSON)

Inhalt pro Projekt:
{
  "1243790": {                    // EGID als Key
    "building": {
      "egid": "1243790",
      "polygon": [[e,n], [e,n], ...],
      "traufhoehe_m": 5.54,
      "firsthoehe_m": 9.34,
      "gebaeudehoehe_m": 9.34
    },
    "terrain": {
      "z_min": 556.2,
      "z_max": 558.0,
      "slope_m": 1.8
    },
    "walls": [...],               // 3D-Wand-Geometrie
    "roofs": [...]                // 3D-Dach-Geometrie
  },
  "1243792": { ... }              // Weiteres Gebäude im Projekt
}
```

**Warum "Hybrid"?**
```
┌──────────────────────────────────────────────────────────────────┐
│                    HYBRID-ARCHITEKTUR                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PROJEKT ERSTELLEN (einmalig)                                │
│     └─ SmartBuildingService.collect_all_data()                  │
│         └─ Daten aus DuckDB + API sammeln                       │
│         └─ buildings_data in geruestbau.db speichern            │
│                                                                  │
│  2. PROJEKT ÖFFNEN (wiederholt)                                 │
│     └─ project_service.get_project_with_data()                  │
│         └─ DIREKT aus geruestbau.db (SQLite)                    │
│         └─ KEIN DuckDB-Lookup nötig!                            │
│         └─ ~5-15ms statt ~60-100s                               │
│                                                                  │
│  3. NACHBARN SUCHEN (dynamisch)                                 │
│     └─ neighbors_service.get_neighbors()                        │
│         └─ DuckDB Koordinaten-Query (~1ms)                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

| Aspekt | Bewertung |
|--------|-----------|
| Read-Performance | ⭐⭐⭐⭐⭐ (~5-15ms Projekt laden) |
| Write-Performance | ⭐⭐⭐⭐ (~50-200ms bei Erstellung) |
| Speicherbedarf | ⭐⭐⭐ (~10-100 KB pro Projekt) |
| Komplexität | ⭐⭐⭐⭐⭐ (bereits implementiert!) |
| Railway-Tauglich | ⭐⭐⭐⭐⭐ (SQLite in Volume) |

**Vorteile:**
- Bereits implementiert (`project_service.py:484-555`)
- Kein DuckDB-Lookup beim Projekt-Öffnen nötig
- Projekt ist **self-contained** (alle Daten dabei)
- Funktioniert auch wenn DuckDB leer/gelöscht ist
- Performance-Logging eingebaut: `[PERF] Projekt laden: Xms`

**Nachteile:**
- Daten-Duplikation (gleiche EGID in mehreren Projekten)
- Projekt-Grösse wächst (~10-100 KB pro Gebäude)
- Nachbarn-Queries gehen immer über DuckDB (nicht aus buildings_data)

**Performance gemessen (project_service.py):**
```
[PERF] Projekt laden: 12.3ms total | DB-Query: 3.1ms | JSON-Parse: 8.5ms | Daten: 45.2KB
```

---

## Speicherbedarf-Analyse

### Railway Volume Limits

| Plan | Volume | Empfehlung |
|------|--------|------------|
| Hobby | 500 MB | DuckDB + Tile-Cleanup |
| Pro | 5 GB | DuckDB + alle Tiles cached |
| Team | 50 GB | Alle Regionen vorgeladen |

### Aktuelle Datengrössen (Beispiel Bern)

```
building_3d.duckdb:
├─ buildings_3d        ~40 MB (15'000 Gebäude)
├─ building_roofs      ~10 MB
├─ building_walls      ~15 MB
└─ Indices             ~5 MB
─────────────────────────────
Gesamt:                ~70 MB

tiles.db:              ~1 MB
geruestbau.db:         ~2 MB (10 Projekte)
─────────────────────────────
Total:                 ~73 MB
```

### Speicher pro Gebäude

| Daten | Grösse | Komprimiert |
|-------|--------|-------------|
| Polygon (JSON) | ~2-5 KB | ~0.5-1 KB |
| Höhen | ~0.1 KB | ~0.05 KB |
| Walls (3D-Geometrie) | ~1-10 KB | ~0.3-3 KB |
| Roofs (3D-Geometrie) | ~0.5-5 KB | ~0.15-1.5 KB |
| **Gesamt pro Gebäude** | **~4-20 KB** | **~1-6 KB** |

---

## Empfehlung

### Für Railway (Hobby Plan, 500 MB Volume)

**Empfohlene Strategie: DuckDB + Tile-Cleanup + Projekt-Speicherung**

```
1. Tile-Download → GDB → Parquet → DuckDB
2. GDB nach Import LÖSCHEN (CLEANUP_TILES_AFTER_IMPORT=true)
3. Bei Projekt-Erstellung: GeruestbauData in buildings_data speichern
4. Bei Projekt-Laden: Direkt aus buildings_data (kein DB-Lookup)
```

**Warum?**
- Tile-Cleanup spart ~95% Speicher (GDB ~50-200 MB → DB ~1-3 MB)
- buildings_data macht Projekte self-contained
- Kein zusätzlicher Service (Redis) nötig
- Bereits implementiert!

### Performance-Ziele

| Szenario | Ziel | Aktuell |
|----------|------|---------|
| First-Load (neues Gebäude) | < 120s | ~60-100s ✅ |
| Projekt öffnen (vorhandene Daten) | < 50ms | ~5-15ms ✅ |
| Fassaden-Berechnung | < 100ms | ~50-200ms ✅ |
| 3D-Rendering | < 200ms | ~100-300ms ✅ |

---

## Nächste Schritte

1. **Monitoring einrichten** - Performance-Metriken in Logs sammeln
2. **Cache-Warming** - Beliebte Regionen (Bern, Zürich) vorpreloaden
3. **Lazy Loading** - 3D-Geometrie nur bei Bedarf laden
4. **CDN für Tiles** - Download-Zeit reduzieren

---

## API-Endpunkte für Performance-Analyse

### Echte Test-Daten (Knospenweg, Bern)

| EGID | Adresse | Koordinaten (E, N) | Traufhöhe |
|------|---------|-------------------|-----------|
| 1243790 | Knospenweg 4 | 2596299.9, 1199805.0 | 7.1m |
| 1243792 | Knospenweg 6 | 2596299.7, 1199812.8 | 7.1m |
| 1243794 | Knospenweg 8 | 2596299.0, 1199820.1 | 7.4m |
| 1243788 | Knospenweg 2 | 2596301.0, 1199797.8 | 6.5m |
| 1243787 | Knospenweg 1 | 2596269.8, 1199794.5 | 7.2m |

### Funktionierende API-Aufrufe

```bash
# ============================================
# 1. NACHBARN PER EGID (bestehend)
# ============================================
# Alle Nachbarn im 10m Radius um Knospenweg 4
curl "http://localhost:8000/api/v1/geruestbau/building/1243790/neighbors?radius_m=10"

# Nur angrenzende Gebäude (5m)
curl "http://localhost:8000/api/v1/geruestbau/building/1243790/neighbors?radius_m=5"

# ============================================
# 2. NEU: NACHBARN PER KOORDINATEN (18.01.2026)
# ============================================
# Gebäude im 10m Radius um Koordinate (Knospenweg-Bereich)
curl "http://localhost:8000/api/v1/geruestbau/neighbors/by-coordinates?e=2596299.9&n=1199805.0&radius_m=10"

# 50m Radius (mehr Kontext)
curl "http://localhost:8000/api/v1/geruestbau/neighbors/by-coordinates?e=2596299.9&n=1199805.0&radius_m=50"

# 100m Radius (volle Umgebung)
curl "http://localhost:8000/api/v1/geruestbau/neighbors/by-coordinates?e=2596299.9&n=1199805.0&radius_m=100"

# Ohne Polygone (schneller, weniger Daten)
curl "http://localhost:8000/api/v1/geruestbau/neighbors/by-coordinates?e=2596299.9&n=1199805.0&radius_m=10&include_polygons=false"

# ============================================
# 3. DB-STATISTIKEN UND METRIKEN
# ============================================
# Aktuelle DB-Statistiken
curl "http://localhost:8000/api/v1/import/db-stats"

# Letzte Import-Metriken
curl "http://localhost:8000/api/v1/import/metrics"

# ============================================
# 4. PERFORMANCE-VERGLEICH DB vs. API
# ============================================
# Vergleich mit EGID (benötigt gestartetes Backend!)
curl "http://localhost:8000/api/v1/performance/compare?egid=1243790"

# Vergleich mit EGID + Adresse (für SmartBuildingService)
curl "http://localhost:8000/api/v1/performance/compare?egid=1243790&address=Knospenweg%204,%203006%20Bern"

# ============================================
# 5. ADRESS-AUFLÖSUNG (Multi-Building)
# ============================================
# Hausnummern-Range auflösen
curl "http://localhost:8000/api/v1/geruestbau/address/resolve?address=Knospenweg%202-10,%20Bern"
```

### Response-Beispiel: Koordinaten-basierte Nachbarsuche

```json
{
  "center": {"e": 2596299.9, "n": 1199805.0},
  "radius_m": 10.0,
  "buildings_count": 5,
  "buildings": [
    {
      "egid": "1243790",
      "center_e": 2596299.9,
      "center_n": 1199805.0,
      "distance_m": 0.0,
      "traufhoehe_m": 7.1,
      "firsthoehe_m": 9.34,
      "gebaeudehoehe_m": 9.34,
      "polygon": [[...], [...]]
    },
    {
      "egid": "1243792",
      "distance_m": 7.8,
      ...
    }
  ],
  "query_time_ms": 0.85
}
```

### Projekt-Ladezeit (im Log)

```bash
# Suche nach Performance-Logs:
# [PERF] Projekt laden: 12.3ms total | DB-Query: 3.1ms | JSON-Parse: 8.5ms | Daten: 45.2KB
```

---

## DuckDB vs. SQLite: Direkter Vergleich

### Warum DuckDB (seit 13.01.2026)?

| Aspekt | SQLite | DuckDB |
|--------|--------|--------|
| **OLAP-Performance** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Bulk-Insert** | Langsam (einzelne Rows) | Schnell (Parquet-Import) |
| **JSON-Support** | TEXT + json_extract() | Native JSON-Typ |
| **Koordinaten-Suche** | Gut | Sehr gut (Column-Store) |
| **RAM-Nutzung** | Gering | Höher (aber kontrollierbar) |
| **Multi-Threading** | Single-Thread | Multi-Thread |

### Performance-Vergleich (gemessen)

| Operation | SQLite | DuckDB |
|-----------|--------|--------|
| EGID-Lookup | ~2-5ms | ~1-3ms |
| Koordinaten-BBox | ~5-20ms | **~0.8ms** |
| Bulk-Insert 5000 Geb. | ~30s | ~5-10s |
| JSON-Parsing | Runtime | Optimiert |

### Wann SQLite besser ist

- **Projekte (geruestbau.db):** Einfache CRUD-Operationen, kleine Tabellen
- **Metadata (tiles.db):** Wenige Rows, einfache Queries
- **Contexts (building_contexts.db):** Key-Value-ähnlicher Zugriff

### Wann DuckDB besser ist

- **Gebäudedaten (building_3d.duckdb):** Tausende Rows, Koordinaten-Queries
- **Bulk-Import:** Parquet → DuckDB ist 5-10x schneller
- **Analytische Queries:** Aggregationen, GROUP BY

### Aktuelles Setup

```
DuckDB:
└─ building_3d.duckdb     (~52 MB, 6409 Gebäude)
    ├─ buildings_3d       (Haupt-Tabelle)
    ├─ building_roofs     (3D-Dach-Geometrie)
    └─ building_walls     (3D-Wand-Geometrie)

SQLite:
├─ geruestbau.db          (~20 KB, Projekte)
├─ tiles.db               (~12 KB, Tile-Metadaten)
└─ building_contexts.db   (~188 KB, Zonen/Terrain)
```

**Empfehlung:** Hybrid-Ansatz beibehalten:
- DuckDB für räumliche Queries (Nachbarn, Koordinaten)
- SQLite für Projekte (einfach, robust, bewährt)

---

## Zusammenfassung: Antworten auf Ihre Fragen

### 1. API-Call für Nachbarn per Koordinaten (10-100m)?

**Endpoint:** `GET /api/v1/geruestbau/building/{egid}/neighbors?radius_m=100`

**Performance:** ~0.8-1ms (unabhängig vom Radius!)

```python
# neighbors_service.py:219-230
cursor.execute('''
    SELECT egid, polygon, center_e, center_n, ...
    FROM buildings_3d
    WHERE center_e BETWEEN ? AND ?
      AND center_n BETWEEN ? AND ?
      AND egid != ?
''', (center_e - radius, center_e + radius, center_n - radius, center_n + radius, egid))
```

### 2. Prefetch-Reihenfolge: 5m ZUERST?

**JA, BESTÄTIGT!** Siehe `tile_prefetch.py:1261-1325`:
1. 5m Nachbarn werden SYNCHRON im Thread geladen
2. Voller Tile wird ASYNC im Hintergrund importiert

### 3. Speicherbedarf pro Tile / 1000 Gebäude?

| Metrik | Wert |
|--------|------|
| KB pro Gebäude | ~8.27 KB |
| MB pro 1000 Gebäude | ~8.08 MB |
| MB pro Tile (~3000-5000 Geb.) | ~25-40 MB |

### 4. Redis interessant (0.5ms)?

**NEIN!** DuckDB ist bereits bei ~0.8ms - der Unterschied von 0.3ms ist:
- Für User nicht spürbar
- Redis kostet $5-20/Monat auf Railway
- Zusätzliche Komplexität (Cache-Invalidierung)

### 5. Was ist "Hybrid (buildings_data)"?

Projekt-Daten werden in `geruestbau.db` als JSON gespeichert:
- Bei Projekt-Erstellung: Alle Daten sammeln, in buildings_data speichern
- Bei Projekt-Öffnen: Direkt aus SQLite (~12ms), KEIN DuckDB-Lookup
- Nachbarn: Weiterhin via DuckDB (~1ms)

### 6. DuckDB vs. SQLite für Objekt-Abruf?

**DuckDB ist schneller für:**
- Koordinaten-basierte Suche (0.8ms vs. 5-20ms)
- Bulk-Queries (mehrere EGIDs)
- JSON-Parsing (nativ)

**SQLite ist ausreichend für:**
- Einzelne Projekt-Lookups
- Einfache CRUD

**Aktuell:** Hybrid-Ansatz optimal!
