# Geodaten-Architektur: Datenfluss & Caching

> **Memory-Dokument** - Erstellt am 03.01.2026, aktualisiert 03.01.2026
> **Branch:** `feature/exact-3d-view`
> **Status:** Tile-Cache ✅ | Neighbors-API ✅ | Adress-Parser ✅ | Polygon-Refactoring ✅

---

## 0. Zuständigkeiten

### Zwei Projekte, klare Trennung

```
┌─────────────────────────────────────────────────────────────────┐
│                        GEODATEN-CH                              │
│                    (Backend-Infrastruktur)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Zuständig für:                                                 │
│  ├─ Tile-Cache System (3-Stufen)                               │
│  ├─ swissBUILDINGS3D Fetcher                                   │
│  ├─ swisstopo API Integration                                  │
│  ├─ Parzellen-API (amtliche Vermessung)                        │
│  ├─ Polygon-Vereinfachung (Douglas-Peucker Service)            │
│  ├─ Höhendaten-Cache                                           │
│  ├─ Geocoding, GWR-Daten                                       │
│  ├─ Adress-Parser (Multi-Adresse: 2-10, 27/29)         ← NEU  │
│  └─ Neighbors-API (Nachbarn, Reihenhäuser)             ← NEU  │
│                                                                 │
│  Datenbanken:                                                   │
│  ├─ tile_cache.db         → Tile-Index, EGID-Mapping           │
│  ├─ building_geodata.db   → Gebäude-Cache (Polygon, Höhen)     │
│  └─ building_heights.db   → Höhen-Cache (Legacy)               │
│                                                                 │
│  Dateien:                                                       │
│  └─ /app/data/tiles/*.gdb → Persistente Tile-Dateien           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GERUESTBAU-APP                            │
│                      (Frontend + Logik)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Zuständig für:                                                 │
│  ├─ Projekt-Verwaltung                                         │
│  ├─ ProjectOverrides (simplify_epsilon, etc.)                  │
│  ├─ Fassaden-Auswahl                                           │
│  ├─ Gerüst-Konfiguration                                       │
│  ├─ 3D-Visualisierung                                          │
│  └─ Export (PDF, IFC)                                          │
│                                                                 │
│  Datenbanken:                                                   │
│  └─ geruestbau.db         → Projekte, Scaffold-Configs         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Schnittstelle

| Von | Nach | Daten |
|-----|------|-------|
| geodaten-ch | geruestbau-app | `polygon` (Original), Höhen, EGID |
| geruestbau-app | geodaten-ch | `simplify_epsilon`, `simplify_angle_tolerance` |
| geodaten-ch | geruestbau-app | `polygon_simplified` (on-the-fly berechnet) |

---

## 1. Kernkonzept: Polygon-Benennung

### Konvention (WICHTIG!)

| Begriff | Definition | Wo berechnet | Persistiert |
|---------|------------|--------------|-------------|
| `polygon` | **Original** aus swissBUILDINGS3D | geodaten-ch | ✅ Ja |
| `polygon_simplified` | On-the-fly vereinfacht | geodaten-ch | ❌ Nein |

**Regel:** Das Original-Polygon heisst immer `polygon`. Die Vereinfachung wird on-the-fly berechnet und ist temporär.

---

## 2. Tile-Cache System (3 Stufen)

### Überlegung: Warum Cache?

**Problem (aktuell):**
```
Jeder API-Aufruf:
1. STAC API aufrufen (bbox query)           ~200-500ms
2. Tile-ZIP herunterladen (~50-200MB)       ~5-10s
3. ZIP entpacken                            ~1-2s
4. GDB parsen                               ~1-3s
5. Gebäude finden                           ~100ms
6. temp_dir LÖSCHEN                         ← Tile weg!

TOTAL: ~8-15 Sekunden pro Abfrage
Ein Tile enthält ~100-500 Gebäude - wird aber jedes Mal neu geladen!
```

**Lösung: 3-Stufen-Cache**

```
┌─────────────────────────────────────────────────────────────────┐
│              TILE-CACHE SYSTEM (geodaten-ch)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STUFE 1: EGID → Gebäudedaten (SQLite)                         │
│  ─────────────────────────────────────                         │
│  SELECT * FROM building_geodata WHERE egid = 2242547           │
│  → Sofort verfügbar wenn schon mal abgefragt                   │
│  → ~1ms                                                         │
│                                                                 │
│  STUFE 2: Koordinaten → Tile-ID (Berechnung)                   │
│  ─────────────────────────────────────────────                 │
│  tile_id = lv95_to_tile_reference(e, n)                        │
│  → KEINE STAC API nötig! Formel existiert bereits.             │
│  → ~0ms                                                         │
│                                                                 │
│  STUFE 3: Tile-ID → Lokaler Pfad (Disk-Cache)                  │
│  ─────────────────────────────────────────────                 │
│  /app/data/tiles/{tile_id}.gdb/                                │
│  → Wenn vorhanden: direkt parsen                               │
│  → Wenn nicht: herunterladen + speichern                       │
│  → Nach Parsen: Alle Gebäude in Stufe 1 speichern              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Datenbank-Schema (tile_cache.db)

```sql
-- Welche Tiles sind lokal vorhanden?
CREATE TABLE tiles (
    tile_id TEXT PRIMARY KEY,      -- "1088-22"
    download_url TEXT,             -- STAC URL (für Re-Download)
    local_path TEXT,               -- "/app/data/tiles/1088-22.gdb"
    downloaded_at TEXT,
    file_size_mb REAL,
    buildings_count INTEGER
);

-- EGID → Tile-ID Mapping (nach Parsen befüllt)
CREATE TABLE egid_tile_index (
    egid INTEGER PRIMARY KEY,
    tile_id TEXT,
    FOREIGN KEY (tile_id) REFERENCES tiles(tile_id)
);
```

### Performance-Erwartung

| Szenario | Aktuell | Mit Cache |
|----------|---------|-----------|
| Erstes Gebäude im Tile | 8-15s | 8-15s (Download nötig) |
| Zweites Gebäude im selben Tile | 8-15s | **~50ms** |
| Bekanntes EGID (Stufe 1) | 8-15s | **~1ms** |
| 100 Gebäude im selben Areal | 17 Minuten | **~15s** |

### Tile-ID Berechnung (existiert bereits!)

```python
# swissbuildings3d_fetcher.py:67-99
def lv95_to_tile_reference(e: float, n: float) -> str:
    """
    Convert LV95 coordinates to swissBUILDINGS3D tile reference.
    z.B. (2600450, 1199830) → "1088-22"
    """
    e_km = int(e / 1000)
    n_km = int(n / 1000)
    main_e = (e_km - 2480) // 4
    main_n = (n_km - 1070) // 4
    sub_e = ((e_km - 2480) % 4) + 1
    sub_n = ((n_km - 1070) % 4) + 1
    main_tile = 1000 + main_e * 10 + main_n
    sub_tile = sub_n * 10 + sub_e
    return f"{main_tile}-{sub_tile}"
```

---

## 3. Polygon-Vereinfachung

### Zwei-Stufen-Prozess (Douglas-Peucker + Kollinear)

```
┌─────────────────────────────────────────────────────────────────┐
│  POLYGON ORIGINAL (26-175 Punkte)                               │
│  z.B. [[2600450.2, 1199800.5], [2600451.3, 1199801.2], ...]    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STUFE 1: Douglas-Peucker                                       │
│  Parameter: epsilon (Toleranz in Metern)                        │
│  Implementierung: geodienste.py:64-145                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STUFE 2: Kollineare Segmente verschmelzen                      │
│  Parameter: angle_tolerance_deg (Winkeltoleranz in Grad)        │
│  Implementierung: geodienste.py:148-179                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  POLYGON VEREINFACHT (4-12 Punkte)                              │
└─────────────────────────────────────────────────────────────────┘
```

### Parameter-Hierarchie

```
1. ProjectOverrides (geruestbau-app, pro Projekt)
   ├─ simplify_epsilon
   └─ simplify_angle_tolerance
   │
   └─► Fallback: Dynamisch nach Perimeter (geodaten-ch)
       ├─ >200m → epsilon=1.5
       ├─ >50m  → epsilon=0.8
       └─ sonst → epsilon=0.3
       │
       └─► Fallback: Globale Defaults
           ├─ DEFAULT_SIMPLIFY_EPSILON = 0.3
           └─ DEFAULT_COLLINEAR_ANGLE_TOLERANCE = 8.0
```

### Empfehlungen nach Gebäudegrösse

| Gebäudetyp | Perimeter | epsilon | angle_tolerance |
|------------|-----------|---------|-----------------|
| EFH (10×12m) | <50m | 0.3m | 5-8° |
| MFH/Gewerbe | 50-200m | 0.5-1.0m | 8-10° |
| Grossprojekt | >200m | 1.0-2.0m | 8-12° |

---

## 4. Datenfluss: Quelle → See

