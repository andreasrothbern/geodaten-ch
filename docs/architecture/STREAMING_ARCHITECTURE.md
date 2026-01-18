# Streaming Architecture

> **Version:** 3.12 (16.01.2026)
> **Status:** Cache-Lookup ✅ | Response-Streaming ✅ | Building-Data-Streaming ✅ | Tile-Prefetch ✅ | 3D-Layer ✅ | Reaktive Architektur 🔲

---

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Teil A: Cache-Lookup Architektur](#teil-a-cache-lookup-architektur) (implementiert)
3. [Teil B: Project-Context-Streaming](#teil-b-response-streaming-architektur) (implementiert)
4. [Teil C: Building-Data-Streaming](#teil-c-building-data-streaming) (implementiert)
5. [Teil D: Pipeline-Optimierung](#teil-d-smartbuildingservice-pipeline-optimierung) (implementiert)
6. [Teil E: Tile-Prefetch Timing](#teil-e-tile-prefetch-timing--on-demand-architektur) (implementiert)
7. [Teil F: Frontend Service-Aufrufe](#teil-f-frontend-service-aufrufe-configuratorpage) (Analyse)
8. [Teil G: 3D Layer Architecture](#teil-g-3d-layer-architecture-dach-daten) (implementiert)
9. [Teil I: Blocking-Architektur Refactoring](#teil-i-blocking-architektur-refactoring-todo) (TODO)
10. [Teil J: Storage-Strategie (Railway Pro)](#teil-j-storage-strategie-railway-pro) (TODO)
11. [Teil K: Projektspezifische 3D-Daten](#teil-k-projektspezifische-3d-daten) (TODO)
12. **[Teil L: Reaktive SSE-Architektur](#teil-l-reaktive-architektur-ziel) (ZIEL-ARCHITEKTUR)**
13. [Services für Streaming](#services-für-streaming)
14. [Implementierungsplan](#implementierungsplan)

---

## Übersicht

Diese Architektur besteht aus mehreren Teilen:

| Teil | Zweck | Status |
|------|-------|--------|
| **A: Cache-Lookup** | Schneller Datenzugriff durch 3-Stufen Lookup | ✅ Implementiert |
| **B: Project-Context-Streaming** | Blockierte Fassaden, Nachbarn für bestehende Projekte | ✅ Implementiert |
| **C: Building-Data-Streaming** | Progressive Datenladung bei Projekt-Erstellung | ✅ Implementiert |
| **D: Pipeline-Optimierung** | Maximale Parallelisierung im SmartBuildingService | ✅ Implementiert |
| **E: Tile-Prefetch** | MINIMAL + ON-DEMAND Architektur | ✅ Implementiert |
| **F: Frontend Service-Aufrufe** | Analyse der ConfiguratorPage Calls | ✅ Dokumentiert |
| **G: 3D Layer Architecture** | Roof_solid Integration für echte Dach-Daten | ✅ Implementiert |
| **L: Reaktive Architektur** | SSE statt REST - Ziel-Architektur | 🔲 **TODO** |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STREAMING ARCHITECTURE v3.0                          │
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
| **Skalierbarkeit** | Begrenzt | **Besser** (keine Long-Running Requests) |

## B.4 Prioritäts-Reihenfolge der Events

```
┌─────────────────────────────────────────────────────────────────┐
│  EVENT-PRIORITÄTEN                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRIO 1: KRITISCH (für Gerüstplanung essentiell)               │
│  ════════════════════════════════════════════                   │
│  • centroid          → Kamera-Zentrierung                      │
│  • project_buildings → Projekt-Gebäude rendern                 │
│  • blocked_facades   → Welche Fassaden sind blockiert?         │
│                                                                 │
│  PRIO 2: WICHTIG (für 3D-Visualisierung)                       │
│  ════════════════════════════════════════                       │
│  • neighbors (5-20m) → Direkte Nachbarn                        │
│  • terrain           → Geländehöhe, Hanglage                   │
│                                                                 │
│  PRIO 3: KONTEXT (für besseres Verständnis)                    │
│  ═════════════════════════════════════════                      │
│  • neighbors (50m)   → Umgebung                                │
│  • neighbors (100m)  → Weiterer Kontext                        │
│                                                                 │
│  PRIO 4: ROADMAP (zukünftige Features)                         │
│  ═════════════════════════════════════                          │
│  • streets           → Strassenverlauf (swisstopo)             │
│  • parking           → Abstellflächen                          │
│  • access_points     → Zufahrten                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## B.5 Projekt-Kontext: Mehrere Gebäude

Ein Projekt kann mehrere Gebäude enthalten. Die Architektur berücksichtigt dies:

```
┌─────────────────────────────────────────────────────────────────┐
│  PROJEKT MIT MEHREREN GEBÄUDEN                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Projekt-Gebäude: [EGID_A, EGID_B, EGID_D]                     │
│                                                                 │
│       ┌─────┐                                                   │
│       │  C  │ ← Externes Gebäude (NICHT im Projekt)            │
│       └─────┘                                                   │
│          ↑ 3m Abstand                                           │
│    ┌─────┬─────┬─────┐                                          │
│    │  A  │  B  │  D  │ ← Projekt-Gebäude (zu einrüsten)        │
│    └─────┴─────┴─────┘                                          │
│                                                                 │
│  BERECHNUNG:                                                    │
│  ───────────                                                    │
│  1. Centroid = geometrischer Mittelpunkt von A, B, D           │
│                                                                 │
│  2. blocked_facades:                                            │
│     • Für JEDES Projekt-Gebäude separat berechnen              │
│     • Nachbarn suchen im 5m Radius                             │
│     • EXKLUDIERE andere Projekt-Gebäude!                       │
│     • Nur externe Gebäude blockieren Fassaden                  │
│                                                                 │
│  Beispiel für Gebäude B:                                        │
│     all_neighbors = [A, C, D] (im 5m Radius)                   │
│     project_egids = [A, B, D]                                  │
│     external = [C]           ← Nur C ist extern!               │
│     blocked_facades_B = [0]  ← Nord-Fassade (Richtung C)       │
│                                                                 │
│  3. neighbors für 3D-View:                                      │
│     • Grösserer Radius (50-100m)                               │
│     • Alle Gebäude ausser Projekt-Gebäude                      │
│     • Progressiv laden (erst nah, dann fern)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

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
│       ├──→ event: research         (~1s, optional)             │
│       │    data: {building_name, building_type}                │
│       │    → UI: Gebäudename anzeigen                          │
│       │                                                         │
│       └──→ event: complete                                     │
│            data: {status, duration_ms, bundle}                 │
│            → UI: "Projekt erstellen" Button aktivieren         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## C.2 Vorteile

| Aspekt | Ohne Streaming | Mit Streaming |
|--------|----------------|---------------|
| **Time to First Feedback** | 200ms - 10s | **~50ms** (geocoding) |
| **User Experience** | Langer Spinner | **Progressives Laden** |
| **Abbruch möglich** | Nein | **Ja** (ESC / Zurück) |
| **Download-Feedback** | Keins | **"Lade Gebäudedaten..."** |
| **Fehlertoleranz** | Alles oder nichts | **Partial Success** möglich |

## C.3 API-Spezifikation

```
GET /api/v1/geruestbau/building/data/stream
    ?address=Kramgasse+10,+Bern
    &include_research=true
    &include_zones=true
    &include_terrain=true
    &force_refresh=false

Headers:
    Accept: text/event-stream
    Cache-Control: no-cache

Response: Server-Sent Events (SSE)
    Content-Type: text/event-stream
```

## C.4 Event-Typen

### geocoding
```json
event: geocoding
data: {
    "matched_address": "Kramgasse 10, 3011 Bern",
    "egid": "1234567",
    "coordinates": {"lv95_e": 2600450.5, "lv95_n": 1199830.2},
    "duration_ms": 48
}
```

### polygon_progress (nur bei Tile-Download)
```json
event: polygon_progress
data: {
    "status": "downloading",
    "message": "Lade Gebäudedaten von swisstopo...",
    "tile_id": "1332-22"
}
```

### polygon
```json
event: polygon
data: {
    "polygon": [[2600450, 1199830], ...],
    "sides": [{"start": {...}, "end": {...}, "length_m": 12.5}, ...],
    "perimeter_m": 45.2,
    "area_m2": 125.3,
    "egid": "1234567",
    "cache_hit": true,
    "duration_ms": 15
}
```

### heights
```json
event: heights
data: {
    "traufhoehe_m": 12.5,
    "firsthoehe_m": 15.8,
    "gebaeudehoehe_m": 15.8,
    "source": "swissBUILDINGS3D",
    "duration_ms": 5
}
```

### terrain
```json
event: terrain
data: {
    "terrain_height_m": 533.5,
    "min_terrain_m": 531.2,
    "max_terrain_m": 537.1,
    "slope_m": 5.9,
    "slope_class": "stark",
    "duration_ms": 185
}
```

### zones
```json
event: zones
data: {
    "zones": [
        {"id": "zone_1", "name": "Hauptgebäude", "zone_type": "hauptgebaeude", ...}
    ],
    "complexity": "simple",
    "source": "auto",
    "duration_ms": 12
}
```

### complete
```json
event: complete
data: {
    "status": "ok",
    "duration_ms": 487,
    "address": "Kramgasse 10, 3011 Bern",
    "egid": "1234567",
    "summary": {
        "has_polygon": true,
        "has_heights": true,
        "has_terrain": true,
        "zones_count": 1,
        "complexity": "simple"
    },
    "bundle": { /* Vollständige Daten für sofortige Verwendung */ }
}
```

## C.5 Frontend-Integration (React Hook)

```typescript
import { useBuildingDataStream } from '../hooks';

function GeodataStep() {
  const {
    start,
    isLoading,
    currentStep,
    stepLabel,
    progress,
    polygon,
    heights,
    bundle,
    isComplete,
    isDownloading,
  } = useBuildingDataStream({
    onPolygon: (data) => renderPolygonOnMap(data.polygon),
    onComplete: (data) => setFormData(data.bundle),
  });

  return (
    <div>
      <AddressInput onSubmit={(addr) => start(addr)} />

      {isLoading && (
        <ProgressBar
          value={progress}
          label={isDownloading ? "Gebäudedaten herunterladen..." : stepLabel}
        />
      )}

      {polygon && <BuildingPreview polygon={polygon.polygon} />}

      {isComplete && (
        <Button onClick={() => createProject(bundle)}>
          Projekt erstellen
        </Button>
      )}
    </div>
  );
}
```

---

# Services für Streaming

## Übersicht: Welche Services nutzen Streaming?

| Service | Streaming? | Begründung |
|---------|------------|------------|
| **BuildingDataStreamService** | ✅ JA | Projekt-Erstellung, viele Schritte |
| **ProjectContextStreamService** | ✅ JA | Blockierte Fassaden, Nachbarn |
| **BlockedFacadesService** | ❌ NEIN | Schnell genug (~50ms) |
| **NeighborsService** | ❌ NEIN | Via ProjectContextStream |
| **SmartBuildingService** | ❌ NEIN | Via BuildingDataStream |
| **SVGGeneratorService** | ❌ NEIN | Einmal-Response (SVG ist atomar) |

## Neue Services für Streaming

### 1. ProjectContextStreamService

**Datei:** `backend/app/services/project_context_stream.py`

**Zweck:** Streaming-API für Projekt-Kontext (Fassaden, Nachbarn, etc.)

```python
class ProjectContextStreamService:
    """
    Streaming-Service für Projekt-Kontext.

    Liefert progressiv:
    1. centroid (Projekt-Mittelpunkt)
    2. project_buildings (Projekt-Gebäude mit Polygonen)
    3. blocked_facades (blockierte Fassaden pro Gebäude)
    4. neighbors (in Schichten: 20m, 50m, 100m)
    5. complete (Abschluss-Signal)
    """

    async def stream_context(
        self,
        project_id: str,
        max_radius_m: float = 100
    ) -> AsyncGenerator[Dict, None]:
        """Generator für SSE Events."""
        pass

    def calculate_centroid(
        self,
        project_egids: List[str]
    ) -> Tuple[float, float]:
        """Berechnet geometrischen Mittelpunkt."""
        pass

    async def calculate_blocked_facades(
        self,
        project_egids: List[str],
        radius_m: float = 5.0
    ) -> Dict[str, BlockedFacadesResult]:
        """
        Berechnet blockierte Fassaden für alle Projekt-Gebäude.
        Exkludiert andere Projekt-Gebäude aus der Nachbar-Suche.
        """
        pass
```

### 2. BlockedFacadesService

**Datei:** `backend/app/services/blocked_facades_service.py`

**Zweck:** Ermittelt welche Fassaden durch externe Gebäude blockiert sind.

```python
class BlockedFacadesService:
    """
    Service zur Ermittlung blockierter Fassaden.

    Eine Fassade gilt als "blockiert" wenn:
    - Ein externes Gebäude (nicht im Projekt) < 2m entfernt ist
    - Kein Gerüst aufgestellt werden kann
    """

    def calculate_for_building(
        self,
        egid: str,
        exclude_egids: Set[str],  # Projekt-Gebäude
        threshold_m: float = 2.0
    ) -> BlockedFacadesResult:
        """
        Berechnet blockierte Fassaden-Indizes.

        Returns:
            BlockedFacadesResult mit blocked_indices, total_facades, etc.
        """
        pass
```

### 3. BuildingDataStreamService

**Datei:** `backend/app/services/building_data_stream.py`

**Zweck:** Progressive Datenladung bei Projekt-Erstellung.

```python
class BuildingDataStreamService:
    """
    Streaming-Service für Gebäudedaten bei Projekt-Erstellung.

    Liefert progressiv:
    1. geocoding - Adress-Match, Koordinaten
    2. gwr - GWR-Daten
    3. polygon - Gebäude-Polygon (mit Download-Progress)
    4. heights - Höhendaten
    5. terrain - Terrain-Höhe, Hanglage
    6. zones - Zonen-Analyse
    7. research - Gebäudename (optional)
    8. complete - Vollständiges Bundle
    """

    async def stream_building_data(
        self,
        address: str,
        include_research: bool = True,
        include_zones: bool = True,
        include_terrain: bool = True
    ) -> AsyncGenerator[SSEEvent, None]:
        """Generator für SSE Events."""
        pass
```

---

# Implementierungsplan

## Phase 1: Backend Streaming ✅ ABGESCHLOSSEN

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.1 | SSE-Dependency hinzufügen (`sse-starlette`) | ✅ |
| 1.2 | `ProjectContextStreamService` implementieren | ✅ |
| 1.3 | `BlockedFacadesService` implementieren | ✅ |
| 1.4 | Streaming-Endpunkt `/project/{id}/context/stream` | ✅ |
| 1.5 | `BuildingDataStreamService` implementieren | ✅ |
| 1.6 | Streaming-Endpunkt `/building/data/stream` | ✅ |

## Phase 2: Frontend Integration ✅ ABGESCHLOSSEN

| Task | Beschreibung | Status |
|------|--------------|--------|
| 2.1 | React Hook `useProjectContextStream` | ✅ |
| 2.2 | React Hook `useBuildingDataStream` | ✅ |
| 2.3 | Typen-Export in hooks/index.ts | ✅ |
| 2.4 | Progressive Callbacks (onGeocoding, onPolygon, etc.) | ✅ |

## Phase 3: Optimierung (Woche 3)

| Task | Beschreibung | Status |
|------|--------------|--------|
| 3.1 | Performance-Messung | 🔲 |
| 3.2 | Caching für häufige Abfragen | 🔲 |
| 3.3 | Error Handling & Retry | 🔲 |

---

# API-Spezifikation

## Streaming-Endpunkt

```
GET /api/v1/project/{project_id}/context/stream
    ?include_blocked_facades=true
    &include_neighbors=true
    &max_radius_m=100

Headers:
    Accept: text/event-stream
    Cache-Control: no-cache

Response: Server-Sent Events (SSE)
    Content-Type: text/event-stream
```

## Event-Typen

### centroid
```
event: centroid
data: {"center_e": 2600450.5, "center_n": 1199830.2}
```

### project_buildings
```
event: project_buildings
data: {
    "buildings": [
        {"egid": "123", "polygon": [[...]], "traufhoehe_m": 12.5},
        {"egid": "456", "polygon": [[...]], "traufhoehe_m": 15.0}
    ]
}
```

### blocked_facades
```
event: blocked_facades
data: {
    "123": {"blocked_indices": [2], "blockers": [{"egid": "789", "distance_m": 1.5}]},
    "456": {"blocked_indices": [0, 3], "blockers": [...]}
}
```

### neighbors
```
event: neighbors
data: {
    "radius_m": 50,
    "buildings": [
        {"egid": "789", "polygon": [[...]], "distance_m": 25.3, "direction": "NW"},
        ...
    ]
}
```

### error
```
event: error
data: {"code": "BUILDING_NOT_FOUND", "message": "EGID 123 not found"}
```

### complete
```
event: complete
data: {"status": "ok", "duration_ms": 487, "total_neighbors": 15}
```

---

# Datenbank-Übersicht

| Datenbank | Inhalt | Streaming-Relevant |
|-----------|--------|-------------------|
| `building_3d.db` | Polygon, Höhen, Koordinaten | ✅ Primäre Quelle für Nachbarn |
| `tiles.db` | Tile-Metadaten | ❌ Nur für Cache-Miss |
| `building_contexts.db` | Zonen, Terrain | ⚠️ Optional für Enrichment |
| `geruestbau.db` | Projekte | ✅ Projekt-Gebäude laden |

---


---

# Teil D: SmartBuildingService Pipeline-Optimierung

> **NEU 10.01.2026:** Maximale Parallelisierung der Datensammlung

## D.1 Das Problem: Sequentielle API-Calls

```
VORHER: Sequentielle Pipeline (~4.5s)
=========================================

Phase 1: Geocoding                              (0.5s)
         |
Phase 2a: GWR                                   (0.3s)
          |
Phase 2b: +-> Building3D --+
          +-> Terrain -----+-> WARTEN           (2.0s)
              (8x SEQ!)    |
                           |
Phase 3:  +-> Sonnendach --+
          +-> Dach-Analyse +-> WARTEN           (1.0s)
          +-> Research ----+

Phase 4: Zonen-Analyse                          (0.5s)

PROBLEM: Terrain macht 8 SEQUENTIELLE API-Calls
         (~300ms x 8 = 2.4s allein fuer Hanglage!)
```

## D.2 Die Loesung: Maximale Parallelisierung

```
NACHHER: Maximale Parallelisierung (~1.5s)
==========================================

Phase 1: Geocoding                              (0.5s)
         |
         | Sofort ALLES parallel starten:
         |
Phase 2: +-> GWR ------------------+
         +-> Building3D -----------+
         +-> Sonnendach -----------+
         +-> Terrain (8x PARALLEL!)+-> WARTEN   (0.8s)
         +-> Research (Claude API)-+

Phase 3: Dach-Analyse (berechnet)               (0.1s)

Phase 4: Zonen-Analyse (wenn noetig)            (0.1s)

OPTIMIERUNGEN:
- Terrain: 8 Hoehen-Calls jetzt PARALLEL (asyncio.gather)
- Research: Startet sofort nach Geocoding (nicht nach GWR)
- Sonnendach: Parallel mit Building3D (braucht nur Koord.)
```

## D.3 Performance-Vergleich

| Phase | VORHER | NACHHER | Ersparnis |
|-------|--------|---------|-----------|
| Geocoding | 0.5s | 0.5s | - |
| GWR + Building3D + Terrain | 2.3s | **0.8s** | 65% |
| Sonnendach + Research | 1.0s | **(parallel)** | 100% |
| Dach + Zonen | 0.7s | 0.2s | 70% |
| **TOTAL** | **~4.5s** | **~1.5s** | **67%** |

## D.4 Code-Aenderungen

### Terrain-Calls parallelisiert

```python
# VORHER (sequentiell, ~2.5s):
for i in range(0, len(bundle.polygon), step):
    point = bundle.polygon[i]
    h = await terrain_service.get_height(point[0], point[1])  # WARTEN
    heights.append(h)

# NACHHER (parallel, ~0.3s):
sample_points = [bundle.polygon[i] for i in range(0, len(polygon), step)]
height_tasks = [terrain_service.get_height(p[0], p[1]) for p in sample_points]
height_results = await asyncio.gather(*height_tasks)  # ALLE PARALLEL
heights = [h for h in height_results if isinstance(h, (int, float))]
```

### Pipeline-Phasen optimiert

```python
# VORHER:
await self._collect_gwr_data(bundle)  # Phase 2a: sequentiell
phase2_tasks = [Building3D, Terrain]   # Phase 2b: parallel
await asyncio.gather(*phase2_tasks)
phase3_tasks = [Sonnendach, Research]  # Phase 3: parallel (aber NACH 2b!)
await asyncio.gather(*phase3_tasks)

# NACHHER:
phase2_tasks = [
    self._collect_gwr_data(bundle),        # Parallel!
    self._collect_building_3d_data(bundle),
    self._collect_sonnendach_data(bundle), # Parallel!
    self._collect_terrain_data(bundle),    # Intern auch parallel!
    self._collect_research_data(bundle),   # Sofort starten!
]
await asyncio.gather(*phase2_tasks)  # ALLES PARALLEL
```

## D.5 Abhaengigkeits-Analyse

| Task | Braucht | Kann starten nach |
|------|---------|-------------------|
| Geocoding | Adresse | Sofort |
| GWR | EGID | Geocoding |
| Building3D | Koordinaten | Geocoding |
| Sonnendach | Koordinaten | Geocoding |
| Terrain | Koordinaten | Geocoding *(Polygon optional)* |
| Research | Adresse | Geocoding *(GWR optional fuer Kontext)* |
| Dach-Analyse | Hoehen + Polygon | Building3D |
| Zonen | Alles | Phase 2 |

**Erkenntnis:** Fast alles kann direkt nach Geocoding parallel starten!


---

# Teil E: Tile-Prefetch Timing & On-Demand Architektur

> **IMPLEMENTIERT 10.01.2026:** MINIMAL + ON-DEMAND Architektur

## E.1 Gemessene Timing-Ergebnisse (10.01.2026)

**Testfall:** Knospenweg 4, Bern (nach vollständigem Reset)

### VORHER (synchroner Prefetch)

```
┌─────────────────────────────────────────────────────────────┐
│               ALTE TIMING-MESSUNG (synchron)                │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: Hauptgebäude laden (Cold Start)                   │
│  ─────────────────────────────────────────                  │
│  - STAC API Tile-Suche: ~2s                                 │
│  - ZIP Download (Tile 1322-21): ~5s                         │
│  - GDB Entpacken + Parsing: ~100s                           │
│  - Prefetch ALLER 4826 Gebäude: ~100s (BLOCKIERT!)          │
│  ─────────────────────────────────────────                  │
│  GESAMT Phase 1: **108.73s** ← PROBLEM: User wartet!        │
│                                                             │
│  Phase 2: Nachbarn abfragen (Warm)                          │
│  ─────────────────────────────────────────                  │
│  - Koordinaten-Suche in building_3d.db: 0.01s              │
│  ─────────────────────────────────────────                  │
│  GESAMT Phase 2: **0.01s**                                  │
└─────────────────────────────────────────────────────────────┘
```

### NACHHER (async Prefetch + Stufe 2 Fix)

```
┌─────────────────────────────────────────────────────────────┐
│            NEUE TIMING-MESSUNG (10.01.2026)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1] COLD START (neues Tile herunterladen)                  │
│  ─────────────────────────────────────────                  │
│  - Tile-Download + GDB-Parsing: ~80s                        │
│  - Prefetch läuft ASYNC im Hintergrund                      │
│  ─────────────────────────────────────────                  │
│  Zeit: **79.92s** (unvermeidlich: Tile-Download)            │
│                                                             │
│  [2] WARM CACHE (building_3d.db)                            │
│  ─────────────────────────────────────────                  │
│  - Stufe 1 Lookup aus building_3d.db                        │
│  ─────────────────────────────────────────                  │
│  Zeit: **0.290s** ← 373x schneller als Cold Start!          │
│                                                             │
│  [3] NACHBAR (gleiches Tile)                                │
│  ─────────────────────────────────────────                  │
│  - Aus building_3d.db geladen (kein GDB-Parsing)            │
│  ─────────────────────────────────────────                  │
│  Zeit: **0.009s** ← Instant!                                │
│                                                             │
│  [4] BUNDLE-CACHE (identische Anfrage)                      │
│  ─────────────────────────────────────────                  │
│  - SmartBuilding Bundle-Cache Hit                           │
│  ─────────────────────────────────────────                  │
│  Zeit: **0.015s** ← Instant!                                │
│                                                             │
│  Tile-Statistik:                                            │
│  - Tile 1322-21 enthält **4827 Gebäude**                    │
│  - Alle in building_3d.db nach Prefetch                     │
└─────────────────────────────────────────────────────────────┘
```

### Zusammenfassung

| Szenario | Zeit | Verbesserung |
|----------|------|--------------|
| Cold Start (Tile-Download) | ~80s | (unvermeidlich) |
| Warm Cache (building_3d.db) | 0.29s | **373x schneller** |
| Nachbar (gleiches Tile) | 0.009s | **12000x schneller** |
| Bundle-Cache (identisch) | 0.015s | **7200x schneller** |

**Fazit:** Nach dem ersten Tile-Download sind alle Abfragen extrem schnell!

## E.2 Aktuelle Architektur (AKTUELL: sequentiell + unnötig)

```
┌─────────────────────────────────────────────────────────────┐
│              AKTUELL: SYNCHRONER PREFETCH                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User gibt Adresse ein                                      │
│       │                                                     │
│       ▼                                                     │
│  GET /building/data/stream?address=Knospenweg 4, Bern      │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Geocoding (~0.5s)                                │   │
│  │ 2. GWR-Daten (~0.3s)                                │   │
│  │ 3. Tile prüfen: nicht gecacht                       │   │
│  │ 4. STAC API: Tile-Suche (~2s)                       │   │
│  │ 5. ZIP Download (~5s)                               │   │
│  │ 6. ██████████████████████████████████████████████   │   │
│  │    PREFETCH ALLER 4826 GEBÄUDE (~100s) ← BLOCKIERT! │   │
│  │    ██████████████████████████████████████████████   │   │
│  │ 7. Hauptgebäude zurückgeben                         │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  User sieht Gebäude nach **~108s**                          │
│                                                             │
│  Problem:                                                   │
│  - User wartet auf 4826 Gebäude, braucht aber nur 1        │
│  - Nachbarn sind sofort danach verfügbar (gut!)            │
│  - Aber: 100s Wartezeit für unnötigen Prefetch             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## E.3 Optimale Architektur (OPTIMAL: MINIMAL + ON-DEMAND)

```
┌─────────────────────────────────────────────────────────────┐
│              OPTIMAL: MINIMAL + ON-DEMAND                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User gibt Adresse ein                                      │
│       │                                                     │
│       ▼                                                     │
│  GET /building/data/stream?address=Knospenweg 4, Bern      │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Geocoding (~0.5s)                                │   │
│  │ 2. GWR-Daten (~0.3s)                                │   │
│  │ 3. Tile prüfen: nicht gecacht                       │   │
│  │ 4. STAC API: Tile-Suche (~2s)                       │   │
│  │ 5. ZIP Download (~5s)                               │   │
│  │ 6. NUR HAUPTGEBÄUDE parsen (~0.1s)                  │   │
│  │ 7. Direkte Nachbarn laden (5m Radius) (~0.5s)       │   │
│  │ 8. Hauptgebäude + Nachbarn zurückgeben              │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  User sieht Gebäude nach **~8-10s** ← 10x schneller!       │
│       │                                                     │
│       │  (Background-Job startet)                           │
│       │       │                                             │
│       │       ▼                                             │
│       │  ┌────────────────────────────────────────────┐    │
│       │  │ ASYNC: Restliche Gebäude prefetchen       │    │
│       │  │ - Läuft im Hintergrund                     │    │
│       │  │ - Blockiert User NICHT                     │    │
│       │  └────────────────────────────────────────────┘    │
│       │                                                     │
│       ▼                                                     │
│  User zoomt auf 20m Radius                                  │
│       │                                                     │
│       ▼                                                     │
│  GET /building/{egid}/neighbors?radius_m=20                │
│       │                                                     │
│       ▼                                                     │
│  Nachbarn aus building_3d.db (falls prefetch fertig)       │
│  ODER: On-Demand aus GDB laden (falls noch nicht)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## E.4 Nachbar-Radien Verwendung

| Radius | Verwendung | Wann geladen |
|--------|------------|--------------|
| **5m** | blocked_facades Berechnung (intern) | Initial (IMMER, kein UI) |
| **20m** | Nahe Nachbarn (2D + 3D) | On-demand (Slider) |
| **50m** | Erweiterte Umgebung (2D + 3D) | On-demand (Slider) |
| **100m** | Voller Kontext (2D + 3D) | On-demand (Slider) |

**Architektur:**
- `blocked-facades` wird IMMER initial geladen (nutzt intern 5m Radius)
  → Blockierte Fassaden sind NICHT ANWÄHLBAR (disabled in UI)
- `neighbors` wird nur on-demand geladen wenn User Slider wählt (20m/50m/100m)
  → Kontext-Polygone in 2D UND 3D (halbtransparent)
- Bei Slider "Aus": Keine Nachbar-Polygone sichtbar, aber blockierte Fassaden bleiben nicht anwählbar!

## E.5 Direkte Nachbarn Optimierung

```
┌─────────────────────────────────────────────────────────────┐
│          OPTIMIERUNG: DIREKTE NACHBARN ZUERST              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Nach dem Laden des Hauptgebäudes:                          │
│                                                             │
│  1. Koordinaten des Hauptgebäudes bekannt                   │
│       │                                                     │
│       ▼                                                     │
│  2. GDB scannen: Gebäude im 5m-Radius suchen               │
│     (nur Koordinaten vergleichen, schnell!)                │
│       │                                                     │
│       ▼                                                     │
│  3. Gefundene Nachbarn sofort in building_3d.db            │
│       │                                                     │
│       ▼                                                     │
│  4. blocked_facades sofort berechenbar!                    │
│       │                                                     │
│       ▼                                                     │
│  5. Diese EGIDs beim grossen Prefetch ÜBERSPRINGEN         │
│     (vermeidet Duplikate)                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implementierung:**
```python
# Nach Hauptgebäude-Parsing:
neighbors_5m = _find_neighbors_in_gdb(gdb_path, center_e, center_n, radius=5)
save_buildings_to_db(neighbors_5m)

# Beim Prefetch:
exclude_egids = {main_egid} | {n.egid for n in neighbors_5m}
prefetch_remaining(gdb_path, exclude=exclude_egids)
```

## E.6 Multi-Building Projekte

Ein Projekt kann mehrere Gebäude umfassen (z.B. "Knospenweg 4-6").

### E.6.1 SmartBuildingService Multi-Adress-Unterstützung (NEU 11.01.2026)

```
┌─────────────────────────────────────────────────────────────┐
│          SMARTBUILDINGSERVICE MULTI-ADRESS FLOW             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Eingang: ["Knospenweg 4, Bern", "Knospenweg 6, Bern"]     │
│       │                                                     │
│       ▼                                                     │
│  collect_all_data(addresses: List[str])                    │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Phase 1: Geocoding PARALLEL für alle Adressen       │   │
│  │ → [{egid: 1243790, coords: ...},                    │   │
│  │    {egid: 1243792, coords: ...}]                    │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Phase 2: Centroid berechnen                          │   │
│  │ → Mittelpunkt aller Koordinaten                      │   │
│  │ → Für Tile-Download Optimierung                      │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Phase 3: Tile laden (EIN Aufruf)                     │   │
│  │ → Prefetch startet für alle Gebäude im Tile          │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Phase 4: Für JEDES Gebäude: _enrich_building()      │   │
│  │ → Interne Cache-Prüfung                              │   │
│  │ → Falls gecacht: sofort zurück                       │   │
│  │ → Falls nicht: GWR + 3D + Terrain + Zonen           │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  Ausgang: [Bundle1, Bundle2]                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### E.6.2 Rückwärtskompatibilität

```python
# VORHER (Single-Adresse):
bundle = await service.collect_all_data("Knospenweg 4, Bern")
# → BuildingDataBundle

# NACHHER (Multi-Adresse):
bundles = await service.collect_all_data(["Knospenweg 4", "Knospenweg 6"])
# → List[BuildingDataBundle]

# NACHHER (Single-Adresse - unverändert):
bundle = await service.collect_all_data("Knospenweg 4, Bern")
# → BuildingDataBundle (wie vorher!)
```

### E.6.3 _enrich_building() - Gemeinsame Enrichment-Logik

```python
async def _enrich_building(
    self,
    address: str,
    egid: Optional[str],
    coordinates: Tuple[float, float],
    ...
) -> BuildingDataBundle:
    """
    Enrichment für ein einzelnes Gebäude.
    Wird von BEIDEN Pfaden genutzt (Single + Multi).

    1. Cache-Prüfung (mit address|egid Key)
    2. Bundle erstellen
    3. Phase 2: GWR, Building3D, Sonnendach, Terrain, Research (parallel)
    4. Validierung
    5. Dach-Berechnung
    6. Zonen-Analyse
    7. Zugänge berechnen
    8. Qualität bewerten
    9. Cache speichern
    """
```

### E.6.4 blocked_facades bei Multi-Building

```
┌─────────────────────────────────────────────────────────────┐
│              BLOCKED_FACADES BERECHNUNG                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Projekt-Gebäude: [EGID_A, EGID_B]                         │
│                                                             │
│       ┌─────┐                                               │
│       │  C  │ ← Externes Gebäude (NICHT im Projekt)        │
│       └─────┘                                               │
│          ↑ 3m Abstand                                       │
│    ┌─────┬─────┐                                            │
│    │  A  │  B  │ ← Projekt-Gebäude (zu einrüsten)          │
│    └─────┴─────┘                                            │
│                                                             │
│  BERECHNUNG für Gebäude A:                                  │
│  ─────────────────────────                                  │
│  1. Nachbarn im 5m-Radius suchen → [B, C]                  │
│  2. Projekt-Gebäude AUSSCHLIESSEN → [C]                    │
│  3. blocked_facades = Fassaden Richtung C                  │
│                                                             │
│  → A und B blockieren sich NICHT gegenseitig!              │
│                                                             │
│  Implementierung (project_context_stream.py):               │
│  ─────────────────────────────────────────────              │
│  neighbors = get_neighbors(egid, radius=5)                 │
│  external = [n for n in neighbors                          │
│              if n.egid not in project_egids]               │
│  blocked = calculate_blocked_from(external)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### E.6.5 Geänderte Dateien (11.01.2026)

| Datei | Änderung |
|-------|----------|
| `smart_building/service.py` | `collect_all_data()` akzeptiert `Union[str, List[str]]` |
| `smart_building/service.py` | `_enrich_building()` - gemeinsame Enrichment-Logik |
| `smart_building/service.py` | `_collect_multi_building_data()` - Multi-Adress-Orchestrierung |
| `smart_building/service.py` | `_geocode_address()` - Geocoding extrahiert |
| `smart_building/service.py` | `_ensure_tile_loaded()` - Tile-Download triggern |

### E.6.6 BUG-015: Point-in-Polygon für EGID-Auflösung (11.01.2026)

**Problem:** Bei Reihenhäusern zeigt die Geocoding-Koordinate auf den **Hauseingang**,
der oft näher am Nachbar-Zentrum liegt als am eigenen Gebäude-Zentrum.

```
┌─────────────────────────────────────────────────────────────┐
│              EGID-LOOKUP BEI REIHENHÄUSERN                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Knospenweg 4, 6, 8 (Reihenhäuser)                         │
│                                                             │
│       ┌─────────┬─────────┬─────────┐                      │
│       │ EGID    │ EGID    │ EGID    │                      │
│       │ 1243790 │ 1243792 │ 1243794 │                      │
│       │    ●    │    ●    │    ●    │  ● = Gebäude-Zentrum │
│       │         │         │         │                      │
│       │    X    │    X    │    X    │  X = Hauseingang     │
│       └─────────┴─────────┴─────────┘      (Geocoding)     │
│                                                             │
│  ALT (Nächstes Zentrum):                                   │
│  ─────────────────────────                                 │
│  Geocoding "Knospenweg 6" → X bei (2596298, 1199812)       │
│  Nächstes Zentrum = EGID 1243794 (Nr. 8!) ← FALSCH!       │
│                                                             │
│  NEU (Point-in-Polygon):                                   │
│  ─────────────────────────                                 │
│  Geocoding "Knospenweg 6" → X bei (2596298, 1199812)       │
│  Punkt liegt im Polygon von EGID 1243792 → KORREKT!       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Lösung:** 2-Stufen Lookup mit Point-in-Polygon Priorität:

```python
# address_parser.py - resolve_to_egids()

# Stufe 1: building_3d.db mit Point-in-Polygon
swissbuildings_egid = _lookup_egid_by_coordinates(e, n, tolerance_m=10.0)

# Stufe 2: Falls nicht in DB → Tile laden + Point-in-Polygon
if swissbuildings_egid is None:
    from app.services.swissbuildings3d_fetcher import fetch_building_polygon_for_coordinates
    result = await fetch_building_polygon_for_coordinates(e, n, skip_prefetch=True)
    if result and result.get('egid'):
        swissbuildings_egid = int(result.get('egid'))
```

**Implementierung in beiden Dateien:**

| Datei | Funktion | Methode |
|-------|----------|---------|
| `address_parser.py` | `_lookup_egid_by_coordinates()` | Ray-Casting (`_point_in_polygon()`) |
| `swissbuildings3d_fetcher.py` | `parse_gdb_for_building_polygon()` | Shapely `contains()` |

**skip_prefetch Parameter:**

```python
# swissbuildings3d_fetcher.py
async def fetch_building_polygon_for_coordinates(
    e: float, n: float,
    skip_prefetch: bool = False  # NEU: Für Address Parser
) -> Optional[Dict]:
    """
    skip_prefetch=True:
    - Lädt Tile (falls nicht gecacht)
    - Findet Gebäude via Point-in-Polygon
    - Triggert KEINEN Background-Prefetch
    - Verwendet von: address_parser.py (nur EGID brauchen)

    skip_prefetch=False (default):
    - Wie oben PLUS Background-Prefetch starten
    - Verwendet von: SmartBuildingService
    """
```

## E.7 Zusammenfassung (GEMESSEN 10.01.2026)

| Aspekt | VORHER | NACHHER (implementiert) | Verbesserung |
|--------|--------|-------------------------|--------------|
| Cold Start | ~108s | ~80s | (Tile-Download unvermeidlich) |
| Warm Cache (Stufe 1) | N/A | **0.29s** | 373x schneller |
| Nachbar (gleiches Tile) | ~108s | **0.009s** | 12000x schneller |
| Bundle-Cache | N/A | **0.015s** | 7200x schneller |
| User-Blockierung | Ja (Prefetch) | Nein (Async) | ✅ |
| blocked_facades | Nach Prefetch | Sofort (5m Nachbarn) | ✅ |

## E.8 Implementierte Änderungen (10.01.2026)

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `building_3d_service.py` | `bulk_save()` optimiert: WAL-Mode, executemany(), Batch-Commits |
| `tile_prefetch.py` | Neue Funktionen: `find_immediate_neighbors()`, `schedule_prefetch_with_neighbors()` |
| `swissbuildings3d_fetcher.py` | Verwendet `schedule_prefetch_with_neighbors()` in **Stufe 2 UND Stufe 3** |

### FIX: Prefetch auch bei Stufe 2 (10.01.2026)

**Problem:** `schedule_prefetch_with_neighbors()` wurde nur bei Stufe 3 (nach Tile-Download) aufgerufen.
Bei Stufe 2 (Tile bereits gecacht) wurde kein Prefetch gestartet → building_3d.db blieb leer.

**Lösung:** Prefetch-Aufruf auch bei Stufe 2 hinzugefügt:

```python
# In swissbuildings3d_fetcher.py, Stufe 2:
if cached_path and cached_path.exists():
    result = parse_gdb_for_building_polygon(...)
    if result:
        _save_to_building_3d(result, tile_id)

        # FIX 10.01.2026: Prefetch auch bei Stufe 2 starten
        schedule_prefetch_with_neighbors(
            tile_id=tile_id,
            gdb_path=cached_path,
            center_e=center_e,
            center_n=center_n,
            main_egid=int(main_egid) if main_egid else None,
            immediate_radius_m=5.0
        )
```

### Neue Funktionen in tile_prefetch.py

```python
# 1. Direkte Nachbarn aus GDB finden (synchron, schnell)
find_immediate_neighbors(gdb_path, center_e, center_n, radius_m=5.0)
# → Lädt nur Gebäude im Radius, nicht das ganze Tile

# 2. Nachbarn laden und speichern
load_neighbors_and_save(gdb_path, center_e, center_n, radius_m, tile_id)
# → Speichert in building_3d.db, gibt (count, egid_list) zurück

# 3. Neue Hauptfunktion (ersetzt schedule_prefetch)
schedule_prefetch_with_neighbors(tile_id, gdb_path, center_e, center_n, main_egid)
# → SYNCHRON: 5m Nachbarn laden
# → ASYNC: Rest im Background prefetchen
```

### Optimierungen in bulk_save()

```python
# SQLite-Optimierungen
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA cache_size=-64000")  # 64MB

# Batch-Insert mit executemany (1000 Rows pro Batch)
cursor.executemany(INSERT_SQL, batch)
```

### API-Response Erweiterung

Nach dem Laden eines Gebäudes enthält die Response:
```json
{
  "immediate_neighbors_loaded": 3,
  "background_prefetch_started": true
}
```

**Noch offen:**
- On-Demand Loading bei Zoom (20m, 50m, 100m)
- Multi-Building Projekt-Logik in blocked_facades

---

# Teil F: Frontend Service-Aufrufe (ConfiguratorPage)

> **Analyse 10.01.2026:** API-Calls bei "Gerüst konfigurieren"

## F.1 Aktueller Ablauf (nach Projekt-Erstellung)

```
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND PAGE FLOW                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ProjectsPage                                                   │
│       │ GET /projects → Project[] (Liste ohne Geodaten)        │
│       │                                                         │
│       └─► Klick "Details"                                       │
│           ↓                                                     │
│  ProjectDetailPage                                              │
│       │ GET /projects/{id} → ProjectWithGeodata                │
│       │ → Zeigt Übersicht, Progress, BuildingDataCard          │
│       │                                                         │
│       └─► Klick "Gerüst konfigurieren"                         │
│           ↓                                                     │
│  ConfiguratorPage                                               │
│       │ GET /projects/{id} → ProjectWithGeodata ← REDUNDANT!   │
│       │ GET /neighbors?radius_m=5                              │
│       │ GET /blocked-facades                                   │
│       └─► Bearbeitung → PUT /projects/{id}/config              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## F.2 Datenstrukturen

| Type | Inhalt | Verwendet von |
|------|--------|---------------|
| `Project` | id, name, address, status, config, client_name... | ProjectsPage (Liste) |
| `ProjectWithGeodata` | Project + geodata (Polygon, Höhen, Fassaden, Zonen) | ProjectDetailPage, ConfiguratorPage |

```typescript
// Project (Basis) - ohne Geodaten
interface Project {
  id: string;
  name: string;
  address: string;
  egid?: string;
  status: ProjectStatus;
  config?: ScaffoldConfig;  // Gerüst-Konfiguration
  client_name?: string;
  created_at: string;
}

// ProjectWithGeodata (Extended) - mit Geodaten
interface ProjectWithGeodata extends Project {
  geodata?: Geodata;  // Polygon, Höhen, Fassaden, Zonen
}
```

## F.3 Service-Aufrufe im Detail

### ProjectsPage → Liste laden

```
GET /api/v1/geruestbau/projects
    → Project[] (ohne Geodaten)
    → Für Listenansicht ausreichend
```

### ProjectDetailPage → Einzelnes Projekt

```
GET /api/v1/geruestbau/projects/{id}
    → ProjectWithGeodata (MIT Geodaten)
    → Zeigt BuildingDataCard mit Polygon-Preview
```

### ConfiguratorPage → Gerüst konfigurieren

```
AKTUELL (redundant + gekoppelt):
─────────────────────────────────
1. GET /projects/{id}        ← REDUNDANT (bereits in ProjectDetailPage geladen!)
2. GET /neighbors?radius_m=5 ← Nachbar-Polygone (gekoppelt mit blocked-facades)
3. GET /blocked-facades      ← Blockierte Fassaden

OPTIMAL (Router State + getrennte Calls):
──────────────────────────────────────────
1. location.state.project    ← Aus Navigation übernommen (kein API-Call!)
2. GET /blocked-facades      ← IMMER initial (für 2D-Markierung)
3. (User wählt Radius)
4. GET /neighbors?radius_m=20 ← ON-DEMAND (für 3D-Darstellung)
```

## F.4 Wofür werden die Services gebraucht?

| Service | Zweck | Verwendet in | Wann |
|---------|-------|--------------|------|
| **blocked-facades** | Erkennt welche Fassaden an Nachbarn grenzen → nicht anwählbar | 2D + Fassaden-Liste | Initial (IMMER) |
| **neighbors** | Liefert Polygone der Nachbargebäude | 2D + 3D | On-demand (Slider: 20m/50m/100m) |

### blocked-facades → Fassaden-Auswahl

```
┌─────────────────────────────────────────────────────────────────┐
│  blocked-facades: NICHT ANWÄHLBAR (nicht rot markiert!)        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  blocked_indices = [0, 2]                                       │
│                                                                 │
│  ┌─────────────────────────────────────────┐                   │
│  │            2D-ANSICHT                   │                   │
│  ├─────────────────────────────────────────┤                   │
│  │       Fassade 0 (N)                     │                   │
│  │       ░░░░░░░░░░░░░░  ← Ausgegraut      │                   │
│  │                                         │                   │
│  │  F1   ████████████████████████   F3     │                   │
│  │  (W)  ████  GEBÄUDE  ████████   (E)     │                   │
│  │       ████████████████████████          │                   │
│  │                                         │                   │
│  │       ░░░░░░░░░░░░░░  ← Ausgegraut      │                   │
│  │       Fassade 2 (S)                     │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
│  ┌─────────────────────────────────────────┐                   │
│  │         FASSADEN-LISTE                  │                   │
│  ├─────────────────────────────────────────┤                   │
│  │  ☐ Fassade 0 (N) - 12.5m   [DISABLED]   │ ← Nicht klickbar │
│  │  ☑ Fassade 1 (W) - 8.2m                 │ ← Wählbar        │
│  │  ☐ Fassade 2 (S) - 12.5m   [DISABLED]   │ ← Nicht klickbar │
│  │  ☑ Fassade 3 (E) - 8.2m                 │ ← Wählbar        │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
│  → 2D-Ansicht und Fassaden-Liste sind SYNCHRON                │
│  → Klick in 2D = Auswahl in Liste und umgekehrt               │
│  → Blockierte Fassaden: Ausgegraut + nicht klickbar           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### neighbors → Kontext-Darstellung (2D + 3D)

```
┌─────────────────────────────────────────────────────────────────┐
│  neighbors: KONTEXT IN 2D UND 3D                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Slider: [Aus] [20m] [50m] [100m]                              │
│                                                                 │
│  Aus:   Nur Hauptgebäude sichtbar                              │
│  20m:   + Direkte Nachbarn (blockierende Gebäude sichtbar)     │
│  50m:   + Erweiterte Umgebung                                  │
│  100m:  + Voller Kontext                                       │
│                                                                 │
│  → Gilt für BEIDE Ansichten (2D und 3D)!                       │
│  → Nachbar-Polygone werden halbtransparent dargestellt         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Wichtige Trennung

```
┌─────────────────────────────────────────────────────────────────┐
│  ZWEI SEPARATE CONCERNS                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. blocked-facades (IMMER, initial)                           │
│     ─────────────────────────────────                          │
│     • Wird beim Laden der ConfiguratorPage geholt              │
│     • Nutzt intern 5m Radius zur Berechnung                    │
│     • Liefert: blocked_indices (welche Fassaden sind blockiert)│
│     • Effekt: Blockierte Fassaden sind NICHT ANWÄHLBAR         │
│     • Unabhängig vom Nachbar-Slider!                           │
│                                                                 │
│  2. neighbors (ON-DEMAND, bei Slider > 0)                      │
│     ─────────────────────────────────────                       │
│     • Wird nur geladen wenn User Radius wählt (20m/50m/100m)   │
│     • Liefert: Nachbar-Polygone für Kontext-Darstellung        │
│     • Wird in 2D UND 3D verwendet                              │
│                                                                 │
│  → Wenn Slider auf "Aus": Keine Nachbar-Polygone sichtbar,     │
│    ABER blockierte Fassaden bleiben nicht anwählbar!           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### blocked-facades Verwendung

```
┌─────────────────────────────────────────────────────────────────┐
│  blocked-facades in 2D-Ansicht                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│       N                                                         │
│       │                                                         │
│   ┌───┴───┐                                                     │
│   │  EXT  │ ← Externes Gebäude (nicht im Projekt)              │
│   └───┬───┘                                                     │
│       │ 1.5m Abstand                                            │
│   ████████████ ← Fassade 0: BLOCKIERT (rot)                    │
│   █          █                                                  │
│ W █  PROJEKT █ E                                                │
│   █          █                                                  │
│   ████████████ ← Fassade 2: FREI (grün)                        │
│       │                                                         │
│       S                                                         │
│                                                                 │
│  blocked_indices = [0]  → Fassade 0 kann nicht eingerüstet     │
│  free_facades = [1, 2, 3]                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### neighbors Verwendung

```
┌─────────────────────────────────────────────────────────────────┐
│  neighbors in 2D + 3D Ansicht                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  WICHTIG: blocked-facades wird IMMER geladen (intern 5m)       │
│           → Blockierte Fassaden sind NICHT ANWÄHLBAR!          │
│                                                                 │
│  neighbors Slider steuert die Kontext-Darstellung:             │
│  (gilt für BEIDE Ansichten: 2D und 3D)                         │
│                                                                 │
│  radius=0 (Aus): Nur Hauptgebäude sichtbar                     │
│  radius=20:      + Nahe Nachbarn (halbtransparent)             │
│  radius=50:      + Erweiterte Umgebung                         │
│  radius=100:     + Voller Kontext                              │
│                                                                 │
│  Der Benutzer wählt den Radius über Slider:                     │
│  ┌────────────────────────────────────────┐                    │
│  │  Nachbarn:  [Aus] [20m] [50m] [100m]   │                    │
│  └────────────────────────────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## F.5 Optimierung: Router State

### Aktuell (redundanter API-Call)

```typescript
// ProjectDetailPage.tsx
const handleConfigureScaffold = () => {
  navigate(`/configurator?projectId=${project.id}`);
  // ↑ Nur projectId übergeben, ConfiguratorPage lädt nochmal
};

// ConfiguratorPage.tsx
useEffect(() => {
  const loadedProject = await geruestbauApi.getProject(projectId);
  // ↑ REDUNDANT: Projekt wurde bereits in ProjectDetailPage geladen!
}, [projectId]);
```

### Optimal (mit Router State)

```typescript
// ProjectDetailPage.tsx
const handleConfigureScaffold = () => {
  navigate(`/configurator?projectId=${project.id}`, {
    state: { project }  // ← Projekt-Daten mitgeben!
  });
};

// ConfiguratorPage.tsx
const location = useLocation();
const passedProject = location.state?.project as ProjectWithGeodata | undefined;

useEffect(() => {
  if (passedProject) {
    // Projekt aus Router State verwenden (kein API-Call!)
    setProject(passedProject);
  } else if (projectId) {
    // Fallback für Direct Links (z.B. Bookmark, Reload)
    const loadedProject = await geruestbauApi.getProject(projectId);
    setProject(loadedProject);
  }
}, [projectId, passedProject]);
```

### Vorteile

| Aspekt | Ohne Router State | Mit Router State |
|--------|-------------------|------------------|
| API-Calls | 2x getProject | 1x getProject |
| Latenz | +100-200ms | Sofort |
| Direct Links | ✅ Funktioniert | ✅ Fallback |
| Reload | ✅ Funktioniert | ✅ Fallback |

## F.6 Wo werden Daten gespeichert?

| Daten | Datenbank | Wann gespeichert |
|-------|-----------|------------------|
| Projekt-Meta (name, client, status) | `geruestbau.db` | Bei Create/Update |
| **Scaffold-Config** (Fassaden, Lagen) | `geruestbau.db/projects.config` | Bei "Speichern" |
| Geodaten (Polygon, Höhen) | `building_3d.db` | Beim Tile-Prefetch |
| Zonen, Terrain | `building_contexts.db` | Bei SmartBuilding-Call |

### Scaffold-Config Struktur

```typescript
interface ScaffoldConfig {
  overrides: ProjectOverrides;     // Manuelle Anpassungen
  settings: ScaffoldSettings;      // System, Lagenhöhe, etc.
  facades: FacadeConfig[];         // Pro Fassade: selected, has_lift, etc.
  corners: CornerConfig[];         // Eck-Konfiguration
  access_points: AccessPoint[];    // Zugänge (Lift, Treppe)
}
```

## F.7 Zusammenfassung

```
┌─────────────────────────────────────────────────────────────────┐
│              OPTIMALER FLOW (TODO)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ProjectsPage                                                   │
│       │ GET /projects → Project[]                              │
│       │                                                         │
│       └─► Klick "Details"                                       │
│           ↓                                                     │
│  ProjectDetailPage                                              │
│       │ GET /projects/{id} → ProjectWithGeodata                │
│       │                                                         │
│       └─► navigate('/configurator', { state: { project } })    │
│           ↓                                                     │
│  ConfiguratorPage                                               │
│       │ const { project } = location.state  ← KEIN API-CALL!   │
│       │ GET /blocked-facades               ← IMMER (initial)   │
│       │                                                         │
│       │ User wählt Nachbar-Radius (20m/50m/100m):              │
│       │ GET /neighbors?radius_m=20         ← ON-DEMAND         │
│       │                                                         │
│       └─► PUT /projects/{id}/config (Speichern)                │
│                                                                 │
│  Ersparnis: 1 API-Call (getProject), Nachbarn on-demand        │
│                                                                 │
│  VERHALTEN:                                                     │
│  • blocked-facades → Blockierte Fassaden NICHT ANWÄHLBAR       │
│  • neighbors → Kontext-Polygone in 2D + 3D (halbtransparent)   │
│  • Fassaden-Liste synchron mit 2D-Ansicht                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# Teil G: 3D Layer Architecture (Dach-Daten)

> **NEU 11.01.2026:** Integration von swissBUILDINGS3D Roof_solid Layer

## G.1 Übersicht: Datenquellen für Dach-Daten

```
┌─────────────────────────────────────────────────────────────────┐
│                    DACH-DATEN PRIORITÄT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PRIO 1: building_roofs (Roof_solid Layer)                      │
│  ═══════════════════════════════════════════                     │
│  → Echte 3D-Geometrie aus swissBUILDINGS3D Tile                 │
│  → roof_form: Aus Z-Level-Analyse (flachdach, satteldach, etc.) │
│  → roof_orientation: Aus Geometrie berechnet                     │
│  → roof_geometry_wkb: Echte 3D-Daten für Frontend               │
│  → Konfidenz: 0.95                                               │
│                                                                  │
│  PRIO 2: Sonnendach.ch (BFE) - ERGÄNZEND                        │
│  ═══════════════════════════════════════════                     │
│  → roof_tilt_deg: Genauere Neigung (Sonnendach-spezifisch)      │
│  → roof_azimuth_deg: Genaue Ausrichtung                          │
│  → roof_overhang_m: Dachüberstand (NICHT in Roof_solid!)        │
│  → roof_surfaces: Dachflächen mit Eignung                        │
│  → Überschreibt NICHT: roof_type, roof_orientation              │
│                                                                  │
│  PRIO 3: Berechnet (Fallback)                                    │
│  ═════════════════════════════                                   │
│  → Nur wenn KEINE echten Daten vorhanden                        │
│  → Aus Trauf-/Firsthöhe + Polygon berechnet                     │
│  → Konfidenz: 0.5-0.7                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## G.2 Datenfluss: Tile-Import → SmartBuildingService

```
┌─────────────────────────────────────────────────────────────────┐
│              TILE-IMPORT (tile_prefetch.py)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  swissBUILDINGS3D Tile (.gdb)                                   │
│       │                                                          │
│       ├─── Building_solid Layer                                  │
│       │    └─► buildings_3d (EGID, Polygon, Höhen)              │
│       │                                                          │
│       └─── Roof_solid Layer                                      │
│            │                                                     │
│            ├─► Z-Level-Analyse (roof_form_detector.py)          │
│            │   └─ flachdach, satteldach, walmdach, etc.         │
│            │                                                     │
│            └─► building_roofs (geometry_wkb, roof_form, ...)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Verknüpfung via gebaeudeeinheit
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              SMARTBUILDINGSERVICE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  _collect_building_3d_data()                                    │
│       │                                                          │
│       ├─► Polygon + Höhen aus buildings_3d                      │
│       │                                                          │
│       └─► _load_roof_data_from_db()  ← NEU 11.01.2026           │
│           │                                                      │
│           ├─ Query building_roofs via EGID                      │
│           ├─ Falls nicht gefunden: via gebaeudeeinheit          │
│           │                                                      │
│           └─► Bundle erhält:                                    │
│               • roof_type (echte Dachform)                      │
│               • roof_orientation (echte Ausrichtung)            │
│               • roof_geometry_wkb (3D-Geometrie)                │
│               • roof_z_levels (für Analyse)                     │
│               • roof_confidence = 0.95                          │
│                                                                  │
│  _calculate_roof_data()  ← NUR ALS FALLBACK                     │
│       │                                                          │
│       └─► Nur wenn roof_confidence < 0.9                        │
│                                                                  │
│  _collect_sonnendach_data()  ← ENRICHMENT                       │
│       │                                                          │
│       └─► Ergänzt: roof_tilt_deg, roof_azimuth_deg,            │
│                    roof_overhang_m, roof_surfaces               │
│       └─► Überschreibt NICHT: roof_type, roof_orientation       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## G.3 Datenbank-Schema

### building_roofs (in building_3d.db)

```sql
CREATE TABLE building_roofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gebaeudeeinheit TEXT NOT NULL,    -- Verknüpfung zu anderen Layern
    egid TEXT,                         -- Eidg. Gebäudeidentifikator
    dach_min REAL,                     -- Traufhöhe (m ü.M.)
    dach_max REAL,                     -- Firsthöhe (m ü.M.)
    roof_form TEXT,                    -- flachdach, satteldach, walmdach, etc.
    roof_angle_deg REAL,               -- Berechnete Neigung
    roof_orientation TEXT,             -- First-Verlauf (N-S, O-W, etc.)
    z_levels TEXT,                     -- JSON: [546.9, 551.0, ...]
    geometry_wkb BLOB,                 -- 3D-Geometrie als WKB
    has_full_geometry INTEGER DEFAULT 0,
    calculated_at TEXT,
    calculation_method TEXT            -- z_level_analysis, etc.
);

CREATE INDEX idx_building_roofs_egid ON building_roofs(egid);
CREATE INDEX idx_building_roofs_gebaeudeeinheit ON building_roofs(gebaeudeeinheit);
```

### BuildingDataBundle Felder (NEU 11.01.2026)

```python
# In smart_building/models.py
@dataclass
class BuildingDataBundle:
    # ... bestehende Felder ...

    # === DACH (swissBUILDINGS3D Roof_solid) - NEU 11.01.2026 ===
    roof_geometry_wkb: Optional[bytes] = None  # 3D-Geometrie als WKB
    has_roof_geometry: bool = False            # Echte Geometrie verfügbar?
    roof_z_levels: Optional[List[float]] = None  # Z-Level Verteilung
    roof_dach_min_m: Optional[float] = None    # Traufhöhe (m ü.M.)
    roof_dach_max_m: Optional[float] = None    # Firsthöhe (m ü.M.)
    roof_gebaeudeeinheit: Optional[str] = None # Verknüpfung zu Roof_solid
```

## G.4 Dachform-Erkennung (roof_form_detector.py)

```
┌─────────────────────────────────────────────────────────────────┐
│              DACHFORM AUS Z-LEVELS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Z-Level-Verteilung analysieren:                                │
│  ─────────────────────────────                                   │
│  • Alle Z-Koordinaten der 3D-Geometrie sammeln                  │
│  • Eindeutige Levels clustern (Toleranz ±0.5m)                  │
│  • Verteilung auswerten:                                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1-2 Levels, geringe Variation  → FLACHDACH            │   │
│  │  2-3 Levels, First-Trauf-Diff   → SATTELDACH           │   │
│  │  3-4 Levels, abgestuft          → WALMDACH             │   │
│  │  1 Level zentral höher          → ZELTDACH             │   │
│  │  Asymmetrisch, 1 Seite höher    → PULTDACH             │   │
│  │  Geknickt, >4 Levels            → MANSARDDACH          │   │
│  │  Viele Levels, komplex          → KOMPLEX              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Zusätzlich berechnet:                                          │
│  • roof_angle_deg: Neigung aus Höhendifferenz + Tiefe          │
│  • roof_orientation: Aus Geometrie-Analyse (längste Kante)     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## G.5 Implementierte Dateien

| Datei | Beschreibung |
|-------|--------------|
| `services/roof_3d_service.py` | Service für building_roofs Tabelle |
| `services/roof_form_detector.py` | Dachform aus Z-Levels erkennen |
| `services/tile_prefetch.py` | Parst Roof_solid beim Tile-Import |
| `services/building_3d_service.py` | Tabellen-Schema + Auto-Create |
| `services/smart_building/service.py` | `_load_roof_data_from_db()` |
| `services/smart_building/models.py` | Neue Bundle-Felder |

## G.6 API-Endpunkte

```
GET /api/v1/building/{egid}/roof
    → Dach-Daten für ein Gebäude

GET /api/v1/building/{egid}/3d-layers
    → Alle 3D-Layer (Roof, Wall, Floor)

POST /api/v1/building/{egid}/load-3d-layers
    → On-demand Wall/Floor laden (für komplexe Gebäude)
```

## G.7 On-Demand Layer Loading

Für komplexe Gebäude können Wall und Floor Layer nachgeladen werden:

```
┌─────────────────────────────────────────────────────────────────┐
│              ON-DEMAND LAYER LOADING                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pre-Import (automatisch):                                       │
│  • Building_solid → buildings_3d                                │
│  • Roof_solid → building_roofs (mit Geometrie!)                 │
│                                                                  │
│  On-Demand (bei Bedarf):                                        │
│  • Wall → building_walls                                        │
│  • Floor → building_floors                                      │
│                                                                  │
│  Trigger:                                                        │
│  • User klickt "3D-Daten laden" im Frontend                     │
│  • Gebäude als MODERATE/COMPLEX klassifiziert                   │
│  • 3D-Visualisierung aktiviert                                  │
│                                                                  │
│  Ablauf (layer_fetcher.py):                                     │
│  1. Koordinaten aus buildings_3d holen                          │
│  2. Tile downloaden (temporär)                                  │
│  3. Wall + Floor parsen (nur passende GEBAEUDEEINHEIT)         │
│  4. In DB speichern                                             │
│  5. has_3d_layers Flag setzen                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## G.8 3D-Layer Daten im SSE-Stream (12.01.2026)

> **Status:** ✅ IMPLEMENTIERT 12.01.2026 22:15
> **Referenz:** [`BUILDING_3D_SCHEMA.md`](BUILDING_3D_SCHEMA.md) - Neues Schema (ohne Floor)
> **Details:** [`3D_LAYER_USAGE.md`](3D_LAYER_USAGE.md) - Vollständige Analyse

### Das Problem

Die 3D-Layer-Daten werden im Backend **korrekt geladen**, aber **NICHT durch den SSE-Stream ans Frontend übertragen**:

```
┌─────────────────────────────────────────────────────────────────┐
│                   3D-LAYER DATENFLUSS - STATUS                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SmartBuildingService._collect_building_3d_data()               │
│       │                                                          │
│       └─► bundle.has_3d_layers = True       ✅ Backend OK        │
│       └─► bundle.has_roof_geometry = True   ✅ Backend OK        │
│       └─► bundle.roof_dach_min_m = 569.75   ✅ Backend OK        │
│       └─► bundle.roof_dach_max_m = 571.05   ✅ Backend OK        │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REST /api/v1/smart-building/data                               │
│       │                                                          │
│       └─► "has_3d_layers": true             ✅ FIX 12.01.2026    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SSE /api/v1/geruestbau/building/data/stream                    │
│       │                                                          │
│       └─► building_data_stream.py:_bundle_to_dict()             │
│           │                                                      │
│           ├─ "has_3d_layers"        ✅ FIX 12.01.2026 22:15      │
│           ├─ "has_roof_geometry"    ✅ FIX 12.01.2026 22:15      │
│           ├─ "roof_dach_min_m"      ✅ FIX 12.01.2026 22:15      │
│           └─ "roof_dach_max_m"      ✅ FIX 12.01.2026 22:15      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend useBuildingDataStream.ts                              │
│       │                                                          │
│       └─► BuildingDataBundle Interface                           │
│           │                                                      │
│           ├─ has_3d_layers?         ✅ FIX 12.01.2026 22:15      │
│           ├─ has_roof_geometry?     ✅ FIX 12.01.2026 22:15      │
│           ├─ roof_dach_min_m?       ✅ FIX 12.01.2026 22:15      │
│           └─ roof_dach_max_m?       ✅ FIX 12.01.2026 22:15      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Verfügbare 3D-Layer Daten (aus building_3d.db)

| Feld | Tabelle | Beschreibung | Nutzen für Frontend |
|------|---------|--------------|---------------------|
| `has_3d_layers` | buildings_3d | Flag: Erweiterte 3D-Daten vorhanden | UI Badge, Qualitätsindikator |
| `roof_form` | building_roofs | flachdach, satteldach, walmdach, etc. | 3D-Dach rendern |
| `roof_orientation` | building_roofs | First-Verlauf (N-S, O-W, etc.) | 3D-Dach korrekt ausrichten |
| `dach_min` | building_roofs | Traufhöhe (m ü.M.) | 3D: Echte Dachposition |
| `dach_max` | building_roofs | Firsthöhe (m ü.M.) | 3D: Echte Dachposition |
| `z_min`, `z_max` | building_walls | Wand-Höhenbereich | 3D: Fassaden-Geometrie |
| `geometry_wkb` | building_roofs/walls | 3D-Geometrie (WKB) | Echte 3D-Visualisierung |

> **Hinweis:** Floor-Layer ist redundant (≈ Building_solid Polygon) und wird **nicht** importiert.
> Siehe [`BUILDING_3D_SCHEMA.md`](BUILDING_3D_SCHEMA.md) für das neue Schema.

### Implementation: Backend

**Datei:** `backend/app/services/building_data_stream.py`

#### 1. HEIGHTS Event erweitern (Zeile 218-227)

```python
# AKTUELL:
yield SSEEvent(
    event=StreamStep.HEIGHTS,
    data={
        "traufhoehe_m": bundle.traufhoehe_m,
        "firsthoehe_m": bundle.firsthoehe_m,
        "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
        "source": height_source,
        "duration_ms": 0
    }
)

# NEU: 3D-Layer Felder hinzufügen
yield SSEEvent(
    event=StreamStep.HEIGHTS,
    data={
        "traufhoehe_m": bundle.traufhoehe_m,
        "firsthoehe_m": bundle.firsthoehe_m,
        "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
        "source": height_source,
        "duration_ms": 0,
        # NEU: 3D-Layer Daten
        "has_3d_layers": bundle.has_3d_layers,
        "has_roof_geometry": bundle.has_roof_geometry,
        "roof_dach_min_m": bundle.roof_dach_min_m,  # m ü.M.
        "roof_dach_max_m": bundle.roof_dach_max_m,  # m ü.M.
    }
)
```

#### 2. _bundle_to_dict() erweitern (Zeile 369-393)

```python
# Am Ende von _bundle_to_dict() hinzufügen:
return {
    # ... bestehende Felder ...

    # NEU: 3D-Layer Felder (12.01.2026)
    "has_3d_layers": bundle.has_3d_layers,
    "has_roof_geometry": bundle.has_roof_geometry,
    "roof_dach_min_m": bundle.roof_dach_min_m,
    "roof_dach_max_m": bundle.roof_dach_max_m,
    "roof_gebaeudeeinheit": bundle.roof_gebaeudeeinheit,
}
```

### Implementation: Frontend

**Datei:** `geruestbau-app/src/hooks/useBuildingDataStream.ts`

#### 1. BuildingDataBundle Interface erweitern (Zeile 152-201)

```typescript
export interface BuildingDataBundle {
  // ... bestehende Felder ...

  // NEU: 3D-Layer Felder (12.01.2026)
  has_3d_layers?: boolean;           // Erweiterte 3D-Daten vorhanden?
  has_roof_geometry?: boolean;       // Echte Dach-Geometrie?
  roof_dach_min_m?: number | null;   // Traufhöhe absolut (m ü.M.)
  roof_dach_max_m?: number | null;   // Firsthöhe absolut (m ü.M.)
  roof_gebaeudeeinheit?: string | null;  // Verknüpfung zu Roof-Layer
}
```

#### 2. HeightsData Interface erweitern

```typescript
export interface HeightsData {
  traufhoehe_m: number | null;
  firsthoehe_m: number | null;
  gebaeudehoehe_m: number | null;
  source: string;
  duration_ms: number;
  // NEU: 3D-Layer Felder
  has_3d_layers?: boolean;
  has_roof_geometry?: boolean;
  roof_dach_min_m?: number | null;
  roof_dach_max_m?: number | null;
}
```

### Zukünftige Verwendung im 3D-Viewer

**Datei:** `geruestbau-app/src/features/scaffold-configurator/components/threeDView/ScaffoldScene.tsx`

```typescript
// AKTUELL: Heuristik für Dach-Orientierung (Zeile 17-47)
function calculatePolygonRoofOrientation(polygon: number[][]): string {
  // Schätzt Dach-Orientierung aus längster Polygon-Seite
  // ...
}

// ZUKÜNFTIG: Echte Daten aus DB verwenden
function getRoofOrientation(buildingData: BuildingDataBundle): string {
  // 1. Echte 3D-Daten verfügbar?
  if (buildingData.has_roof_geometry && buildingData.roof_orientation) {
    return buildingData.roof_orientation;  // "N-S", "O-W", etc.
  }

  // 2. Fallback: Polygon-Heuristik
  return calculatePolygonRoofOrientation(buildingData.polygon);
}
```

### Test-Befehle

```bash
# Backend: Prüfen ob Daten im Bundle sind
curl "http://localhost:8000/api/v1/smart-building/data?address=Bundesplatz%203,%20Bern&force_refresh=true" \
  | jq '{has_3d_layers, has_roof_geometry, roof_dach_min_m, roof_dach_max_m}'

# SSE: Prüfen ob Daten im Stream sind (nach Implementation)
curl -N "http://localhost:8000/api/v1/geruestbau/building/data/stream?address=Bundesplatz%203,%20Bern" \
  | grep -o '"has_3d_layers":[^,}]*'

# DB: Direkter Check
sqlite3 backend/app/data/building_3d.db \
  "SELECT has_3d_layers FROM buildings_3d WHERE egid=2242547"
```

### Priorität

| Task | Aufwand | Nutzen | Priorität |
|------|---------|--------|-----------|
| SSE Stream erweitern | 15 Min | Daten ans Frontend | **P1** |
| Frontend Interface | 10 Min | TypeScript-Typen | **P1** |
| 3D-Viewer nutzt echte Daten | 1-2h | Bessere Visualisierung | P2 |
| Wall-Layer im Stream | 30 Min | Fassaden-Geometrie | P3 |

---

# Teil H: Terrain/Hanglage & 3D-Layer Architecture

> **Status:** ⚠️ Analyse abgeschlossen, Implementation ausstehend
> **Datum:** 13.01.2026 00:30
> **Vollständige Dokumentation:** [`3D_LAYER_ANALYSIS.md`](3D_LAYER_ANALYSIS.md)

## H.1 Kurzübersicht

### Aktueller Status

| Bereich | Status | Details |
|---------|--------|---------|
| 2D-Anzeige | ✅ OK | `terrain_height_m`, `slope_class` in BuildingDataCard |
| SSE-Stream | ✅ OK | Terrain-Event mit slope_m, slope_class |
| 3D-Viewer | ⚠️ Teilweise | Flacher Boden, kein geneigtes Terrain |
| Scaffold-Berechnung | ❌ Fehlt | `slope_class` wird ignoriert, alle Fassaden gleiche Höhe |

### Das Problem

Bei Hanglage hat jede Fassade eine **andere effektive Höhe**, aber aktuell
bekommen alle Fassaden die gleiche `traufhoehe_m`.

### Die Lösung

**Zwei Ansätze** (siehe vollständige Analyse):

1. **Wall-Layer Daten** (präziser)
   - swissBUILDINGS3D Wall-Layer hat z_min/z_max **pro Wand-Segment**
   - On-demand laden via `layer_fetcher.py`
   - Mapping Wall → Fassade implementieren

2. **Terrain-Berechnung** (Fallback)
   - swissALTI3D Höhen an Polygon-Ecken
   - `facade_heights` aus corner_heights berechnen
   - Funktioniert auch ohne Wall-Layer

### TODOs

Siehe [`3D_LAYER_ANALYSIS.md`](3D_LAYER_ANALYSIS.md) Teil 6 für vollständige TODO-Liste.

**P3 Fassaden-Höhen (T1-T4) - ✅ ALLE ERLEDIGT 14.01.2026:**
- T1: Wall→Facade Matching Prototyp ✅ 13.01.2026
- T2: facade_heights in TerrainProfile ✅ 14.01.2026 (models.py, service.py)
- T3: facade_heights in API ✅ 14.01.2026 (main.py, project_service.py)
- T4: Frontend: Fassaden-Höhen anzeigen ✅ 14.01.2026 (BuildingDataCard.tsx)

### Implementierte Features (14.01.2026)

| Feature | Backend | Frontend | Status |
|---------|---------|----------|--------|
| Wall→Side Matching (Stufe 1) | `wall_facade_matcher.py` | - | ✅ |
| Terrain-Sampling (Stufe 2) | `service.py:_collect_facade_heights()` | - | ✅ |
| Global Fallback (Stufe 3) | `service.py` | - | ✅ |
| Qualitäts-Badge | - | `BuildingDataCard.tsx:Data3DQualityBadge` | ✅ |
| Höhen pro Richtung | - | `BuildingDataCard.tsx:FacadeHeightsInfo` | ✅ |
| Project-Service Integration | `project_service.py` | - | ✅ |

### Offene Fragen (BEANTWORTET)

| # | Frage | Status | Antwort |
|---|-------|--------|---------|
| D2 | Entspricht 1 Wall-Eintrag = 1 Fassade? | ✅ | Nein, Wall ist trianguliert → Matching nötig |
| D3 | Wie matchen wir Wall → unsere Sides? | ✅ | Konvexe Hülle + Azimut-Match |
| A1 | Wall-Layer immer oder on-demand laden? | ✅ | On-demand, mit Terrain-Sampling als Fallback |

---

## Referenzen

- [`3D_LAYER_ANALYSIS.md`](3D_LAYER_ANALYSIS.md) - **Vollständige Analyse mit Use Cases und TODOs**
- [`3D_LAYER_USAGE.md`](3D_LAYER_USAGE.md) - Aktuelle 3D-Layer Verwendung
- [`BUILDING_3D_SCHEMA.md`](BUILDING_3D_SCHEMA.md) - DB-Schema Konzept

---

# Teil I: Blocking-Architektur Refactoring (TODO)

> **Stand:** 15.01.2026 03:00
> **Status:** 📋 Geplant

## I.1 Problem: Redundante Datenquellen

Die aktuelle Architektur für "blockierte Fassaden" nutzt **3 redundante Quellen**:

```
┌────────────────────────────────────────────────────────────────────────┐
│              AKTUELLE ARCHITEKTUR (Redundant!)                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  1. SSE blocked_facades (Backend-berechnet)                     │  │
│  │     └─ Endpunkt: /project-context-stream                        │  │
│  │     └─ Liefert: blocked_indices pro EGID                        │  │
│  │     └─ Frontend: blockedFacadesData → blockedDirectionsFromSSE  │  │
│  │                                                                 │  │
│  │  ⚠️ PROBLEM: blocked_indices basiert auf BACKEND-Polygon!       │  │
│  │     Das Frontend hat ein ANDERES vereinfachtes Polygon          │  │
│  │     → Index-Mismatch möglich!                                   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  2. neighbors API → blockedSides (Richtungs-Fallback)           │  │
│  │     └─ Endpunkt: /building/{egid}/neighbors                     │  │
│  │     └─ Liefert: blockedSides = ["N", "S", "O", "W"]             │  │
│  │     └─ Richtungs-basiert, nicht fassaden-spezifisch             │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  3. blockingNeighbors → Frontend Geometrie-Check (NEU)          │  │
│  │     └─ FIX 15.01.2026: Nachbarn im Frontend gefiltert           │  │
│  │     └─ facadeToPolygonDistance() < 2m → blockiert               │  │
│  │     └─ Konsistent weil auf denselben Daten wie Anzeige          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## I.2 Ziel: Vereinfachte Architektur

```
┌────────────────────────────────────────────────────────────────────────┐
│              NEUE ARCHITEKTUR (Vereinfacht)                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  SSE neighbors (nur Nachbar-Polygone)                           │  │
│  │     └─ Keine blocked_facades mehr im SSE                        │  │
│  │     └─ Nur: neighbors[] mit Polygon + Koordinaten               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                              │                                         │
│                              ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Frontend: Geometrie-Check (Single Source of Truth)             │  │
│  │     └─ blockingNeighbors = neighbors.filter(n => n.distance < 2m)│  │
│  │     └─ isFacadeBlocked() = facadeToPolygonDistance() < 2m       │  │
│  │     └─ KEINE Index-basierte Logik mehr                          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ENTFERNEN:                                                           │
│  ❌ SSE blocked_facades Event                                         │
│  ❌ blockedFacadesData State                                          │
│  ❌ blockedDirectionsFromSSE                                          │
│  ❌ blockedSides (Richtungs-Fallback)                                 │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## I.3 Implementierungsplan

| # | Aufgabe | Dateien | Priorität |
|---|---------|---------|-----------|
| I.1 | Backend: `blocked_facades` SSE-Event entfernen | `geruestbau.py`, `project_context_stream()` | P2 |
| I.2 | Frontend: `blockedFacadesData` State entfernen | `ConfiguratorPage.tsx` | P2 |
| I.3 | Frontend: `blockedDirectionsFromSSE` entfernen | `FacadePanel.tsx` | P2 |
| I.4 | Frontend: `blockedSides` Prop entfernen | `FacadePanel.tsx`, `ThreeDPanel.tsx` | P2 |
| I.5 | Frontend: Nur `blockingNeighbors` verwenden | `FacadePanel.tsx:isFacadeBlocked()` | P2 |
| I.6 | Backend: neighbors API vereinfachen | `geruestbau.py` | P3 |
| I.7 | Tests aktualisieren | - | P3 |

---

# Teil J: Storage-Strategie (Railway Pro)

> **Stand:** 15.01.2026 03:00
> **Status:** 📋 Geplant (erfordert Railway Pro)

## J.1 Problem: Volume-Nutzung

Railway Free/Starter hat nur 500MB Volume-Speicher. Aktuelle Nutzung:

| Datei | Grösse | Inhalt |
|-------|--------|--------|
| `building_3d.duckdb` | ~557 MB | Buildings + Roofs + Walls (ALLE!) |
| `geruestbau.db` | ~0.03 MB | Projekte |
| `tiles.db` | ~0.02 MB | Tile-Metadaten |
| `building_contexts.db` | ~0.25 MB | Zonen, Terrain-Cache |
| **Total** | **~557 MB** | ⚠️ Über 500MB Limit! |

**Problem:** `building_3d.duckdb` speichert Wall-Geometrie für ALLE Gebäude beim BATCH_IMPORT!

## J.2 Ziel: Ephemeral vs Volume Trennung

```
┌────────────────────────────────────────────────────────────────────────┐
│              NEUE STORAGE-STRATEGIE                                    │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  EPHEMERAL STORAGE (100GB, wiped bei Redeploy)                  │  │
│  │  ══════════════════════════════════════════════                 │  │
│  │  • tiles/ - GDB-Rohdateien (temporär)                          │  │
│  │  • parquet/ - Parquet-Dateien für Import                       │  │
│  │  • cache/ - Temporäre API-Caches                               │  │
│  │                                                                 │  │
│  │  ✅ Vorteil: Unbegrenzt, wird automatisch aufgeräumt           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  VOLUME 1: Geodaten (persistent, shared)                        │  │
│  │  ══════════════════════════════════════                         │  │
│  │  • building_3d.duckdb - NUR Metadaten:                         │  │
│  │    - EGID, Polygon, Höhen, Zentrum                             │  │
│  │    - KEINE Wall/Roof Geometrie mehr!                           │  │
│  │  • tiles.db - Tile-Metadaten                                   │  │
│  │  • building_contexts.db - Zonen, Terrain-Cache                 │  │
│  │                                                                 │  │
│  │  ✅ Geschätzte Grösse: ~50-100 MB (statt 557 MB)               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  VOLUME 2: Gerüstbau-App (persistent, projektspezifisch)        │  │
│  │  ═══════════════════════════════════════════════════            │  │
│  │  • geruestbau.db - Projekte mit:                               │  │
│  │    - Projekt-Metadaten (Name, Adresse, Client, etc.)           │  │
│  │    - buildings[] Array (Multi-Building)                        │  │
│  │    - NEU: roof_geometry (nur für Projekt-Gebäude)              │  │
│  │    - NEU: wall_geometry (nur für Projekt-Gebäude)              │  │
│  │                                                                 │  │
│  │  ✅ Bei Projekt-Löschung: Geometrie-Daten werden mitgelöscht   │  │
│  │  ✅ Geschätzte Grösse: ~1-10 MB pro aktive Projekte            │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## J.3 Config-Änderungen

```python
# config.py - NEU

# Ephemeral Storage (wiped bei Redeploy, OK für temporäre Dateien)
EPHEMERAL_DIR = Path(os.getenv("EPHEMERAL_DIR", "/tmp/geodaten"))
TILES_DIR = EPHEMERAL_DIR / "tiles"
PARQUET_DIR = EPHEMERAL_DIR / "parquet"

# Volume 1: Geodaten (persistent, shared)
GEODATEN_VOLUME = Path(os.getenv("GEODATEN_VOLUME", "/app/data/geodaten"))
BUILDING_3D_DB = GEODATEN_VOLUME / "building_3d.duckdb"
TILES_DB = GEODATEN_VOLUME / "tiles.db"
CONTEXTS_DB = GEODATEN_VOLUME / "building_contexts.db"

# Volume 2: Gerüstbau-App (persistent, projektspezifisch)
GERUESTBAU_VOLUME = Path(os.getenv("GERUESTBAU_VOLUME", "/app/data/geruestbau"))
GERUESTBAU_DB = GERUESTBAU_VOLUME / "geruestbau.db"
```

## J.4 Wall-Import nur für Projekt-Gebäude

**Aktuell (FALSCH):**
```python
# tile_prefetch.py - IMPORT_ALL_LAYERS = true
# → Speichert Wall-Geometrie für ALLE Gebäude im Tile
```

**Neu (RICHTIG):**
```python
# Wall-Geometrie NUR on-demand für ausgewählte Gebäude
# 1. User erstellt Projekt mit EGID
# 2. ConfiguratorPage lädt 3D-Daten für dieses EGID
# 3. Wall/Roof Geometrie wird in geruestbau.db gespeichert (projektspezifisch)
```

## J.5 Implementierungsplan

| # | Aufgabe | Priorität | Erfordert |
|---|---------|-----------|-----------|
| J.1 | `IMPORT_ALL_LAYERS = false` setzen | P1 | - |
| J.2 | Wall-Geometrie aus building_3d.duckdb entfernen | P2 | Migration |
| J.3 | Neue Tabellen in geruestbau.db: `project_walls`, `project_roofs` | P2 | Schema |
| J.4 | roof_3d_service.py: Speichern in geruestbau.db | P2 | Code |
| J.5 | layer_fetcher.py: Speichern in geruestbau.db | P2 | Code |
| J.6 | Railway Config: 2 Volumes einrichten | P2 | Railway Pro |
| J.7 | Ephemeral Paths konfigurieren | P2 | - |

---

# Teil K: Wall-Geometrie Optimierung

> **Stand:** 15.01.2026 05:00
> **Status:** ✅ Implementiert

## K.1 Problem: Wall speichert Geometrie für ALLE Gebäude

**Analyse 15.01.2026:**

| Tabelle | Einträge | Mit geometry_wkb | Speicher |
|---------|----------|------------------|----------|
| building_roofs | 57.700 | **4** (0.007%) | 0.02 MB |
| building_walls | 56.679 | **56.679** (100%) | **249 MB** |

**Ursache in `tile_prefetch.py`:**

```python
# ROOF (Zeile 454-457) - OPTIMIERT ✅
# OPTIMIERUNG 12.01.2026: geometry_wkb NICHT beim Prefetch speichern
geometry_wkb = None

# WALL (Zeile 349-353) - NICHT OPTIMIERT ❌
geometry_wkb = None
if feature['geometry'] is not None:
    geom = shape(feature['geometry'])
    geometry_wkb = geom.wkb  # ← Speichert Geometrie für ALLE!
```

## K.2 Korrekter Datenfluss

```
┌────────────────────────────────────────────────────────────────────────┐
│              DATENFLUSS FÜR 3D-GEOMETRIE                               │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  1. User sucht Adresse                                                 │
│     └─ Tile wird heruntergeladen (falls nicht gecacht)                │
│     └─ Für DIESES Gebäude: Wall/Roof MIT Geometrie speichern          │
│     └─ Prefetch (Background): Alle anderen Gebäude im Tile            │
│        └─ NUR Metadaten (z_min, z_max, etc.)                          │
│        └─ KEINE geometry_wkb (= NULL)                                 │
│                                                                        │
│  2. User konfiguriert Projekt                                          │
│     └─ 3D-Ansicht: Daten aus building_3d.duckdb via SSE               │
│     └─ Wall/Roof Geometrie bereits vorhanden (aus Schritt 1)          │
│                                                                        │
│  3. User speichert Projekt                                             │
│     └─ Nur Projekt-Metadaten in geruestbau.db                         │
│     └─ 3D-Daten bleiben in building_3d.duckdb (wie bisher)            │
│                                                                        │
│  4. User öffnet Projekt später                                         │
│     └─ Geometrie aus building_3d.duckdb (bereits vorhanden)           │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## K.3 Fix: Wall-Geometrie nur für angefragte Gebäude

**Datei:** `tile_prefetch.py`, Funktion `_parse_wall_layer_from_gdb()`

```python
# VORHER (speichert Geometrie für ALLE):
geometry_wkb = None
if feature['geometry'] is not None:
    geom = shape(feature['geometry'])
    geometry_wkb = geom.wkb

# NACHHER (wie Roof - nur Metadaten):
# OPTIMIERUNG 15.01.2026: geometry_wkb NICHT beim Prefetch speichern
# Reduziert DB-Grösse von ~557MB auf ~308MB (45% Ersparnis!)
# Wall-Geometrie wird nur für angefragte Gebäude gespeichert
geometry_wkb = None
```

**Zusätzlich:** Bestehende Wall-Geometrie bereinigen:
```sql
UPDATE building_walls SET geometry_wkb = NULL
WHERE egid NOT IN (SELECT DISTINCT egid FROM projects WHERE egid IS NOT NULL);
```

## K.4 Erwartete Ersparnis

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| building_3d.duckdb | 557 MB | ~308 MB |
| Wall geometry_wkb | 249 MB | ~1-5 MB (nur Projekt-Gebäude) |
| Ersparnis | - | **~45%** |

---

# Teil L: Reaktive Architektur (ZIEL)

> **NEU 16.01.2026:** Ziel-Architektur - SSE statt REST für alle relevanten Daten
> **Prinzip:** Reaktive Applikation mit SSE-Streams für optimale User Experience

## L.1 Problem: Aktueller Mischmasch

Die aktuelle Architektur verwendet **sowohl REST als auch SSE**, was zu Inkonsistenzen führt:

```
┌─────────────────────────────────────────────────────────────────┐
│              AKTUELL: MISCH-ARCHITEKTUR (Wildwuchs)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  REST-ENDPOINTS (blockierend):                                 │
│  ══════════════════════════════                                 │
│  • GET /smart-building/data      → Alle Daten auf einmal       │
│  • GET /configurator/facades     → Fassaden + building_walls   │
│  • GET /building/{egid}/neighbors → Nachbar-Gebäude            │
│                                                                 │
│  SSE-ENDPOINTS (reaktiv):                                      │
│  ═════════════════════════                                      │
│  • GET /building/data/stream     → Progressive Datenladung     │
│  • GET /project/{id}/context/stream → Projekt-Kontext          │
│                                                                 │
│  PROBLEME:                                                      │
│  ─────────                                                      │
│  • Frontend muss beide Arten handhaben                         │
│  • REST blockiert UI bis Response komplett                     │
│  • Inkonsistente Fehlerbehandlung                              │
│  • Keine Progress-Indikatoren bei REST                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## L.2 Ziel: Reaktive SSE-Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│              ZIEL: REAKTIVE SSE-ARCHITEKTUR                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SSE-ENDPOINTS (alle reaktiv):                                 │
│  ══════════════════════════════                                 │
│                                                                 │
│  1. /building/stream (HAUPT-ENDPOINT)                          │
│     ├─ event: geocoding      → Adresse aufgelöst               │
│     ├─ event: gwr            → GWR-Daten                       │
│     ├─ event: polygon        → Gebäude-Polygon                 │
│     ├─ event: heights        → Höhendaten                      │
│     ├─ event: terrain        → Hanglage                        │
│     ├─ event: walls          → building_walls[] (3D)           │
│     ├─ event: roofs          → building_roofs[] (3D)           │
│     ├─ event: zones          → Zonen-Analyse                   │
│     ├─ event: facades        → Vereinfachte Fassaden           │
│     └─ event: complete       → Alle Daten geladen              │
│                                                                 │
│  2. /project/{id}/context/stream (bestehend)                   │
│     ├─ event: centroid       → Projekt-Mittelpunkt             │
│     ├─ event: buildings      → Projekt-Gebäude                 │
│     ├─ event: blocked_facades → Blockierte Fassaden            │
│     └─ event: neighbors      → Nachbar-Gebäude (progressiv)    │
│                                                                 │
│  REST-ENDPOINTS (nur für einfache Operationen):                │
│  ═══════════════════════════════════════════════                │
│  • POST /projects            → Projekt erstellen               │
│  • PUT /projects/{id}        → Projekt aktualisieren           │
│  • DELETE /projects/{id}     → Projekt löschen                 │
│  • GET /health               → Health-Check                    │
│                                                                 │
│  VORTEILE:                                                      │
│  ─────────                                                      │
│  ✅ Sofortiges Feedback (Time to First Byte ~50ms)             │
│  ✅ Progressive UI-Updates                                      │
│  ✅ Einheitliche Fehlerbehandlung                               │
│  ✅ Abbruch jederzeit möglich                                   │
│  ✅ Konsistente Frontend-Integration                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## L.3 Migration: REST → SSE

| REST-Endpoint | SSE-Ersatz | Status |
|---------------|------------|--------|
| `GET /smart-building/data` | `/building/stream` | 🔲 TODO |
| `GET /configurator/facades` | `/building/stream` (events: facades, walls, roofs) | 🔲 TODO |
| `GET /building/{egid}/neighbors` | `/project/{id}/context/stream` (event: neighbors) | ✅ Existiert |
| `GET /building/{egid}/blocked-facades` | `/project/{id}/context/stream` (event: blocked_facades) | ✅ Existiert |

## L.4 Event-Schema für /building/stream

```typescript
// Gebäude-Daten-Stream Events
interface BuildingStreamEvents {
  // Phase 1: Geocoding
  geocoding: {
    matched_address: string;
    egid: string;
    coordinates: { lv95_e: number; lv95_n: number };
    duration_ms: number;
  };

  // Phase 2: GWR
  gwr: {
    floors: number | null;
    area_m2: number | null;
    category: string | null;
    year_built: number | null;
    duration_ms: number;
  };

  // Phase 3: 3D-Daten
  polygon: {
    polygon: number[][];
    sides: FacadeSide[];
    perimeter_m: number;
    area_m2: number;
    cache_hit: boolean;
    duration_ms: number;
  };

  heights: {
    traufhoehe_m: number | null;
    firsthoehe_m: number | null;
    gebaeudehoehe_m: number | null;
    source: string;
    has_3d_layers: boolean;
    duration_ms: number;
  };

  // Phase 4: 3D-Layer (NEU)
  walls: {
    building_walls: BuildingWall[];  // Volle 3D-Geometrie
    count: number;
    duration_ms: number;
  };

  roofs: {
    building_roofs: BuildingRoof[];  // Volle 3D-Geometrie
    count: number;
    duration_ms: number;
  };

  // Phase 5: Enrichment
  terrain: {
    terrain_height_m: number;
    slope_m: number;
    slope_class: string;
    duration_ms: number;
  };

  zones: {
    zones: ZoneInfo[];
    complexity: string;
    source: string;
    duration_ms: number;
  };

  // Phase 6: Fassaden
  facades: {
    facades: SimplifiedFacade[];  // Vereinfacht mit Höhen
    corners: Corner[];
    duration_ms: number;
  };

  // Abschluss
  complete: {
    status: 'ok' | 'partial' | 'error';
    duration_ms: number;
    summary: {
      has_polygon: boolean;
      has_heights: boolean;
      has_3d_layers: boolean;
      has_terrain: boolean;
      zones_count: number;
      facades_count: number;
    };
  };

  // Fehler (kann jederzeit kommen)
  error: {
    code: string;
    message: string;
    phase: string;
    recoverable: boolean;
  };
}
```

## L.5 Implementierungsplan

### Phase 1: Neuen SSE-Endpoint erstellen

```python
# geruestbau.py - Neuer Endpoint
@router.get("/building/stream", response_class=EventSourceResponse)
async def stream_building_data(
    address: str = Query(...),
    include_3d_layers: bool = Query(True),
    include_terrain: bool = Query(True),
    include_zones: bool = Query(True),
):
    """
    SSE-Stream für alle Gebäude-Daten.
    Ersetzt: /smart-building/data und /configurator/facades
    """
    async def event_generator():
        # Phase 1: Geocoding
        yield create_sse_event("geocoding", {...})

        # Phase 2: GWR (parallel mit 3D)
        # Phase 3: Polygon + Höhen
        # Phase 4: 3D-Layer (walls, roofs)
        # Phase 5: Terrain, Zones
        # Phase 6: Fassaden (vereinfacht mit Höhen-Matching)
        # Abschluss

    return EventSourceResponse(event_generator())
```

### Phase 2: Frontend-Hook erstellen

```typescript
// useBuildingStream.ts
export function useBuildingStream(options: BuildingStreamOptions) {
  const [state, setState] = useState<BuildingStreamState>({
    isLoading: false,
    currentPhase: null,
    geocoding: null,
    polygon: null,
    heights: null,
    walls: null,
    roofs: null,
    terrain: null,
    facades: null,
    error: null,
  });

  const start = useCallback((address: string) => {
    const eventSource = new EventSource(
      `/api/v1/geruestbau/building/stream?address=${encodeURIComponent(address)}`
    );

    eventSource.addEventListener('geocoding', (e) => {
      const data = JSON.parse(e.data);
      setState(prev => ({ ...prev, geocoding: data, currentPhase: 'geocoding' }));
    });

    eventSource.addEventListener('walls', (e) => {
      const data = JSON.parse(e.data);
      setState(prev => ({ ...prev, walls: data.building_walls, currentPhase: 'walls' }));
    });

    // ... weitere Events ...

    eventSource.addEventListener('complete', (e) => {
      setState(prev => ({ ...prev, isLoading: false }));
      eventSource.close();
    });
  }, []);

  return { ...state, start };
}
```

### Phase 3: Alte Endpoints als deprecated markieren

```python
@router.get("/smart-building/data")
@deprecated("Use /building/stream instead")
async def get_smart_building_data(...):
    """
    DEPRECATED: Verwende /building/stream für reaktive Datenladung.
    Dieser Endpoint wird in Version 4.0 entfernt.
    """
    ...
```

## L.6 Verfeinerte Szenario-Analyse

### Szenario 1: Neue Adresse eingeben (COLD - EXISTIERT BEREITS ✅)

```
User gibt Adresse ein → SSE-Stream existiert!
───────────────────────────────────────────────
GET /building/data/stream?address=...

├─ event: geocoding     (API-Call swisstopo, ~500ms)
├─ event: gwr           (API-Call swisstopo, ~300ms)
├─ event: polygon       (DB oder STAC API, 1ms-5s)
├─ event: heights       (aus DB, ~1ms)
├─ event: terrain       (API-Call swissALTI3D, ~200ms)
├─ event: zones         (berechnet/Claude, ~100ms)
└─ event: complete      (Signal)

→ SEQUENTIELL mit Feedback weil APIs langsam
→ Daten werden in DuckDB geschrieben
→ SSE ist hier RICHTIG ✅ (bereits implementiert)
```

### Szenario 2: Projekt öffnen (WARM CACHE - OPTIMIERBAR)

```
User öffnet existierendes Projekt
────────────────────────────────────────────────

AKTUELL (suboptimal):
┌─────────────────────────────────────────────┐
│  GET /projects/{id}                         │
│       │                                     │
│       ▼                                     │
│  geodata.polygon vorhanden?                 │
│       │                                     │
│  JA   │   NEIN                              │
│  ↓    │   ↓                                 │
│  Fast │   GET /configurator/facades         │
│  Path │   (BLOCKIEREND, ~200-500ms)         │
│       │                                     │
│  ⚠️ PROBLEM: Fast Path hat KEINE           │
│     building_walls / building_roofs!        │
└─────────────────────────────────────────────┘

ZIEL (optimiert):
┌─────────────────────────────────────────────┐
│  GET /projects/{id}                         │
│       │                                     │
│       ▼                                     │
│  Alle Daten aus DuckDB PARALLEL laden:      │
│  ┌─ polygon       ─┐                        │
│  ├─ heights       ─┤                        │
│  ├─ building_walls ─┼─→ ~10-50ms TOTAL     │
│  ├─ building_roofs ─┤                       │
│  ├─ terrain       ─┤                        │
│  └─ facades       ─┘                        │
│                                             │
│  → Alles aus Cache = SCHNELL               │
│  → Kein SSE nötig (REST reicht)            │
│  → ABER: building_walls/roofs müssen       │
│          im Project-Cache sein!             │
└─────────────────────────────────────────────┘
```

### Szenario 3: Projekt öffnen + Daten fehlen (PARTIAL CACHE)

```
Einige Daten fehlen (z.B. building_walls noch nicht geladen)
────────────────────────────────────────────────────────────

ZIEL:
┌─────────────────────────────────────────────┐
│  GET /projects/{id}                         │
│       │                                     │
│       ▼                                     │
│  Cache-Check: Was fehlt?                    │
│       │                                     │
│       ├─ polygon ✅ (aus Cache)             │
│       ├─ heights ✅ (aus Cache)             │
│       ├─ building_walls ❌ (fehlt!)         │
│       ├─ building_roofs ❌ (fehlt!)         │
│       └─ terrain ✅ (aus Cache)             │
│                                             │
│  → Fehlende Daten nachladen:               │
│    SSE-Event "loading_3d_layers"            │
│    → walls + roofs parallel aus GDB         │
│    → In DB schreiben                        │
│    SSE-Event "3d_layers_complete"           │
│                                             │
└─────────────────────────────────────────────┘
```

## L.7 Naming-Refactoring: `geodata` → `geruestbaudata`

### Problem: Unklares Naming

**Aktuell:** `project.geodata` - generischer Name, unklare Struktur

**Neu:** `project.geruestbaudata` - domänenspezifisch, klare Struktur

### Neues Datenmodell: `GeruestbauData`

```typescript
// project.ts - NEU
interface GeruestbauData {
  // === GEBÄUDE (aus SmartBuildingService) ===
  building: {
    egid: string;
    address: string;
    polygon: number[][];           // Original aus swissBUILDINGS3D
    polygon_simplified?: number[][]; // Vereinfacht für Fassaden
    center_e: number;
    center_n: number;
    perimeter_m: number;
    area_m2: number;
  };

  // === HÖHEN (aus swissBUILDINGS3D) ===
  heights: {
    traufhoehe_m: number;          // Traufhöhe relativ zu Terrain
    firsthoehe_m: number;          // Firsthöhe relativ zu Terrain
    gebaeudehoehe_m: number;       // Gesamthöhe
    terrain_height_m: number;      // Terrain-Höhe (m ü.M.)
    source: 'swissBUILDINGS3D' | 'gwr_estimated' | 'manual';
  };

  // === 3D-LAYER (aus swissBUILDINGS3D Wall/Roof) ===
  walls: BuildingWall[];           // Alle Wand-Polygone mit z_min/z_max
  roofs: BuildingRoof[];           // Alle Dach-Polygone mit dach_min/max

  // === TERRAIN (aus swissALTI3D) ===
  terrain: {
    height_m: number;              // Zentrale Terrain-Höhe
    min_m: number;                 // Tiefster Punkt (Polygon-Ecken)
    max_m: number;                 // Höchster Punkt
    slope_m: number;               // Höhendifferenz
    slope_class: 'eben' | 'leicht' | 'mittel' | 'stark';
    requires_level_compensation: boolean;
  };

  // === ZONEN (aus SmartBuildingService) ===
  zones: ZoneInfo[];               // Gebäudezonen (Hauptgebäude, Turm, etc.)

  // === STRASSEN/ZUFAHRT (GEPLANT - aus swisstopo TLM) ===
  astra?: {
    nearest_road_m: number;        // Distanz zur nächsten Strasse
    road_type: string;             // Quartierstrasse, Hauptstrasse, etc.
    access_points: AccessPoint[];  // Mögliche Zufahrten
  };

  // === META ===
  fetched_at: string;              // Wann wurden Daten geladen
  data_quality: 'complete' | 'partial' | 'minimal';
  missing_data?: string[];         // Was fehlt noch
}
```

### Mapping Alt → Neu

| Alt (`geodata.xxx`) | Neu (`geruestbaudata.xxx`) |
|---------------------|----------------------------|
| `polygon` | `building.polygon` |
| `traufhoehe_m` | `heights.traufhoehe_m` |
| `firsthoehe_m` | `heights.firsthoehe_m` |
| `terrain_height_m` | `terrain.height_m` |
| `slope_m` | `terrain.slope_m` |
| `building_walls` | `walls` |
| `building_roofs` | `roofs` |
| `zones` | `zones` |
| *(neu)* | `astra` |

## L.8 Datenfluss-Optimierung

### Prinzip: SmartBuildingService liefert ORIGINAL-Daten

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATENFLUSS-ARCHITEKTUR                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SZENARIO 1: Neue Adresse (SSE)                                │
│  ═══════════════════════════════                                │
│                                                                 │
│  User gibt Adresse ein                                          │
│       │                                                         │
│       ▼                                                         │
│  SmartBuildingService.collect_all_data()                       │
│       │                                                         │
│       ├─► swisstopo API (Geocoding, GWR)                       │
│       ├─► swissBUILDINGS3D (Polygon, Höhen, Walls, Roofs)      │
│       ├─► swissALTI3D (Terrain)                                │
│       └─► Claude API (Zonen bei komplexen Gebäuden)            │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ORIGINAL-DATEN (unverändert von APIs)                  │   │
│  │  → In DuckDB speichern (building_3d.duckdb)             │   │
│  │  → Via SSE ans Frontend streamen                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  Frontend (geruestbau-app)                                     │
│       │                                                         │
│       ├─► Polygon vereinfachen (Douglas-Peucker)               │
│       ├─► Fassaden-Höhen matchen (walls ↔ sides)               │
│       ├─► 3D-Visualisierung rendern                            │
│       └─► Gerüst-Konfiguration berechnen                       │
│       │                                                         │
│       ▼                                                         │
│  User klickt "Projekt erstellen"                               │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PROJEKT SPEICHERN (geruestbau.db)                      │   │
│  │  → project.geruestbaudata = ALLE Original-Daten         │   │
│  │  → project.config = User-Einstellungen                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SZENARIO 2: Projekt öffnen (WARM CACHE)                       │
│  ═══════════════════════════════════════                        │
│                                                                 │
│  User öffnet Projekt                                            │
│       │                                                         │
│       ▼                                                         │
│  GET /projects/{id}                                            │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  project.geruestbaudata VORHANDEN?                      │   │
│  │                                                         │   │
│  │  JA → Alle Daten sofort verfügbar:                      │   │
│  │       • building (polygon, center, area)                │   │
│  │       • heights (trauf, first, terrain)                 │   │
│  │       • walls[] (3D-Geometrie)                          │   │
│  │       • roofs[] (3D-Geometrie)                          │   │
│  │       • terrain (slope, compensation)                   │   │
│  │       • zones[]                                         │   │
│  │       → KEIN API-Call nötig!                            │   │
│  │       → ~10-50ms Ladezeit                               │   │
│  │                                                         │   │
│  │  NEIN (Legacy-Projekt) → Daten nachladen:               │   │
│  │       → SSE-Stream für fehlende Daten                   │   │
│  │       → In project.geruestbaudata speichern             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Vorteile dieser Architektur

| Aspekt | Aktuell | Neu |
|--------|---------|-----|
| **Projekt öffnen** | 200-500ms (API-Call) | **10-50ms** (aus DB) |
| **3D-Daten** | Fehlen im Cache | ✅ Vollständig |
| **Offline-fähig** | Nein | Ja (alles im Projekt) |
| **Konsistenz** | Daten können sich ändern | Snapshot beim Erstellen |
| **Naming** | `geodata` (unklar) | `geruestbaudata` (klar) |

### Multi-Adresse SSE (NEU 18.01.2026)

**Refaktorierung:** Single- und Multi-Adressen verwenden denselben SSE-Endpunkt
mit EINER Methode `stream_building_data()`.

```
┌─────────────────────────────────────────────────────────────────┐
│             MULTI-ADRESSE SSE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Adresse eingeben: "Knospenweg 4-6, Bern"                      │
│       │                                                         │
│       ▼                                                         │
│  Frontend: startStream(address)                                 │
│       │                                                         │
│       ▼                                                         │
│  Backend: stream_building_data(address)                        │
│       │                                                         │
│       ├─► _is_multi_address() → true (4-6 erkannt)             │
│       │                                                         │
│       ├─► AddressParser.parse() → ["Knospenweg 4", "Knospenweg 6"] │
│       │                                                         │
│       └─► Für JEDE Adresse:                                     │
│           ├─► Geocoding + GWR                                   │
│           ├─► Polygon + Höhen                                   │
│           ├─► Terrain                                           │
│           ├─► Zonen                                             │
│           └─► Research                                          │
│       │                                                         │
│       ▼                                                         │
│  SSE Events:                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Single:                                                 │   │
│  │    {matched_address: "...", egid: "...", polygon: [...]} │   │
│  │                                                         │   │
│  │  Multi:                                                  │   │
│  │    {buildings: [{...}, {...}], building_count: 2}       │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  Frontend prüft: if (data.buildings) → Multi else → Single     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Geänderte Dateien:**

| Datei | Änderung |
|-------|----------|
| `building_data_stream.py` | EINE Methode `stream_building_data()` für Single+Multi |
| `GeodataStep.tsx` | Immer `startStream()` verwenden (kein `loadMultiAddress`) |
| `useBuildingDataStream.ts` | `CompleteData.buildings[]` Interface hinzugefügt |
| `project.ts` | `BuildingEntry` mit vollen 3D-Daten |

**Vorteile:**
- Kein Code-Duplizierung mehr (vorher: `_stream_multi_building_data`)
- Einheitliches Event-Format erkennt Single/Multi automatisch
- Alle Gebäude bekommen volle 3D-Daten (Polygon, Höhen, Walls, Roofs)

## L.9 Implementierungsplan

### Phase 1: Datenmodell (P0)

```typescript
// 1. Neues Interface definieren
interface GeruestbauData { ... }

// 2. Migrations-Helper für alte Projekte
function migrateGeodataToGeruestbaudata(geodata: Geodata): GeruestbauData

// 3. Project-Interface erweitern
interface Project {
  // ... bestehende Felder ...
  geodata?: Geodata;                    // DEPRECATED
  geruestbaudata?: GeruestbauData;      // NEU
}
```

### Phase 2: Backend-Anpassungen (P1)

```python
# geruestbau.py

# 1. Beim Projekt-Erstellen: Alle Daten speichern
@router.post("/projects")
async def create_project(...):
    # SmartBuildingService liefert Original-Daten
    building_data = await smart_building_service.collect_all_data(address)

    # In geruestbaudata-Format konvertieren
    geruestbaudata = {
        "building": { ... },
        "heights": { ... },
        "walls": building_data.building_walls,
        "roofs": building_data.building_roofs,
        "terrain": { ... },
        "zones": building_data.zones,
        "fetched_at": datetime.now().isoformat(),
        "data_quality": "complete"
    }

    # Projekt mit allen Daten speichern
    project.geruestbaudata = geruestbaudata
    save_project(project)

# 2. Beim Projekt-Laden: Daten aus DB
@router.get("/projects/{id}")
async def get_project(id: str):
    project = load_project(id)

    # Alte Projekte migrieren
    if project.geodata and not project.geruestbaudata:
        project.geruestbaudata = migrate_geodata(project.geodata)
        save_project(project)  # Migration persistieren

    return project
```

### Phase 3: Frontend-Anpassungen (P1)

```typescript
// ConfiguratorPage.tsx

const handleProjectLoaded = async (project: ProjectWithGeodata) => {
  // NEU: geruestbaudata hat Priorität
  if (project.geruestbaudata) {
    console.log('Using geruestbaudata from project cache');

    // Alle Daten direkt verfügbar!
    setBuildingData({
      building: project.geruestbaudata.building,
      heights: project.geruestbaudata.heights,
      walls: project.geruestbaudata.walls,
      roofs: project.geruestbaudata.roofs,
      terrain: project.geruestbaudata.terrain,
      zones: project.geruestbaudata.zones,
    });

    setLoadingState('success');
    return;
  }

  // FALLBACK: Alte Projekte mit geodata
  if (project.geodata?.polygon) {
    // Migration im Frontend
    const geruestbaudata = migrateGeodataToGeruestbaudata(project.geodata);
    // ... Rest wie bisher
  }

  // FALLBACK: Kein Cache → API-Call
  await fetchBuildingData(project.address, project);
};
```

## L.10 Priorisierte TODO-Liste (aktualisiert)

| # | Task | Beschreibung | Priorität |
|---|------|--------------|-----------|
| 1 | **GeruestbauData Interface** | Neues Datenmodell definieren | **P0** |
| 2 | **Migration geodata → geruestbaudata** | Alte Projekte konvertieren | **P0** |
| 3 | Projekt-Erstellen anpassen | Alle Daten in geruestbaudata speichern | P1 |
| 4 | Projekt-Laden anpassen | geruestbaudata nutzen wenn vorhanden | P1 |
| 5 | SSE-Stream für fehlende Daten | Nur nachladen was fehlt | P2 |
| 6 | ASTRA-Integration | Strassen/Zufahrt-Daten | P3 |

## L.11 Altlasten & Prüfpunkte (VOR Implementierung prüfen!)

**⚠️ WICHTIG:** Nichts kaputt machen was im aktuellen Branch funktioniert!

### 1. Heights-Berechnung (Altlast)

**Aktuell:** `heights.traufhoehe_m`, `heights.firsthoehe_m` werden aus swissBUILDINGS3D **direkt** geladen (DACH_MIN, DACH_MAX).

**Problem:** Diese globalen Höhen sind oft **falsch** für komplexe Gebäude (z.B. Bundeshaus: 14.5m ist nur Arkaden-Höhe!).

**Ziel:** Heights sollten **aus den `walls` berechnet** werden:
- `traufhoehe_m` = min(wall.z_max) - terrain_height (niedrigste Wandoberkante)
- `firsthoehe_m` = max(roof.dach_max) - terrain_height (höchste Dachoberktane)

**Prüfen vor Änderung:**
- [ ] Wo werden heights aktuell berechnet/geladen? (SmartBuildingService?)
- [ ] Welche Komponenten nutzen diese Werte?
- [ ] Gibt es Fallbacks wenn keine walls vorhanden?
- [ ] Was passiert bei Gebäuden ohne 3D-Layer?

### 2. Aktuelle Implementierung (Branch-Stand)

Was funktioniert aktuell im Branch:
- ✅ `building_walls` und `building_roofs` werden aus DB geladen
- ✅ 3D-Dach-Rendering mit `createRoofFrom3DGeometry()`
- ✅ `/configurator/facades` liefert walls und roofs
- ✅ `BuildingWall` und `BuildingRoof` Interfaces definiert

**Nicht ändern ohne Prüfung:**
- `ScaffoldScene.tsx` - 3D-Rendering funktioniert
- `polygonSimplifier.ts` - Fassaden-Vereinfachung
- `/configurator/facades` Endpoint - liefert alle Daten

### 3. Naming-Konsistenz prüfen

| Ort | Aktuelles Naming | Ziel-Naming |
|-----|------------------|-------------|
| DB-Tabelle | `building_walls` | `building_walls` ✅ |
| API-Response | `building_walls` | `walls` (in geruestbaudata) |
| TypeScript | `BuildingWall` | `BuildingWall` ✅ |
| `geodata.xxx` | `building_walls` | `geruestbaudata.walls` |

---

# Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 18.01.2026 | 3.14 | facades[] Array mit konstanter Traufhöhe + is_gable Flag (FIX Gerüsthöhen-Berechnung) |
| 18.01.2026 | 3.13 | SSE Multi-Adresse: EINE Methode für Single+Multi (stream_building_data refaktoriert) |
| 16.01.2026 | 3.12 | Teil L: Reaktive SSE-Architektur (Ziel-Architektur) |
| 15.01.2026 | 3.11 | Teil I: Blocking-Architektur Refactoring, Teil J: Storage-Strategie, Teil K: Projektspezifische 3D-Daten |
| 14.01.2026 | 3.10 | T1-T4 Fassaden-Höhen End-to-End implementiert |
| 12.01.2026 | 3.9 | Teil H: Terrain/Hanglage Architecture mit TODOs |
| 12.01.2026 | 3.8 | Teil G.8: TODO 3D-Layer Daten im SSE-Stream |
| 11.01.2026 | 3.7 | Teil G: 3D Layer Architecture (Roof_solid Integration) |
| 11.01.2026 | 3.6 | Teil E.6: Multi-Building SmartBuildingService (collect_all_data mit List) |
| 10.01.2026 | 3.5 | Teil F: Frontend Service-Aufrufe Analyse (ConfiguratorPage) |
| 10.01.2026 | 3.4 | Teil E: Stufe 2 Fix - Prefetch auch bei gecachten Tiles, Timing gemessen |
| 10.01.2026 | 3.3 | Teil E implementiert: MINIMAL + ON-DEMAND Architektur |
| 10.01.2026 | 3.2 | Tile-Prefetch Timing & On-Demand Architektur (Teil E) |
| 10.01.2026 | 3.1 | Pipeline-Optimierung: Maximale Parallelisierung (Teil D) |
| 08.01.2026 | 3.0 | Building-Data-Streaming hinzugefügt (Teil C) |
| 08.01.2026 | 2.0 | Project-Context-Streaming hinzugefügt (Teil B) |
| 08.01.2026 | 1.1 | egid_tile_index entfernt |
| 07.01.2026 | 1.0 | 3-Stufen Lookup implementiert (Teil A) |