```
┌─────────────────────────────────────────────────────────────────┐
│  QUELLE: swissBUILDINGS3D (swisstopo STAC API)                 │
│  ───────────────────────────────────────────                   │
│  • GDB-Dateien mit 3D-Geometrie                                │
│  • Attribute: EGID, DACH_MAX, DACH_MIN, GELAENDEPUNKT          │
│  • Tiles: 1km × 1km Grid                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FETCHER: swissbuildings3d_fetcher.py (geodaten-ch)            │
│  ─────────────────────────────────────                         │
│  • Tile-Download + Caching (NEU)                               │
│  • GDB-Parsing (GeoPandas/Fiona)                               │
│  • 3D → 2D Projektion (Footprint)                              │
│  • Höhen-Berechnung (DACH_MAX - GELAENDEPUNKT)                 │
│  • Output: polygon (Original!), heights, egid                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CACHE: building_geodata.db (geodaten-ch)                      │
│  ────────────────────────────────────────                      │
│  • egid (PK)                                                   │
│  • polygon (JSON) ← ORIGINAL                                   │
│  • traufhoehe_m, firsthoehe_m, gebaeudehoehe_m                │
│  • area_m2, perimeter_m                                        │
│  • coord_e, coord_n (für Koordinaten-Lookup)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SERVICE: swissbuildings3d_service.py (geodaten-ch)            │
│  ──────────────────────────────────────                        │
│  • Cache-Lookup (Stufe 1)                                      │
│  • Koordinaten → Tile (Stufe 2)                                │
│  • Tile-Cache Check (Stufe 3)                                  │
│  • Polygon-Vereinfachung (on-the-fly)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  API: /api/v1/geruestbau/configurator/facades (geodaten-ch)    │
│  ──────────────────────────────────────────────────────────────│
│  Response:                                                      │
│  • polygon (Original)                                          │
│  • polygon_simplified (on-the-fly, mit Projekt-Parametern)     │
│  • sides (Fassaden aus vereinfachtem Polygon)                  │
│  • heights, roof, metadata                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND: geruestbau-app                                       │
│  ────────────────────────────                                  │
│  • ConfiguratorPage.tsx: Lädt Daten                            │
│  • ScaffoldConfigurator: Fassaden-Auswahl (vereinfacht)        │
│  • ScaffoldScene.tsx: 3D-View (Original)                       │
│  • ProjectOverrides: User kann Parameter anpassen              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Erweiterte Szenarien

### Überlegung: Nicht nur einzelne Gebäude

| Szenario | Beispiel | Herausforderung |
|----------|----------|-----------------|
| **Komplexes Gebäude** | Kirche mit Turm | Mehrere Teile, verschiedene Höhen |
| **Multi-Adresse** | Bollwerk 27/29 | Adress-Parsing, mehrere EGIDs |
| **Neubau** | FORUM UZH | Kein Gebäude in Geodaten |
| **Parzelle bekannt** | FL2456 | Nur Grundstück, kein Gebäude |

### Lösungsansätze (geodaten-ch)

```
┌─────────────────────────────────────────────────────────────────┐
│  KOMPLEXES GEBÄUDE                                              │
│  ─────────────────                                              │
│  fetch_building_complex_for_coordinates(e, n, radius_m=50)     │
│  → Findet ALLE Gebäude im Radius                               │
│  → Return: main_building + adjacent_buildings[]                │
│  → Status: ✅ Implementiert                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  MULTI-ADRESSE                                                  │
│  ─────────────                                                  │
│  Adress-Parser: "Bollwerk 27/29" → ["Bollwerk 27", "Bollwerk 29"]│
│  → Mehrfach-Geocoding                                          │
│  → Mehrere EGIDs sammeln                                       │
│  → Status: ✅ Implementiert (address_parser.py)                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  NEIGHBORS-API (Reihenhäuser, Nachbarn)                         │
│  ──────────────────────────────────────                         │
│  GET /api/v1/geruestbau/building/{egid}/neighbors               │
│  → Findet alle Nachbarn im Radius                              │
│  → Polygon-zu-Polygon Distanzberechnung                        │
│  → Richtung (N, NE, E, SE, S, SW, W, NW)                       │
│  → blocked_sides für Gerüstplanung                             │
│  → Status: ✅ Implementiert (geodata_service.py)               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PARZELLEN-API                                                  │
│  ────────────                                                   │
│  Layer: ch.swisstopo-vd.amtliche-vermessung                    │
│  → Grundstücksgrenzen, EGRID, Parzellennummer                  │
│  → Für Neubauten: Polygon aus Parzelle                         │
│  → Status: ✅ Implementiert (parzellen_service.py)             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  NEUBAU-SUPPORT                                                 │
│  ─────────────                                                  │
│  Manuelle Eingabe wenn keine Geodaten:                         │
│  → Polygon zeichnen auf Karte                                  │
│  → DXF/DWG hochladen                                           │
│  → Masse eingeben (L × B × H)                                  │
│  → Höhen aus Ausschreibung (Geschosse × 3.2m)                  │
│  → Status: ⚠️ Konzept in MULTI_OBJECT_WORKFLOW.md              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Datenstrukturen

### Backend: Building3D (geodaten-ch)

```python
@dataclass
class Building3D:
    # Identifikation
    egid: Optional[str] = None

    # Polygon (IMMER Original!)
    polygon: List[Tuple[float, float]] = field(default_factory=list)

    # Höhen
    trauf_height_m: Optional[float] = None
    first_height_m: Optional[float] = None
    building_height_m: Optional[float] = None

    # Fassaden (on-the-fly aus vereinfachtem Polygon)
    sides: List[dict] = field(default_factory=list)
    perimeter_m: Optional[float] = None
    area_m2: Optional[float] = None

    # Qualität
    confidence: float = 1.0
    height_source: str = "unknown"
```

### Frontend: Geodata (geruestbau-app)

```typescript
interface Geodata {
  egid: string;
  polygon?: [number, number][];      // ORIGINAL
  traufhoehe_m?: number;
  firsthoehe_m?: number;
  gebaeudehoehe_m?: number;
  area_m2?: number;
  perimeter_m?: number;
}

interface ProjectOverrides {
  polygon?: number[][];              // Manuell angepasst
  traufhoehe_m?: number;
  firsthoehe_m?: number;
  simplify_epsilon?: number;         // → geodaten-ch
  simplify_angle_tolerance?: number; // → geodaten-ch
}
```

---

## 7. Polygon-Benennung (Refactoring abgeschlossen ✅)

### Neues Konzept (03.01.2026)

| Schicht | Attribut | Bedeutung |
|---------|----------|-----------|
| Fetcher | `polygon` | **ORIGINAL** aus swissBUILDINGS3D |
| Fetcher | `sides` | Berechnet aus on-the-fly vereinfachtem Polygon |
| Service | `polygon` | **ORIGINAL** |
| Service | `sides_from_simplified` | Flag: sides sind aus vereinfachtem Polygon |
| API | `polygon` | **ORIGINAL** |
| API | `sides` | Für Fassaden-Auswahl (aus vereinfachtem Polygon) |

### Neuer Service: polygon_simplifier.py

```python
from app.services.polygon_simplifier import simplify_building_polygon

result = simplify_building_polygon(polygon, epsilon=0.5, angle_tolerance=8.0)
# result.polygon          - Vereinfachtes Polygon
# result.sides            - Berechnete Fassaden
# result.perimeter_m      - Umfang
# result.epsilon_used     - Verwendeter Epsilon-Wert
```

### Entfernte Attribute

| Attribut | Status |
|----------|--------|
| `polygon_original` | ❌ Entfernt |
| `polygon_simplified` (Boolean) | ❌ Entfernt |
| `polygon_simplify_epsilon` | ❌ Entfernt |
| `polygon_point_count_original` | → `polygon_point_count` |

### Frontend (TODO)

| Datei | Attribut | Status |
|-------|----------|--------|
| scaffold.types.ts | `buildingPolygonOriginal` | ⏳ Noch zu entfernen |

---

## 8. Referenz: Code-Stellen

| Komponente | Datei | Zuständigkeit |
|------------|-------|---------------|
| Tile-ID Berechnung | `swissbuildings3d_fetcher.py:67-99` | geodaten-ch |
| Polygon-Vereinfachung | `polygon_simplifier.py` | geodaten-ch (NEU) |
| Douglas-Peucker | `polygon_simplifier.py:216-272` | geodaten-ch |
| Kollineare Segmente | `polygon_simplifier.py:275-327` | geodaten-ch |
| Fassaden-Berechnung | `polygon_simplifier.py:131-183` | geodaten-ch |
| Building3D | `swissbuildings3d_service.py:36-84` | geodaten-ch |
| BuildingGeodata Cache | `geodata_service.py:21-49` | geodaten-ch |
| ProjectOverrides | `project.ts:29-36` | geruestbau-app |
| 3D-Scene | `ScaffoldScene.tsx:797` | geruestbau-app |

---

## 9. Offene Punkte (Roadmap)

| # | Aufgabe | Zuständigkeit | Status |
|---|---------|---------------|--------|
| 1 | Tile-Cache System | geodaten-ch | ✅ Done |
| 2 | EGID → Tile-ID Index | geodaten-ch | ✅ Done |
| 3 | lv95_to_tile_reference() nutzen | geodaten-ch | ✅ Done |
| 4 | Background Prefetch (alle Gebäude im Tile) | geodaten-ch | ✅ Done |
| 5 | Neighbors-API (Reihenhäuser) | geodaten-ch | ✅ Done |
| 6 | Adress-Parser (Multi-Adresse) | geodaten-ch | ✅ Done |
| 7 | Polygon-Benennung vereinheitlichen | geodaten-ch | ✅ Done |
| 8 | Vereinfachung → on-the-fly Service | geodaten-ch | ✅ Done |
| 9 | polygon_original entfernen | geodaten-ch | ✅ Done |
| 10 | API Response anpassen | geodaten-ch | ✅ Done |
| 11 | ProjectOverrides anwenden | geodaten-ch | ⏳ |
| 12 | buildingPolygonOriginal entfernen | geruestbau-app | ⏳ |
| 13 | Parzellen-API | geodaten-ch | ✅ Done |
| 14 | Neubau-Support | geruestbau-app | ⏳ |

---

## 10. Implementierungsdetails (03.01.2026)

### Tile-Cache (Neu)

**Dateien:**
- `tile_cache.py` - TileCacheService mit 3-Stufen-Cache
- `swissbuildings3d_fetcher.py` - Integriert Tile-Cache

**Speicherorte:**
```
backend/app/data/
├── tiles.db          # Tile-Index + EGID-Mapping
└── tiles/            # GDB-Verzeichnisse
    ├── 1088-22.gdb/  # Bern Zentrum
    ├── 1088-23.gdb/  # Bern Nord
    └── ...
```

**API:**
```python
from app.services.tile_cache import get_tile_cache, lv95_to_tile_id

cache = get_tile_cache()

# Tile-ID berechnen (O(1), keine API)
tile_id = lv95_to_tile_id(2600450, 1199830)  # → "1088-22"

# Cache-Lookup
path = cache.get_tile_path(tile_id)  # → Path oder None

# Stats
stats = cache.get_stats()
# {"tile_count": 5, "egid_count": 847, "total_size_mb": 123.5, ...}
```

**Response enthält jetzt:**
```json
{
  "polygon": [...],
  "tile_id": "1088-22",
  "cache_hit": true
}
```

### Background Prefetch (Neu)

**Problem:** Tile ist gecacht, aber jedes Gebäude muss einzeln geparst werden (~50ms).

**Lösung:** Nach dem ersten Fetch werden ALLE Gebäude im Tile im Hintergrund geladen.

```
User fragt Gebäude A
    ↓
Gebäude A sofort zurück (~50ms für Parsing)
    ↓ (parallel, im Hintergrund)
schedule_prefetch(tile_id, gdb_path, exclude_egid=A)
    ↓
Alle ~100-500 Gebäude im Tile → building_geodata.db
    ↓
Nächste Anfrage im selben Tile: ~1ms (DB-Lookup)
```

**Dateien:**
- `tile_prefetch.py` - Background-Job
- Integration in `swissbuildings3d_fetcher.py`

**API:**
```python
from app.services.tile_prefetch import get_prefetch_status

# Status laufender Jobs
status = get_prefetch_status()
# {"in_progress": ["1088-22"], "count": 1}
```

**Performance nach Prefetch:**
| Szenario | Ohne Prefetch | Mit Prefetch |
|----------|---------------|--------------|
| Erstes Gebäude | ~50ms | ~50ms |
| Zweites Gebäude | ~50ms | **~1ms** |
| 100 Gebäude | ~5s | **~100ms** |

### Neighbors-API (Neu)

**Problem:** Bei Reihenhäusern können nur 2 von 4 Seiten eingerüstet werden.

**Lösung:** Erkennung angrenzender Gebäude via Polygon-Distanz.

**Dateien:**
- `geodata_service.py` - `get_neighbors()` Methode
- `geruestbau.py` - API-Endpunkt

**API:**
```python
GET /api/v1/geruestbau/building/{egid}/neighbors
    ?radius_m=10           # 0=angrenzend, 5=nah, 10=Kontext
    &include_polygons=true # Für 3D-View
```

**Response:**
```json
{
  "target_egid": "123456",
  "target_polygon": [[2600000, 1200000], ...],
  "neighbors": [
    {
      "egid": "123457",
      "distance_m": 0.0,
      "direction": "E",
      "polygon": [...],
      "traufhoehe_m": 8.5
    }
  ],
  "blocked_sides": ["E", "W"],
  "query_time_ms": 5.2
}
```

**Distanz-Berechnung:**
- Punkt-zu-Segment Distanz für alle Polygonpunkte
- `distance_m < 0.5` = direkt angrenzend → blockierte Seite

**Richtungsberechnung (Fassaden-basiert):**

Bei angrenzenden Gebäuden (< 1m Distanz) wird die Richtung basierend auf der
blockierten Fassade berechnet, nicht nur auf Schwerpunkt-Differenz.

```
┌─────────────────────────────────────────────────────────────────────┐
│              RICHTUNGSBERECHNUNG BEI NACHBARN                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Situation: Reihenhäuser mit überlappenden Polygonen                │
│                                                                     │
│  Problem mit Schwerpunkt-Methode:                                   │
│  ┌───────────────────────────────────────────────┐                  │
│  │     ┌────────┐ ┌────────┐                     │                  │
│  │     │ Haus A │ │ Haus B │                     │                  │
│  │     │   •    │ │   •    │  ← Schwerpunkte     │                  │
│  │     │  (5,6) │ │ (5.4,6)│    nur 0.4m apart!  │                  │
│  │     └────────┘ └────────┘                     │                  │
│  │                                               │                  │
│  │  → Schwerpunkt-Differenz ergibt E/S statt E   │                  │
│  └───────────────────────────────────────────────┘                  │
│                                                                     │
│  Lösung: Fassaden-basierte Berechnung                               │
│  ┌───────────────────────────────────────────────┐                  │
│  │  1. Finde die Kante am nächsten zum Nachbarn  │                  │
│  │  2. Berechne Normalvektor der Kante           │                  │
│  │  3. Wähle Richtung via Dot-Product            │                  │
│  │                                               │                  │
│  │     ┌────────┐→┌────────┐                     │                  │
│  │     │ Haus A │→│ Haus B │                     │                  │
│  │     │        │→│        │  → Normal zeigt E   │                  │
│  │     └────────┘→└────────┘                     │                  │
│  └───────────────────────────────────────────────┘                  │
│                                                                     │
│  Spezialfall: Schwerpunkte < 2m auseinander                         │
│  → Vereinfachte 4-Richtungen (N/S/E/W) basierend auf                │
│    dominanter Achse (dx vs dy)                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Funktionen:**
- `_calculate_facade_direction()` - Fassaden-basierte Richtung
- `_calculate_direction()` - Schwerpunkt-basiert (Fallback)

**Tests:** `tests/test_neighbors.py::TestCalculateFacadeDirection` (10 Tests)

**Anwendungsfall Reihenhaus:**
```
Knospenweg 4 (Mitte der Reihe)
├─ Nachbar Ost: Knospenweg 6 (distance: 0.0m) → blocked
├─ Nachbar West: Knospenweg 2 (distance: 0.0m) → blocked
├─ Nord: Frei → Gerüst möglich
└─ Süd: Frei → Gerüst möglich
```

### Adress-Parser & Multi-Building Mode (Implementiert 03.01.2026)

**Problem:** Ganze Häuserzeilen (z.B. "Knospenweg 2-10") sollen auf einmal erfasst werden können.

**Lösung:** Parser für Adressbereiche mit Geocoding-Integration und Multi-Building UI.

**Dateien:**
```
Backend:
├── app/services/address_parser.py     # Parser-Logik
├── app/routers/geruestbau.py          # API-Endpunkte
└── app/api/geruestbau.py              # API-Client Typen

Frontend:
├── src/api/geruestbau.ts              # API-Client (resolveAddressRange, getBuildingPolygon)
└── src/pages/ConfiguratorPage.tsx     # Multi-Building UI & Selection
```

**Unterstützte Formate:**

| Format | Beispiel | Ergebnis | Beschreibung |
|--------|----------|----------|--------------|
| Range (gerade) | `2-10` | [2, 4, 6, 8, 10] | Automatische Schrittweite 2 |
| Range (ungerade) | `1-9` | [1, 3, 5, 7, 9] | Automatische Schrittweite 2 |
| Range (gemischt) | `1-4` | [1, 2, 3, 4] | Schrittweite 1 |
| Slash-Notation | `27/29` | [27, 29] | Explizite Liste |
| Komma-Liste | `1, 3, 5` | [1, 3, 5] | Explizite Liste |

**Backend API:**

```python
# Nur Parsing (ohne Geocoding)
GET /api/v1/geruestbau/address/parse?address=Knospenweg 2-10, Bern

# Mit Geocoding → EGIDs + Koordinaten
GET /api/v1/geruestbau/address/resolve?address=Knospenweg 2-10, Bern
```

**Response (resolve):**
```json
{
  "parsed": {
    "street": "Knospenweg",
    "city": "Bern",
    "zip": "3006",
    "numbers": ["2", "4", "6", "8", "10"],
    "range_type": "range"
  },
  "buildings": [
    {
      "address": "Knospenweg 2, 3006 Bern",
      "egid": "1234567",
      "coordinates": {"e": 2601234, "n": 1200567}
    },
    {
      "address": "Knospenweg 4, 3006 Bern",
      "egid": "1234568",
      "coordinates": {"e": 2601240, "n": 1200570}
    }
  ],
  "building_count": 5,
  "error_count": 0,
  "errors": []
}
```

**Frontend Integration (ConfiguratorPage.tsx):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTI-BUILDING FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User gibt Adresse ein: "Knospenweg 2-10, Bern"             │
│     ↓                                                           │
│  2. isAddressRange() erkennt Range-Pattern                     │
│     ↓                                                           │
│  3. geruestbauApi.resolveAddressRange() → Backend              │
│     ↓                                                           │
│  4. UI zeigt Gebäude-Auswahl (Checkboxen):                     │
│     ┌─────────────────────────────────────┐                    │
│     │ ☑ Knospenweg 2, Bern  (EGID: 123)  │                    │
│     │ ☑ Knospenweg 4, Bern  (EGID: 124)  │                    │
│     │ ☐ Knospenweg 6, Bern  (EGID: 125)  │                    │
│     │ ☑ Knospenweg 8, Bern  (EGID: 126)  │                    │
│     │ ☑ Knospenweg 10, Bern (EGID: 127)  │                    │
│     └─────────────────────────────────────┘                    │
│     [Alle auswählen]  [4 Gebäude laden]                        │
│     ↓                                                           │
│  5. Bei Auswahl > 1 Gebäude:                                   │
│     a) Erstes Gebäude → Hauptgebäude (fetchBuildingData)       │
│     b) Weitere → additionalBuildings (getBuildingPolygon)      │
│     ↓                                                           │
│  6. ScaffoldConfigurator erhält:                               │
│     - buildingPolygon (Hauptgebäude)                           │
│     - additionalBuildings[] (weitere Polygone für 3D)          │
│     ↓                                                           │
│  7. 3D-View zeigt alle Gebäude nebeneinander                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**State-Management (ConfiguratorPage):**

```typescript
// Multi-Building State
const [addressRangeData, setAddressRangeData] = useState<AddressRangeResponse | null>(null);
const [selectedBuildings, setSelectedBuildings] = useState<AddressRangeBuilding[]>([]);
const [isMultiMode, setIsMultiMode] = useState(false);
const [additionalBuildings, setAdditionalBuildings] = useState<MultiBuildingData[]>([]);
```

**Anwendungsfall Reihenhäuser:**
```
User: "Knospenweg 2-10, Bern"
→ 5 Reihenhäuser werden erkannt
→ User wählt 3 aus (z.B. 4, 6, 8)
→ Knospenweg 4 wird als Hauptgebäude geladen
→ Knospenweg 6 + 8 werden als Zusatz-Polygone geladen
→ 3D-View zeigt alle 3 Gebäude
→ Gerüst kann für alle 3 konfiguriert werden
```

**Kombination mit Neighbors-API:**
```
Bei Reihenhäusern werden automatisch blockierte Seiten erkannt:
- Knospenweg 4: Blockiert Ost (→ Nr. 6), Blockiert West (→ Nr. 2)
- Nur Nord + Süd sind gerüstbar
```

### Parzellen-API (Neu 03.01.2026)

**Problem:** Bei Neubauten existiert noch kein Gebäude in swissBUILDINGS3D.

**Lösung:** Grundstücksgrenzen aus der amtlichen Vermessung als Baufeld nutzen.

**Dateien:**
- `parzellen_service.py` - Service für Grundstücksdaten

**API:**
```python
# Parzelle an Koordinaten
GET /api/v1/geruestbau/parzelle/at?e=2600450&n=1199830

# Parzelle per EGRID
GET /api/v1/geruestbau/parzelle/by-egrid/CH280652308630

# Parzelle für Adresse (mit Neubau-Check)
GET /api/v1/geruestbau/parzelle/for-address?address=Bundesplatz 3, Bern
```

**Response (for-address):**
```json
{
  "geocoding": {
    "input": "Neubaustrasse 10, Bern",
    "matched_address": "Neubaustrasse 10, 3011 Bern",
    "egid": null,
    "coordinates": {"lv95_e": 2600450, "lv95_n": 1199830}
  },
  "parzelle": {
    "egrid": "CH280652308630",
    "number": "1234",
    "canton": "BE",
    "polygon": [[e1,n1], [e2,n2], ...],
    "area_m2": 850.5
  },
  "has_building": false,
  "neubau_possible": true
}
```

**Anwendungsfall Neubau:**
```
1. User gibt Adresse ein → Geocoding findet Koordinaten
2. Parzelle wird geladen → EGRID, Grundstücksgrenzen
3. has_building = false → Neubau-Modus aktiviert
4. Parzellen-Polygon als Baufeld-Grenze
5. User zeichnet Gebäude oder lädt DXF hoch
```

---

## 11. Teststrategie (03.01.2026)

### Architektur-basierte Testszenarien

Die Tests müssen die 3-Stufen-Cache-Architektur systematisch abdecken:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CACHE-STUFEN & TESTFÄLLE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STUFE 1: EGID → Gebäudedaten (building_geodata.db)            │
│  ─────────────────────────────────────────────                 │
│  • TC-01: Bekanntes EGID → Sofort aus DB (~1ms)                │
│  • TC-02: Unbekanntes EGID → Weiter zu Stufe 2                 │
│                                                                 │
│  STUFE 2: Koordinaten → Tile-ID (Berechnung)                   │
│  ─────────────────────────────────────────────                 │
│  • TC-03: LV95-Koordinaten → korrekte Tile-ID                  │
│  • TC-04: LV03-Koordinaten → automatische Konvertierung        │
│  • TC-05: Edge-Cases (Tile-Grenzen, Südwest-Ecke)              │
│                                                                 │
│  STUFE 3: Tile-ID → Lokaler Pfad (Disk-Cache)                  │
│  ─────────────────────────────────────────────                 │
│  • TC-06: Tile im Cache → GDB parsen (~50ms)                   │
│  • TC-07: Tile NICHT im Cache → STAC Download (~8-15s)         │
│  • TC-08: Tile gelöscht aber DB-Entry → Cleanup & Re-Download  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Test-Kategorien

#### A) Unit Tests (tests/test_tile_cache.py)

| Test | Beschreibung | Erwartetes Ergebnis |
|------|--------------|---------------------|
| `test_tile_id_calculation` | Koordinaten → Tile-ID | Korrekte Tile-IDs für bekannte Orte |
| `test_lv03_to_lv95_conversion` | LV03 wird zu LV95 konvertiert | Gleiche Tile-ID für beide Systeme |
| `test_service_initialization` | TileCacheService startet | Singleton, DB erstellt |
| `test_register_egid_function` | EGID im Index speichern | Kann wieder abgerufen werden |

#### B) Integrationstests (tests/test_integration.py - NEU)

```
┌─────────────────────────────────────────────────────────────────┐
│  TEST-SZENARIO 1: Cold Start (kein Cache)                      │
├─────────────────────────────────────────────────────────────────┤
│  Input:  Adresse "Bundesplatz 3, 3011 Bern"                    │
│  Ablauf:                                                        │
│    1. Geocoding → Koordinaten (2600450, 1199830)               │
│    2. lv95_to_tile_id → "1088-22"                              │
│    3. get_tile_path("1088-22") → None (nicht im Cache)         │
│    4. STAC API → Tile herunterladen                            │
│    5. GDB parsen → Gebäude finden                              │
│    6. store_tile() → Cache speichern                           │
│    7. Prefetch starten (Background)                            │
│  Erwartet:                                                      │
│    - polygon: nicht leer                                        │
│    - traufhoehe_m: > 0                                         │
│    - cache_hit: false                                          │
│    - tile_id: "1088-22"                                        │
│    - Dauer: 8-15s                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TEST-SZENARIO 2: Warm Cache (zweite Anfrage im Tile)          │
├─────────────────────────────────────────────────────────────────┤
│  Input:  Adresse "Kramgasse 49, 3011 Bern" (selbes Tile!)      │
│  Ablauf:                                                        │
│    1. Geocoding → Koordinaten                                   │
│    2. lv95_to_tile_id → "1088-22" (wie Bundeshaus!)            │
│    3. get_tile_path("1088-22") → Path (im Cache!)              │
│    4. GDB parsen → anderes Gebäude finden                      │
│  Erwartet:                                                      │
│    - polygon: nicht leer                                        │
│    - cache_hit: true (Tile war im Cache)                       │
│    - Dauer: ~50ms (kein Download)                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TEST-SZENARIO 3: EGID-Index Hit (nach Prefetch)               │
├─────────────────────────────────────────────────────────────────┤
│  Voraussetzung: Prefetch für Tile "1088-22" abgeschlossen      │
│  Input:  EGID 2242547 (Bundeshaus)                             │
│  Ablauf:                                                        │
│    1. get_tile_for_egid(2242547) → "1088-22"                   │
│    2. Direkt aus building_geodata.db laden                     │
│  Erwartet:                                                      │
│    - Daten sofort verfügbar                                    │
│    - Dauer: ~1ms                                               │
└─────────────────────────────────────────────────────────────────┘
```

#### C) End-to-End Tests (scripts/test_simap_import_flow.py)

| Phase | Test | Status 03.01.2026 | Problem |
|-------|------|-------------------|---------|
| Import | Felder parsen | ✅ 20/20 | - |
| Geocoding | Adresse → Koordinaten | ⚠️ 19/20 | TC-010 keine Ergebnisse |
| Geodaten | SmartBuildingService | ❌ 0/20 | GeocodingResult hat kein `egid` |
| Polygon | swissBUILDINGS3D | ❌ 0/20 | Nicht erreicht |
| Höhen | swissBUILDINGS3D | ❌ 0/20 | Nicht erreicht |

### Bekannte Probleme (03.01.2026)

#### BUG: GeocodingResult.egid fehlt

```python
# PROBLEM in test_simap_import_flow.py (Zeile 156-164):
geo = await self.swisstopo.geocode(address)
if geo and geo.coordinates:
    result.geocode_success = True
    # ... aber result.egid_found wird nie gesetzt!

# PROBLEM in SmartBuildingService (Zeile 461):
if hasattr(geo, 'egid') and geo.egid:  # GeocodingResult HAT kein egid!
```

**Ursache:** `GeocodingResult` (schemas.py:87) enthält:
- `input_address`, `matched_address`, `confidence`
- `coordinates` (Coordinates)
- `terrain` (Optional)
- **KEIN** `egid`!

**EGID kommt aus GWR:** Das EGID wird erst in Phase 2 über `identify_buildings()` geholt.

#### Datenfluss-Korrektur

```
AKTUELL (falsch erwartet):
  Geocoding → egid, coordinates

RICHTIG (wie implementiert):
  Geocoding → coordinates
  GWR-Lookup (identify_buildings) → egid, floors, category
```

### Test-Fixtures (Bekannte Test-Daten)

| Ort | Koordinaten | Tile-ID | EGID | Beschreibung |
|-----|-------------|---------|------|--------------|
| Bundeshaus | 2600450, 1199830 | 1088-22 | 2242547 | Komplexes Gebäude |
| Kramgasse 49 | ~2600656, 1199497 | 1088-22 | - | Selbes Tile wie Bundeshaus |
| Zürich HB | 2683200, 1247700 | 1144-34 | - | Anderes Tile |
| Basel Marktplatz | 2611200, 1267900 | 1094-44 | - | Weiteres Tile |

### Empfohlene Test-Reihenfolge

```
1. Unit Tests (pytest tests/test_tile_cache.py)
   → Tile-ID Berechnung, Cache-Operationen

2. Address Parser Tests (pytest tests/test_address_parser.py)
   → Range-Parsing, API-Endpunkte, Resolve-Service

3. Service Tests (pytest tests/test_swissbuildings3d.py)
   → fetch_building_polygon_for_coordinates()

4. Integration Tests (pytest tests/test_smart_building.py)
   → SmartBuildingService.collect_all_data()

5. E2E Tests (python scripts/test_simap_import_flow.py)
   → Voller Flow: Import → Geocoding → Geodaten
```

### Address-Range Parser Tests (Neu 03.01.2026)

Implementiert in `tests/test_address_parser.py` - **35 Tests, alle bestanden**.

#### Testklassen-Übersicht

| Klasse | Tests | Beschreibung |
|--------|-------|--------------|
| `TestParseNumberRange` | 7 | Hausnummern-Parsing (Range, Slash, Single) |
| `TestDetermineStep` | 3 | Schrittweite-Bestimmung (gerade/ungerade) |
| `TestParseAddressRange` | 6 | Vollständige Adress-Parsing |
| `TestEdgeCases` | 6 | Edge Cases (umgekehrt, gleich, gross) |
| `TestAddressPatterns` | 5 | Schweizer Adress-Muster |
| `TestRealWorldAddresses` | 3 | Echte Adressen (Knospenweg, Bollwerk) |
| `TestAPIIntegration` | 3 | API-Endpunkte mit TestClient |
| `TestResolveService` | 2 | Async Service mit Mocking |

#### Test-Details

**TestParseNumberRange:**
```python
test_simple_range_even      # "2-10" → [2, 4, 6, 8, 10]
test_simple_range_odd       # "1-9" → [1, 3, 5, 7, 9]
test_mixed_range            # "1-4" → [1, 2, 3, 4]
test_slash_notation         # "27/29" → [27, 29]
test_single_number          # "15" → [15]
test_number_with_suffix     # "15a" → [15a]
test_range_with_spaces      # "2 - 10" → [2, 4, 6, 8, 10]
```

**TestAddressPatterns (Schweizer Strassenmuster):**
```python
test_strasse_ending         # Bahnhofstrasse → korrekt geparst
test_gasse_ending           # Kramgasse → korrekt geparst
test_weg_ending             # Knospenweg → korrekt geparst
test_platz_ending           # Bundesplatz → SINGLE erkannt
test_address_with_canton    # "St. Gallen" → korrekt als Stadt
```

**TestRealWorldAddresses:**
```python
test_knospenweg_reihenhaus  # Knospenweg 2-10, 3027 Bern
  → street="Knospenweg", plz="3027", numbers=[2,4,6,8,10]

test_bollwerk_double        # Bollwerk 27/29, 3011 Bern
  → range_type=EXPLICIT, numbers=[27, 29]

test_zurich_bahnhof         # Bahnhofstrasse 46-50, 8001 Zürich
  → city="Zürich", plz="8001", numbers=[46,48,50]
```

**TestAPIIntegration (mit FastAPI TestClient):**
```python
test_parse_endpoint         # GET /api/v1/geruestbau/address/parse
test_parse_single_address   # Einzelne Adresse → range_type="single"
test_parse_slash_notation   # Slash → range_type="explicit"
```

**TestResolveService (Async mit Mocking):**
```python
test_resolve_returns_structure   # Korrekte Response-Struktur
test_resolve_handles_not_found   # Fehlerbehandlung
```

#### Ausführen der Tests

```bash
# Alle Address-Parser Tests
pytest tests/test_address_parser.py -v

# Nur API-Integration Tests
pytest tests/test_address_parser.py::TestAPIIntegration -v

# Nur Async Tests
pytest tests/test_address_parser.py::TestResolveService -v
```

#### Abhängigkeiten

```python
# pytest.ini oder pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"

# Benötigte Packages
pytest
pytest-asyncio
fastapi[test]  # für TestClient
```

---

## 12. Offene Punkte (Aktualisiert 03.01.2026)

| # | Aufgabe | Zuständigkeit | Status |
|---|---------|---------------|--------|
| 1-10 | (siehe Abschnitt 9) | - | ✅ Done |
| 11 | ProjectOverrides anwenden | geodaten-ch | ⏳ |
| 12 | buildingPolygonOriginal entfernen | geruestbau-app | ⏳ |
| 13 | Parzellen-API | geodaten-ch | ✅ Done |
| 14 | Neubau-Support | geruestbau-app | ⏳ |
| 15 | Test-Script fixen (EGID-Lookup) | geodaten-ch | ✅ Done |
| 16 | Integrationstests erstellen | geodaten-ch | 🔴 Offen |
| 17 | Test-Fixtures dokumentieren | geodaten-ch | 🔴 Offen |
| **18** | **Address-Range Parser + Multi-Building UI** | beide | ✅ Done |
| **19** | **Neighbors-API + Blockierte Fassaden** | beide | ✅ Done |
| **20** | **Polygon-Vereinfachungs-Slider** | beide | ✅ Done |

---

## 13. Frontend-Kompatibilität (03.01.2026)

### Status: ✅ Kompatibel

Das Frontend (`geruestbau-app`) ist bereits mit der neuen Backend-Architektur kompatibel:

```
Frontend (types.ts)          Backend (Response)
────────────────────         ──────────────────
SmartBuildingData            /api/v1/smart-building/data
├─ egid                      ├─ egid
├─ polygon                   ├─ polygon (ORIGINAL)
├─ traufhoehe_m              ├─ traufhoehe_m
├─ firsthoehe_m              ├─ firsthoehe_m
├─ building_name             ├─ building_name
└─ zones                     └─ zones
```

**Konvertierung:** `smartToScaffoldingData()` in `types.ts` wandelt das neue Format für Rückwärtskompatibilität.

### Polygon-Namenskonvention (Aktuell)

| Schicht | Attribut | Bedeutung | Persistiert |
|---------|----------|-----------|-------------|
| Backend | `polygon` | **ORIGINAL** aus swissBUILDINGS3D | ✅ Ja |
| Backend | `polygon_simplified` | On-the-fly berechnet (Temporär) | ❌ Nein |
| Frontend | `polygon` | = Backend `polygon` | Via API |
| Frontend | `buildingPolygonOriginal` | **⚠️ Veraltet, zu entfernen** | Lokal |

### Frontend-Todo-Liste

| # | Aufgabe | Datei | Priorität |
|---|---------|-------|-----------|
| F1 | `buildingPolygonOriginal` entfernen | scaffold.types.ts | 🔴 Hoch |
| F2 | `polygon_simplified` Boolean entfernen | types.ts | 🟡 Mittel |
| F3 | Vereinfachung via API-Parameter nutzen | App.tsx | 🟡 Mittel |
| F4 | Neubau-Modus implementieren | ConfiguratorPage.tsx | 🔵 Niedrig |

### F1: buildingPolygonOriginal entfernen

**Problem:** In `scaffold.types.ts` existiert noch:
```typescript
buildingPolygonOriginal?: number[][];  // ← Veraltet!
```

**Lösung:** Entfernen, da Backend immer das Original in `polygon` liefert.

### F2: polygon_simplified Boolean entfernen

**Problem:** In `types.ts`:
```typescript
polygon_simplified?: boolean;  // ← Nicht mehr sinnvoll
```

**Lösung:** Entfernen. Vereinfachung wird on-the-fly berechnet, nicht persistiert.

### F3: Vereinfachung via API-Parameter

**Aktuell:** Frontend speichert `polygon` und `polygon_simplified` lokal.

**Neu:** Backend-API Parameter für on-the-fly Vereinfachung:
```
GET /api/v1/smart-building/data?address=...
    &simplify_epsilon=0.5
    &simplify_angle_tolerance=8.0
```

Response enthält dann:
```json
{
  "polygon": [[...], ...],           // Original
  "polygon_simplified": [[...], ...] // On-the-fly berechnet
}
```

**Vorteil:** Keine doppelte Speicherung, konsistente Vereinfachung.

### F4: Neubau-Modus (Parzellen-API)

Wenn `/api/v1/geruestbau/parzelle/for-address` `has_building: false` zurückgibt:

1. Frontend aktiviert Neubau-Modus
2. Parzellen-Polygon als Baufeld anzeigen
3. User kann Gebäude zeichnen oder DXF hochladen
4. Manuelle Höheneingabe (Geschosse × 3.2m)

### Datenfluss-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND → BACKEND → FRONTEND                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User gibt Adresse ein                                   │
│     ↓                                                       │
│  2. GET /api/v1/smart-building/data?address=...             │
│     ↓                                                       │
│  3. Backend: SmartBuildingService.collect_all_data()        │
│     ├─ Geocoding → Koordinaten                              │
│     ├─ GWR → EGID, Geschosse                                │
│     ├─ swissBUILDINGS3D → polygon (ORIGINAL), Höhen         │
│     └─ Claude → building_name, zones                        │
│     ↓                                                       │
│  4. Response: BuildingDataBundle (flat JSON)                │
│     ↓                                                       │
│  5. Frontend: smartToScaffoldingData(response)              │
│     ├─ polygon → buildingPolygon                            │
│     ├─ traufhoehe_m → buildingHeight                        │
│     └─ (Konvertierung für Rückwärtskompatibilität)          │
│     ↓                                                       │
│  6. ScaffoldConfigurator: Fassaden-Auswahl                  │
│     ↓                                                       │
│  7. ScaffoldScene: 3D-Visualisierung                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Keine Änderungen nötig für

- **App.tsx**: Nutzt bereits `/api/v1/smart-building/data`
- **SmartBuildingData Interface**: Struktur passt
- **3D-Viewer**: Nutzt `polygon` korrekt

---

## 14. Neue Backend-APIs (Vollständige Übersicht)

### 14.1 Parzellen-API (Neubau-Support)

**Zweck:** Gebäude planen wo noch keins existiert (Neubau, Abbruch+Neubau)

| Endpunkt | Parameter | Response |
|----------|-----------|----------|
| `GET /api/v1/geruestbau/parzelle/at` | `e`, `n`, `include_geometry` | Parzelle an Koordinate |
| `GET /api/v1/geruestbau/parzelle/by-egrid/{egrid}` | EGRID | Parzellen-Details |
| `GET /api/v1/geruestbau/parzelle/for-address` | `address` | **Inkl. `has_building` Flag!** |

**Anwendungsfall:**
```
1. User sucht "Neubaustrasse 10, Bern"
2. Geocoding findet Koordinaten
3. has_building = false → Kein Gebäude in swissBUILDINGS3D
4. Frontend: "Neubau-Modus" aktivieren
5. Parzellen-Polygon als Baufeld anzeigen
6. User zeichnet Gebäude oder lädt DXF hoch
```

### 14.2 Neighbors-API (Nachbargebäude)

**Zweck:** Blockierte Fassaden erkennen, 3D-Kontext zeigen

| Endpunkt | Parameter | Response |
|----------|-----------|----------|
| `GET /api/v1/geruestbau/building/{egid}/neighbors` | `radius_m` (0/5/10), `include_polygons` | Nachbarn + `blocked_sides` |

**Response-Beispiel:**
```json
{
  "target_egid": "123456",
  "neighbors": [
    {"egid": "123457", "distance_m": 0.0, "direction": "E", "polygon": [...]}
  ],
  "blocked_sides": ["E", "W"]  // ← Für Gerüstplanung!
}
```

**Anwendungsfall:**
- Reihenhaus: Nur 2 von 4 Seiten eingerüstbar
- 3D-View: Nachbarn mit Kontext zeigen
- Slider: 0m (angrenzend), 5m (nah), 10m (Kontext)

### 14.3 Adress-Parser (Multi-Adressen)

**Zweck:** Ganze Häuserzeile auf einmal erfassen

| Endpunkt | Parameter | Response |
|----------|-----------|----------|
| `GET /api/v1/geruestbau/address/parse` | `address` | Nur Parsing |
| `GET /api/v1/geruestbau/address/resolve` | `address` | Parsing + Geocoding aller Adressen |

**Unterstützte Formate:**
```
"Knospenweg 2-10"     → [2, 4, 6, 8, 10]     (gerade Schritte)
"Kramgasse 27/29"     → [27, 29]             (explizit)
"Hauptstr. 1, 3, 5"   → [1, 3, 5]            (Liste)
```

**Response (resolve):**
```json
{
  "parsed": {"street": "Knospenweg", "numbers": ["2","4","6","8","10"]},
  "buildings": [
    {"address": "Knospenweg 2, Bern", "egid": "123456"},
    {"address": "Knospenweg 4, Bern", "egid": "123457"},
    ...
  ],
  "building_count": 5
}
```

### 14.4 Building Environment API

**Zweck:** Vollständiger Kontext eines Gebäudes

| Endpunkt | Parameter | Response |
|----------|-----------|----------|
| `GET /api/v1/building/{egid}/environment` | - | Nachbarn, Terrain, blockierte Seiten |

### 14.5 Polygon-Vereinfachung (On-the-fly)

**Zweck:** Frontend muss nicht mehr lokal vereinfachen

**Neuer API-Parameter:**
```
GET /api/v1/smart-building/data?address=...
    &simplify_epsilon=0.5
    &simplify_angle_tolerance=8.0
```

**Response enthält:**
```json
{
  "polygon": [[...], ...],            // Original (immer)
  "polygon_simplified": [[...], ...], // On-the-fly berechnet
  "sides": [...]                      // Aus vereinfachtem Polygon
}
```

### 14.6 Tile-Cache (Transparent)

**Für Frontend unsichtbar**, aber Performance-Verbesserung:
- Erstes Gebäude im Tile: ~8-15s (Download)
- Alle weiteren: ~1ms (Cache-Hit)

---

## 15. Frontend-Integrations-Roadmap

### Phase 1: Cleanup (P0 - Sofort)

| # | Aufgabe | Datei | Aufwand |
|---|---------|-------|---------|
| 1.1 | `buildingPolygonOriginal` entfernen | scaffold.types.ts | 1h |
| 1.2 | `polygon_simplified: boolean` entfernen | types.ts | 30min |
| 1.3 | Lokale Vereinfachung durch API-Parameter ersetzen | App.tsx | 2h |

### Phase 2: Neighbors-Integration (P1 - Hoch)

| # | Aufgabe | Datei | Aufwand |
|---|---------|-------|---------|
| 2.1 | Neighbors-API aufrufen nach Gebäude-Laden | App.tsx | 2h |
| 2.2 | Radius-Slider (0/5/10m) in UI | ConfiguratorPage.tsx | 1h |
| 2.3 | Nachbar-Polygone in 3D-Scene rendern | ScaffoldScene.tsx | 4h |
| 2.4 | `blocked_sides` in Fassaden-Auswahl anzeigen | FacadeSelector.tsx | 2h |
| 2.5 | Warnung bei blockierter Fassade | ScaffoldConfigurator.tsx | 1h |

**Mockup Radius-Slider:**
```
Nachbargebäude:  [0m] ──●── [5m] ───── [10m]
                 nur    nah    Kontext
                 angrenzend
```

### Phase 3: Multi-Adress-Support (P1 - Hoch)

| # | Aufgabe | Datei | Aufwand |
|---|---------|-------|---------|
| 3.1 | Adress-Bereich erkennen in Suchfeld | SearchForm.tsx | 2h |
| 3.2 | `/address/resolve` API aufrufen | App.tsx | 1h |
| 3.3 | Multi-Building-Ansicht | ConfiguratorPage.tsx | 4h |
| 3.4 | Alle Gebäude in 3D-Scene | ScaffoldScene.tsx | 4h |
| 3.5 | Aggregierte Statistiken (Total m², Gerüstfläche) | - | 2h |

**Anwendungsfall:**
```
User: "Knospenweg 2-10, Bern"
→ 5 Gebäude werden geladen
→ 3D-Scene zeigt alle 5 nebeneinander
→ Angebot für gesamte Häuserzeile
```

### Phase 4: Neubau-Modus (P2 - Mittel)

| # | Aufgabe | Datei | Aufwand |
|---|---------|-------|---------|
| 4.1 | `has_building: false` Handler | App.tsx | 1h |
| 4.2 | Neubau-Banner/Hinweis | ConfiguratorPage.tsx | 1h |
| 4.3 | Parzellen-Polygon anzeigen | ScaffoldScene.tsx | 2h |
| 4.4 | Manuelles Polygon-Zeichnen | PolygonEditor.tsx (NEU) | 8h |
| 4.5 | Manuelle Höheneingabe | HeightInput.tsx | 2h |
| 4.6 | DXF-Import | DxfImporter.tsx (NEU) | 8h |

**Flow:**
```
1. Adresse eingeben → "Kein Gebäude gefunden"
2. Parzelle wird angezeigt (grau)
3. Option A: Polygon zeichnen (Klicks auf Karte)
4. Option B: DXF hochladen
5. Höhe eingeben (oder Geschosse × 3.2m)
6. Gerüst-Konfiguration normal weiter
```

### Phase 5: Erweiterte Features (P3 - Niedrig)

| # | Aufgabe | Aufwand |
|---|---------|---------|
| 5.1 | Terrain-Profil in Schnitt-Ansicht | 4h |
| 5.2 | Dachüberstand visualisieren (Sonnendach-Daten) | 2h |
| 5.3 | Zonen-Editor (Höhen manuell anpassen) | 8h |
| 5.4 | Building-Context speichern (validiert) | 2h |
| 5.5 | Offline-Modus (Service Worker) | 8h |

---

## 16. Aufwand-Schätzung (Gesamt)

| Phase | Beschreibung | Aufwand | Priorität |
|-------|--------------|---------|-----------|
| **Phase 1** | Cleanup | ~4h | P0 |
| **Phase 2** | Neighbors | ~10h | P1 |
| **Phase 3** | Multi-Adress | ~13h | P1 |
| **Phase 4** | Neubau | ~22h | P2 |
| **Phase 5** | Erweitert | ~24h | P3 |
| **Total** | | **~73h** | |

### Empfohlene Reihenfolge

```
Woche 1: Phase 1 (Cleanup) + Phase 2.1-2.2 (Neighbors-Basis)
Woche 2: Phase 2.3-2.5 (Neighbors-3D) + Phase 3.1-3.2 (Multi-Adress-Basis)
Woche 3: Phase 3.3-3.5 (Multi-Adress-UI)
Woche 4: Phase 4.1-4.3 (Neubau-Basis)
Woche 5-6: Phase 4.4-4.6 (Neubau-Editor)
Später: Phase 5 (Erweitert)
```

---

## 17. API-Kompatibilitäts-Matrix

| Frontend-Feature | Backend-API | Status Backend | Status Frontend |
|------------------|-------------|----------------|-----------------|
| Gebäude-Suche | `/smart-building/data` | ✅ | ✅ |
| 3D-Ansicht | `polygon`, `traufhoehe_m` | ✅ | ✅ |
| Fassaden-Auswahl | `sides` | ✅ | ✅ |
| Zonen-Anzeige | `zones` | ✅ | ⚠️ Teilweise |
| **Nachbargebäude** | `/building/{egid}/neighbors` | ✅ | ❌ Nicht integriert |
| **Blockierte Seiten** | `blocked_sides` | ✅ | ❌ Nicht integriert |
| **Multi-Adresse** | `/address/resolve` | ✅ | ❌ Nicht integriert |
| **Neubau-Modus** | `/parzelle/for-address` | ✅ | ❌ Nicht integriert |
| **Polygon-Vereinfachung** | `simplify_epsilon` Parameter | ✅ | ⚠️ Lokal |
| Building-Context | `/building/context/*` | ✅ | ❌ Nicht integriert |
| SVG-Cache | `/building/{egid}/svg/*` | ✅ | ⚠️ Teilweise |

**Legende:**
- ✅ Vollständig implementiert
- ⚠️ Teilweise/Workaround
- ❌ Nicht integriert

---

## 18. Bugfixes (Changelog)

### BUG-006: polygon_simplified AttributeError (03.01.2026)

**Problem:**
```
AttributeError: 'BuildingDataBundle' object has no attribute 'polygon_simplified'
```

Die API `/api/v1/smart-building/data` gab einen 500-Fehler zurück, weil in `main.py` das nicht existierende Attribut `bundle.polygon_simplified` referenziert wurde.

**Ursache:**
Laut der neuen Architektur (Abschnitt 7) wird `polygon_simplified` nicht mehr im `BuildingDataBundle` persistiert, sondern on-the-fly berechnet. Der Code in `main.py` war nicht synchronisiert.

**Fix (Backend):**
```python
# main.py:3541-3558 (vorher)
"polygon_simplified": bundle.polygon_simplified,  # ← AttributeError!

# main.py:3541-3558 (nachher)
from app.services.polygon_simplifier import simplify_building_polygon

# Polygon on-the-fly vereinfachen (falls vorhanden)
polygon_simplified = None
if bundle.polygon and len(bundle.polygon) >= 3:
    result = simplify_building_polygon(bundle.polygon)
    polygon_simplified = result.polygon

# In Response:
"polygon_simplified": polygon_simplified,  # ✅ On-the-fly berechnet
```

**Fix (Frontend):**
```typescript
// NewProjectPage.tsx:81-93 - Falsches Mapping korrigiert
// Vorher:
coord_e: data.coordinates?.e,  // ← undefined!
coord_n: data.coordinates?.n,  // ← undefined!
area_m2: data.area_m2,         // ← undefined!

// Nachher:
coord_e: data.lv95_e,
coord_n: data.lv95_n,
area_m2: data.footprint_area_m2 || data.gwr_area_m2,
polygon: data.polygon,
polygon_simplified: data.polygon_simplified,
```

**Betroffene Dateien:**
| Datei | Änderung |
|-------|----------|
| `backend/app/main.py:3541-3558` | On-the-fly Vereinfachung |
| `geruestbau-app/src/pages/NewProjectPage.tsx:81-93` | API-Response Mapping |
| `geruestbau-app/src/types/project.ts:16` | `polygon_simplified` zu Interface |

**Tests:**
- `backend/tests/test_smart_building_api.py::test_polygon_simplified_in_response`
- `backend/tests/test_smart_building_api.py::test_polygon_simplified_reduces_points`

**Status:** ✅ Gefixt (03.01.2026)

---

### BUG-007: ProjectCreate.building_data AttributeError (03.01.2026)

**Problem:**
```
AttributeError: 'ProjectCreate' object has no attribute 'building_data'
```

POST `/api/v1/geruestbau/projects` schlug fehl beim Erstellen eines neuen Projekts.

**Ursache:**
Der `ProjectCreate` Pydantic-Modell hat kein `building_data` Feld, aber `project_service.py` griff direkt darauf zu.

**Fix:**
```python
# project_service.py:72-79 (vorher)
if data.building_data:  # ← AttributeError!
    ...

# project_service.py:72-82 (nachher)
egid = getattr(data, 'egid', None)  # EGID kann direkt im ProjectCreate sein
building_data = getattr(data, 'building_data', None)  # Optional
if building_data:
    ...
```

**Betroffene Dateien:**
| Datei | Änderung |
|-------|----------|
| `backend/app/services/geruestbau/project_service.py:72-82` | `getattr()` für optionale Felder |

**Status:** ✅ Gefixt (03.01.2026)

### BUG-008: ProjectCreate.description + DB-Schema Mismatch (03.01.2026)

**Problem:**
```
AttributeError: 'ProjectCreate' object has no attribute 'description'
sqlite3.OperationalError: table projects has no column named description
```

POST `/api/v1/geruestbau/projects` schlug fehl weil:
1. `ProjectCreate` Model hatte kein `description` Feld
2. Bestehende DB hatte keine `description`, `building_data`, `scaffold_config` Spalten

**Ursache:**
Das `description` Feld kommt aus SIMAP-Datenextraktion (PDF/Link Import) und war nicht im Model.
Die DB wurde vor dem Feature erstellt und hatte die neuen Spalten nicht.

**Fix:**
```python
# models/geruestbau.py - ProjectCreate erweitert
class ProjectCreate(BaseModel):
    name: str
    address: str
    egid: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[str] = None
    description: Optional[str] = None  # NEU: SIMAP-Import

# project_service.py - DB-Migration hinzugefügt
def _init_db(self):
    ...
    # DB-Migrationen: Fehlende Spalten hinzufügen
    cursor.execute("PRAGMA table_info(projects)")
    columns = [col[1] for col in cursor.fetchall()]

    migrations = {
        'description': 'TEXT',      # SIMAP-Import Feature
        'building_data': 'TEXT',    # Geodaten-Anreicherung
        'scaffold_config': 'TEXT',  # Gerüst-Konfiguration
    }

    for col_name, col_type in migrations.items():
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
```

**Betroffene Dateien:**
| Datei | Änderung |
|-------|----------|
| `backend/app/models/geruestbau.py:160-171` | `description` zu `ProjectCreate` hinzugefügt |
| `backend/app/models/geruestbau.py:174-182` | `description` zu `ProjectUpdate` hinzugefügt |
| `backend/app/services/geruestbau/project_service.py:64-79` | DB-Migration für fehlende Spalten |
| `backend/app/services/geruestbau/project_service.py:104-108` | `getattr()` für alle optionalen Felder |

**Status:** ✅ Gefixt (03.01.2026)

### BUG-009: GeocodingResult.lv95_e AttributeError in enrich_with_geodata (03.01.2026)

**Problem:**
```
[Gerüstbau] Fehler bei Geodaten-Anreicherung: 'GeocodingResult' object has no attribute 'lv95_e'
```

POST `/api/v1/geruestbau/projects/{id}/enrich` schlug fehl. Die Geodaten wurden nicht korrekt im Cache gespeichert, sodass ConfiguratorPage die Daten erneut fetchen musste.

**Ursache:**
Der Code in `enrich_with_geodata` griff direkt auf `geocode_result.lv95_e` zu, aber die korrekte Struktur ist `geocode_result.coordinates.lv95_e`. Dies ist ein wiederkehrendes Problem mit inkonsistenten Koordinaten-Attributen in verschiedenen Services.

**Root Cause Analysis:**
```python
# FALSCH (alt):
geocode_result = await self.swisstopo.geocode(project.address)
egid = geocode_result.egid  # ← GeocodingResult hat kein egid!
coord_e = geocode_result.lv95_e  # ← AttributeError!

# RICHTIG:
geocode_result.coordinates.lv95_e  # Verschachtelt in Coordinates-Objekt
```

**Fix:**
Komplettes Refactoring von `enrich_with_geodata` um den SmartBuildingService zu verwenden:
```python
# project_service.py:238-344 (nachher)
async def enrich_with_geodata(self, project_id: str) -> Optional[ProjectWithGeodata]:
    """Projekt mit Geodaten anreichern via SmartBuildingService."""
    project = await self.get_project(project_id)
    if not project:
        return None

    try:
        from app.services.smart_building import get_smart_building_service
        smart_service = get_smart_building_service()
        bundle = await smart_service.collect_all_data(
            address=project.address,
            force_refresh=False,
            include_research=False,
            include_zones_analysis=False,
            include_terrain=True,
        )

        if bundle:
            egid = bundle.egid
            # Koordinaten direkt vom Bundle (konsistent!)
            building_data["geocode"] = {
                "coordinates": {
                    "e": bundle.lv95_e,
                    "n": bundle.lv95_n,
                },
            }
            # ... weitere Daten aus Bundle ...

            # Geodaten im zentralen Cache speichern
            geodata = BuildingGeodata(
                egid=str(egid),
                polygon=bundle.polygon,
                # ... etc ...
            )
            self.geodata_service.save(geodata)
    except Exception as e:
        print(f"[Gerüstbau] Fehler bei Geodaten-Anreicherung: {e}")

    # Mit Geodaten zurückgeben
    return await self.get_project_with_geodata(project_id)
```

**Vorteile des Refactorings:**
1. **Konsistente Daten:** SmartBuildingService hat einheitliche Koordinaten-Attribute
2. **Cache-Integration:** Geodaten werden automatisch im Cache gespeichert
3. **Weniger Fehlerquellen:** Keine manuellen API-Aufrufe mehr
4. **Return-Typ:** Gibt jetzt `ProjectWithGeodata` zurück (inkl. gecachter Geodaten)

**Betroffene Dateien:**
| Datei | Änderung |
|-------|----------|
| `backend/app/services/geruestbau/project_service.py:238-344` | Komplettes Refactoring auf SmartBuildingService |

**TODO - Koordinaten-Attribut-Chaos:**

| Service/Model | Koordinaten-Zugriff | Bemerkung |
|---------------|---------------------|-----------|
| `GeocodingResult` | `.coordinates.lv95_e` | Verschachtelt in Coordinates-Objekt |
| `BuildingDataBundle` | `.lv95_e`, `.lv95_n` | Flach auf Top-Level |
| `BuildingGeodata` | `.coord_e`, `.coord_n` | Anderer Name! |
| `Coordinates` | `.lv95_e`, `.lv95_n`, `.wgs84_lon`, `.wgs84_lat` | Alle 4 Koordinatensysteme |

**Empfehlung:** Vereinheitlichung auf `lv95_e`/`lv95_n` für alle LV95-Koordinaten.

**Status:** ✅ Gefixt (03.01.2026)


---

## BUG-011: LV03 statt LV95 Koordinaten (GEFIXT 04.01.2026)

### Problem

Die swisstopo SearchServer API gibt Koordinaten im LV03-Format ohne Präfix zurück:
```json
{
  "x": 199805,  // LV03 N-Koordinate (ohne 1xxx Präfix)
  "y": 596299   // LV03 E-Koordinate (ohne 2xxx Präfix)
}
```

Der Code speicherte diese direkt als LV95-Koordinaten, was zu fehlgeschlagenen Identify-Lookups führte.

### Lösung

In `backend/app/services/swisstopo.py` Zeile 143-156:

```python
# LV03 → LV95 Konvertierung (wenn Werte < 1000000)
lv95_e = raw_e + 2000000 if raw_e < 1000000 else raw_e
lv95_n = raw_n + 1000000 if raw_n < 1000000 else raw_n
```

Zusätzlich: `sr=2056` Parameter für Identify API.

**Status:** ✅ Gefixt

---

## BUG-013: GWR vs swissBUILDINGS3D EGID-Unterschiede (GEFIXT)

### Problem

Bei Reihenhäusern haben GWR und swissBUILDINGS3D **unterschiedliche EGIDs**:

| Adresse | GWR EGID | swissBUILDINGS3D EGID |
|---------|----------|----------------------|
| Knospenweg 2 | 1243790 | 1243788 |
| Knospenweg 4 | 1243790 | 1243790 |
| Knospenweg 6 | 1243790 | 1243792 |

- **GWR:** Reihenhaus = 1 Gebäude (Nr. 2-6 = EGID 1243790)
- **swissBUILDINGS3D:** Jedes Segment = separates Gebäude

### Auswirkung

Bei Multi-Adress-Suche "Knospenweg 4-6":
1. GWR-Geocoding gibt für beide Adressen EGID 1243790 zurück
2. Frontend gruppiert nach EGID → zeigt nur 1 Gebäude
3. Aber in `buildings` DB existieren separate Polygone pro Adresse!

### Lösung (04.01.2026)

**Koordinaten-basierter Lookup in tiles.db statt GWR identify_buildings:**

```python
# address_parser.py - _lookup_egid_by_coordinates()
def _lookup_egid_by_coordinates(e: float, n: float, tolerance_m: float = 10.0):
    cursor.execute('''
        SELECT egid,
               (lv95_e - ?) * (lv95_e - ?) + (lv95_n - ?) * (lv95_n - ?) as dist_sq
        FROM egid_tile_index
        WHERE lv95_e BETWEEN ? AND ? AND lv95_n BETWEEN ? AND ?
        ORDER BY dist_sq LIMIT 1
    ''', (e, e, n, n, e - tolerance_m, e + tolerance_m, n - tolerance_m, n + tolerance_m))
```

**Datenfluss:**
```
Adresse → Geocoding (swisstopo) → LV95 Koordinaten → tiles.db Lookup → swissBUILDINGS3D EGID
```

**Test-Ergebnisse:**
```
Knospenweg 2:  EGID=1243788, Source=swissBUILDINGS3D ✅
Knospenweg 4:  EGID=1243790, Source=swissBUILDINGS3D ✅
Knospenweg 6:  EGID=1243792, Source=swissBUILDINGS3D ✅
Knospenweg 8:  EGID=1243794, Source=swissBUILDINGS3D ✅
Knospenweg 10: EGID=1243797, Source=swissBUILDINGS3D ✅
```

**Geänderte Dateien:**
- `backend/app/services/address_parser.py` - `_lookup_egid_by_coordinates()` Funktion
- `backend/app/services/smart_building/service.py` - EGID-Assignment aus swissBUILDINGS3D
- `backend/app/services/smart_building/models.py` - `gwr_egid` Feld für Referenz

**Status:** ✅ Gefixt (04.01.2026)

---

## Architektur-Entscheidung: Koordinaten-basierte Lookups (04.01.2026)

### Entscheidung

**Kein Adress-Cache in tiles.db** - Alle Gebäude-Lookups erfolgen über Koordinaten.

### Begründung

1. **swissBUILDINGS3D enthält keine Adressen** - nur EGID + Koordinaten + Höhen
2. **Koordinaten-Lookup ist ausreichend** für unsere Kern-Anwendungen:
   - Gebäude-Identifikation: Adresse → Geocoding → Koordinaten → tiles.db
   - Nachbar-Suche: Koordinaten ±10m → tiles.db Query
3. **Keine 100 API-Calls pro Tile nötig** für Adress-Anreicherung

### Datenfluss ohne Adress-Cache

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOOKUP OHNE ADRESS-CACHE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Adress-Suche:                                                  │
│  "Knospenweg 4, Bern"                                           │
│       │                                                         │
│       ▼                                                         │
│  swisstopo Geocoding → (E=2596299, N=1199805)                  │
│       │                                                         │
│       ▼                                                         │
│  tiles.db: SELECT egid WHERE E±10m AND N±10m                   │
│       │                                                         │
│       ▼                                                         │
│  EGID=1243790 (swissBUILDINGS3D)                               │
│       │                                                         │
│       ▼                                                         │
│  Polygon + Höhen aus tiles.db                                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Nachbar-Suche:                                                 │
│  "Gebäude im Umkreis von 10m?"                                  │
│       │                                                         │
│       ▼                                                         │
│  tiles.db: SELECT egid WHERE E±10m AND N±10m AND egid != ?     │
│       │                                                         │
│       ▼                                                         │
│  Liste der Nachbar-EGIDs (ohne Adressen)                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Mögliche Erweiterung (optional)

Ein Adress-Cache wäre **rein informativ** für:
- Darstellung von Ausschnitten/Ranges in der 3D-Ansicht
- Adress-Labels auf Nachbargebäuden

**Implementation** (falls gewünscht):
1. Beim Tile-Import: GWR API für jede EGID abfragen
2. Adresse in tiles.db speichern (neue Spalte `address`)
3. ~100 API-Calls pro Tile (ca. 1-2 Minuten)

**Priorität:** Niedrig - Fokus liegt auf exakten Lookups und Gebäude-Identifikation
