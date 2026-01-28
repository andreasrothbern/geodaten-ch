# 3D-Layer Datenverwendung

> **Datum:** 28.01.2026 10:00
> **Status:** P1 + P2 + P3 (T1-T4) + P4 ✅ ALLE IMPLEMENTIERT
> **Basis:** BUILDING_3D_SCHEMA.md, SWISSBUILDINGS3D_ANALYSE.md, 3D_LAYER_ANALYSIS.md
> **Siehe auch:** [`3D_LAYER_USAGE_SCAFFOLDING.md`](3D_LAYER_USAGE_SCAFFOLDING.md) - Gerüst-Kalkulation Details
>
> **NEU 14.01.2026:** 3D-Dachgeometrie wird für ALLE Gebäude gerendert (Fix in ScaffoldScene.tsx)
> **NEU 17.01.2026:** Höhenberechnung und Radius-Werte dokumentiert
>
> **Siehe auch:** [`RAILWAY_DEPLOYMENT.md`](RAILWAY_DEPLOYMENT.md) - Railway Volume & Pfad-Konfiguration

---

## Höhenberechnung (NEU 17.01.2026)

### Objekt (1 oder mehrere Gebäude) vs. Nachbarn

| Gebäudetyp | Methode | Genauigkeit | Datenquelle |
|------------|---------|-------------|-------------|
| **Objekt** | Terrain-Sampling | ±0.5m | swissALTI3D (8 Polygon-Ecken) |
| **Nachbarn** | GELAENDEPUNKT | ±2-3m (Hang!) | swissBUILDINGS3D GDB |

### Formeln

**Objekt (korrekt - geruestbau.py:558-589):**
```
traufhoehe = dach_min (m ü.M.) - min(facade_z_min)

Beispiel Knospenweg 9:
  dach_min = 562.94m ü.M. (aus building_roofs)
  min(facade_z_min) = 555.80m (niedrigster Polygon-Eckpunkt via swissALTI3D)
  → traufhoehe = 7.14m
```

**Nachbarn (Prefetch - weniger genau):**
```
traufhoehe = DACH_MIN - GELAENDEPUNKT

Beispiel Knospenweg 9:
  DACH_MIN = 562.94m ü.M.
  GELAENDEPUNKT = 557.45m (Gebäudezentrum, NICHT niedrigstes Terrain!)
  → traufhoehe = 5.49m (±2.6m Abweichung bei Hanglage!)
```

### Datenfluss

```
┌─────────────────────────────────────────────────────────────────┐
│                    HÖHENBERECHNUNG DATENFLUSS                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OBJEKT (Smart-Building Endpoint)                        │
│  ════════════════════════════════════                           │
│                                                                 │
│    swissALTI3D API                    building_roofs            │
│    (Terrain-Sampling)                 (swissBUILDINGS3D)        │
│          │                                  │                   │
│          ▼                                  ▼                   │
│    facade_z_min{}                      dach_min/dach_max        │
│    {"N": 555.8, "S": 557.1, ...}       (m ü.M.)                │
│          │                                  │                   │
│          └──────────────┬───────────────────┘                   │
│                         ▼                                       │
│              traufhoehe = dach_min - min(facade_z_min)          │
│              Genauigkeit: ±0.5m                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  NACHBARN (Prefetch beim Tile-Import)                          │
│  ════════════════════════════════════                           │
│                                                                 │
│    swissBUILDINGS3D GDB                                        │
│    (direkt aus Tile)                                            │
│          │                                                      │
│          ├─► DACH_MIN (Traufhöhe m ü.M.)                       │
│          └─► GELAENDEPUNKT (einzelner Terrain-Punkt)           │
│                         │                                       │
│                         ▼                                       │
│              traufhoehe = DACH_MIN - GELAENDEPUNKT              │
│              Genauigkeit: ±2-3m bei Hanglagen                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Warum der Unterschied?

**GELAENDEPUNKT** ist ein einzelner Terrain-Punkt (meist Gebäudezentrum), der bei
Hanglagen **nicht** das niedrigste Terrain ist. Für präzise Gerüstplanung am
Hauptgebäude verwenden wir daher **Terrain-Sampling** an allen Polygon-Ecken.

Für **Nachbarn** ist diese Genauigkeit meist ausreichend, da sie primär für:
- Kollisionserkennung (blockierte Fassaden)
- 3D-Visualisierung (Kontext)

verwendet werden, nicht für die eigentliche Gerüstkalkulation.

---

## Radius-Werte (Klarstellung 17.01.2026)

| Konstante | Wert | Datei | Verwendung |
|-----------|------|-------|------------|
| `immediate_radius_m` | **5m** | `tile_prefetch.py:1267` | Prefetch: Sofortige Nachbarn |
| `BLOCKING_THRESHOLD_M` | **2m** | `geruestbau.py:747` | Fassade = "blockiert" |
| `radius_m` (Default) | **10m** | `neighbors_service.py:58` | Neighbors-API Default |
| `max_radius_m` | **100m** | `geruestbau.py:691` | Maximum erlaubt in API |

**Wichtig:** Diese Werte MÜSSEN mit dem Frontend übereinstimmen!
- Frontend `BLOCKING_THRESHOLD_M`: `FacadePanel.tsx:104`, `ConfiguratorPage.tsx:638`

---

## Blockierte Fassaden - DatenflussNein, setzte" 

**AKTUALISIERT 25.01.2026 12:00:** Neues SSE-Event `blocking_neighbors` liefert blockierende Nachbarn
> mit **Polygon-zu-Polygon Distanz** (statt Center-to-Center). BUG-030 endgültig gefixt!

### Das Problem (BUG-030)

Zwei Probleme bei blockierten Fassaden:

1. **Index-Mismatch:** Bei Polygon-Vereinfachung stimmen die Fassaden-Indizes nicht überein
2. **Leere blockingNeighbors:** Die `distance_m` im `neighbors` SSE-Event war **Center-to-Center**

```
PROBLEM 1: Index-Mismatch
  ORIGINAL-Polygon: 27 Fassaden (Index 0-26)
  VEREINFACHT:      4 Fassaden  (Index 0-3)
  → SSE blocked_indices beziehen sich auf Original!

PROBLEM 2: Center-to-Center Distanz
  neighbors[].distance_m = 15m (Center-to-Center)
  blockingNeighbors = neighbors.filter(n => n.distance_m <= 2.0)
  → IMMER LEER bei Reihenhäusern! (Center-Distanz > 10m)
  → isFacadeBlocked() hatte keine Daten zum Prüfen!
```

### Lösung: SSE `blocking_neighbors` Event

Neues SSE-Event mit **Polygon-zu-Polygon** Distanz:

| SSE Event | Inhalt | Verwendung |
|-----------|--------|------------|
| `blocked_facades` | `blocked_indices` (Original-Polygon) | Nur Fallback |
| `blocking_neighbors` | Nachbarn mit Polygon-Distanz < 2m | **PRIMÄR** |
| `neighbors` | Alle Nachbarn (Center-Distanz) | 3D-Anzeige |

### Datenfluss (v3 - 25.01.2026)

```
┌─────────────────────────────────────────────────────────────────┐
│                    BLOCKIERTE FASSADEN (v3)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User öffnet Projekt → SSE Stream startet                   │
│     ↓                                                           │
│  2. Backend (project_context_stream.py):                        │
│     │                                                           │
│     ├─► blocked_facades Event:                                  │
│     │   blocked_facades_service.calculate_for_project()        │
│     │   → blocked_indices (Original-Polygon Indizes)           │
│     │   → blockers[] mit EGID und Distanz                      │
│     │                                                           │
│     └─► blocking_neighbors Event (NEU 25.01.2026):             │
│         Sammle alle EGIDs aus blockers[]                        │
│         → Lade Polygon-Daten für jeden Blocker                 │
│         → Sende als blocking_neighbors[]                        │
│     ↓                                                           │
│  3. Frontend (useProjectContextStream.ts):                      │
│     sseData.blockingNeighbors[] = Nachbarn mit Polygonen       │
│     ↓                                                           │
│  4. Frontend (ConfiguratorPage.tsx):                           │
│     blockingNeighbors = sseData.blockingNeighbors              │
│     (nicht mehr: neighbors.filter(n => n.distance_m <= 2))     │
│     ↓                                                           │
│  5. Frontend (FacadePanel.tsx):                                │
│     │                                                           │
│     ├─► WENN blockingNeighbors vorhanden:                      │
│     │   isFacadeBlocked(facade, index)                         │
│     │   → Geometrischer Check: Fassade vs. Nachbar-Polygone    │
│     │   → facadeToPolygonDistance() < BLOCKING_THRESHOLD_M     │
│     │   → Funktioniert mit JEDEM Polygon (original/vereinfacht)│
│     │                                                           │
│     └─► FALLBACK (keine Geometrie):                            │
│         isFacadeFullyBlocked(index)                            │
│         → SSE blocked_indices (nur für Original-Polygon!)      │
│                                                                 │
│  6. Blockierte Fassade:                                         │
│     → Farbe: #e5e7eb (grau)                                    │
│     → Nicht klickbar (cursor: default)                         │
│     → In Fassaden-Liste: disabled                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `project_context_stream.py:222-263` | Neues SSE Event `blocking_neighbors` |
| `useProjectContextStream.ts` | Event empfangen, State speichern |
| `ConfiguratorPage.tsx:1012-1034` | `blockingNeighbors` aus SSE |
| `FacadePanel.tsx:448-538` | SVG-Rendering: Geometrie-Check |
| `FacadePanel.tsx:666-693` | Fassaden-Liste: Gleiche Logik |

### Warum die ersten beiden Ansätze nicht funktionierten

1. **Erster Ansatz (SSE blocked_indices):** Index-Mismatch bei vereinfachtem Polygon
2. **Zweiter Ansatz (Geometrie-Check priorisieren):** `blockingNeighbors` war LEER!
   - `neighbors[].distance_m` war Center-to-Center
   - Filterung `<= 2.0m` gab leere Liste

Der neue Ansatz liefert `blocking_neighbors` direkt vom Backend mit korrekter
Polygon-zu-Polygon Distanzberechnung aus `blocked_facades_service`.

---

## Terrain-Erweiterungen (Geplant)

### Aktueller Stand: Terrain pro Gebäude

- Jedes Gebäude einzeln: 8 Polygon-Eckpunkte parallel gesampled (~0.3s)
- Cache: `building_environment` pro EGID (nicht projekt-bezogen)

### Mögliche Erweiterung: Projekt-Terrain (100m Grid)

```
┌─────────────────────────────────────────────────────────────────┐
│            PROJEKT-BEZOGENES TERRAIN (Idee)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Projekt erstellen → Zentrum + 100m Radius definieren       │
│                                                                 │
│  2. Terrain-Grid holen:                                         │
│     │  swissALTI3D: 10x10 Grid (100 Punkte, ~10m Abstand)      │
│     │  → ~0.7s × 100 = 70s sequentiell                         │
│     │  → Mit asyncio.gather: ~3-5s                              │
│     │                                                           │
│     └→ Speichern in geruestbau.db (project_terrain)            │
│                                                                 │
│  3. Strassen/Wege holen (swissTLM3D):                          │
│     │  BBox-Query: roads_and_tracks                            │
│     └→ Speichern in geruestbau.db (project_roads)              │
│                                                                 │
│  4. 3D-View rendern:                                            │
│     │  Three.js: PlaneGeometry mit Height-Displacement          │
│     │  Strassen: LineGeometry auf Terrain                       │
│     └→ Gebäude: Wie bisher                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Verfügbare Datenquellen

| Quelle | Daten | Zugriff | Format |
|--------|-------|---------|--------|
| [swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d) | Höhenmodell | REST API, STAC | Punkte, GeoTIFF |
| [swissTLM3D Roads](https://opendata.swiss/en/dataset/swisstlm3d-strassen-und-wege) | Strassen, Wege | STAC, Download | Vector, 0.2-1.5m |
| [swissTLM3D Hiking](https://opendata.swiss/en/dataset/swisstlm3d-wanderwege) | Wanderwege | WMTS, API | Vector |
| [Cesium Quantized Mesh](https://www.swisstopo.admin.ch/en/3d-viewer-update-data) | 3D Terrain Mesh | map.geo.admin.ch | Mesh tiles |

### Priorität

**Aktuell:** Fokus auf optimale 3D-Gebäudedarstellung (Dach, Kamin, Fenster, Foto-Vision)
**Später:** Terrain-Grid und Strassen für vollständige 3D-Umgebung

---

## Executive Summary

swissBUILDINGS3D 3.0 liefert echte 3D-Gebäudemodelle mit **Wall** und **Roof** Layern.
Diese Daten ermöglichen präzisere Gerüstplanung als die bisherigen Heuristiken.

**Kernvorteile:**
- Echte Dachneigung statt Schätzung (±1° statt ±5-10°)
- Korrekte Dach-Orientierung (First-Verlauf)
- 3D-Visualisierung mit echten Fassaden-Geometrien
- Automatische Komplexitäts-Erkennung
- **✅ NEU 14.01.2026:** Fassaden-Höhen End-to-End implementiert (T1-T4)
  - Wall-Layer Matching (±0.1m) → Terrain-Sampling (±0.5m) → Global Fallback
  - BuildingDataCard zeigt Qualitäts-Badge und Höhen pro Richtung

---

## Strategische Entscheidung: Wall-Import (AKTUALISIERT 13.01.2026 18:00)

### Aktuelle Datenlage

| Metrik | Wert |
|--------|------|
| Gebäude in buildings_3d | 18'192 |
| Gebäude mit Wall-Daten | 2 (0.01%) |
| Gebäude mit Roof-Daten | 18'225 (100%) |
| Mit vollständigem 3D-Layer-Flag | 2 |

### ~~Entscheidung: Walls NICHT batch-importieren~~ REVIDIERT

> **UPDATE 13.01.2026 18:00:** Die ursprüngliche Entscheidung wurde revidiert.
> Walls werden jetzt **DOCH beim Batch-Import** extrahiert.

### NEUE Entscheidung: Walls beim Batch-Import extrahieren

**Begründung für Änderung:**
1. **Tile-Download ist teuer:** Ein Tile ist ~30MB, Download dauert 5-10s
2. **Doppelte Arbeit vermeiden:** Wenn Wall-Daten später on-demand benötigt werden,
   müsste das Tile nochmal heruntergeladen werden
3. **Tiles können gelöscht werden:** Nach Extraktion aller Layer ist das GDB
   nicht mehr nötig → Speicherersparnis ~70-80%
4. **DB-Deployment:** Vorbereitete DB kann auf Railway deployed werden
   → Schnelle Antwortzeiten ohne On-Demand Downloads

**Neue Import-Strategie:**

| Layer | Import-Zeitpunkt | Speicherung |
|-------|------------------|-------------|
| **Building_solid** | Batch | buildings_3d |
| **Roof_solid** | Batch | building_roofs |
| **Wall** | **Batch** (NEU!) | building_walls |

> **Siehe:** `docs/architecture/BATCH_IMPORT.md` für Details zur All-Layer-Import Strategie

### Fallback-Kette für Fassaden-Höhen

> **WICHTIG (15.01.2026):** Die Höhenwerte `z_min` und `z_max` sind **separate Skalarwerte**,
> NICHT abhängig von `geometry_wkb`! Sie werden beim Prefetch aus den GDB-Attributen berechnet:
>
> ```python
> # tile_prefetch.py - Höchste Konfidenz (LiDAR)
> z_min = GELAENDEPUNKT                    # Terrain-Höhe (m ü.M.)
> z_max = GELAENDEPUNKT + GESAMTHOEHE      # Wandoberkante (m ü.M.)
> ```
>
> | Feld | Gespeichert bei Prefetch | Beschreibung |
> |------|--------------------------|--------------|
> | `z_min` | ✅ JA | Terrain-Höhe am Gebäude (Skalar) |
> | `z_max` | ✅ JA | Wandoberkante (Skalar) |
> | `geometry_wkb` | ❌ NULL | 3D-Geometrie (nur On-Demand, spart ~250 MB) |
>
> **Fazit:** Alle per Prefetch geladenen Gebäude haben bereits die Höhendaten mit höchster Konfidenz!

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FASSADEN-HÖHEN FALLBACK-KETTE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STUFE 1: Wall-Layer z_min/z_max (höchste Präzision)                    │
│  ════════════════════════════════════════════════════                    │
│  Bedingung: building_walls Einträge vorhanden (via Prefetch!)           │
│                                                                          │
│     Datenquelle: building_walls.z_min, building_walls.z_max             │
│          │                                                               │
│          └─► Für jede Fassade: z_min, z_max aus DB-Spalten (NICHT WKB!) │
│              • z_min = GELAENDEPUNKT (m ü.M.) - beim Prefetch berechnet │
│              • z_max = GELAENDEPUNKT + GESAMTHOEHE (m ü.M.)             │
│              • Konfidenz: 1.0 (LiDAR-Daten aus swissBUILDINGS3D)        │
│                                                                          │
│  STUFE 2: swissALTI3D Terrain-Sampling (gute Präzision)                 │
│  ══════════════════════════════════════════════════════                  │
│  Bedingung: Polygon mit sides vorhanden                                 │
│                                                                          │
│     Für jede Fassade:                                                   │
│          │                                                               │
│          ├─► Terrain-Höhe an Start-Punkt: terrain_service.get_height()  │
│          ├─► Terrain-Höhe an End-Punkt: terrain_service.get_height()    │
│          │                                                               │
│          └─► z_min = min(start_terrain, end_terrain)                    │
│              z_max = z_min + traufhoehe_m                               │
│              Konfidenz: 0.7                                              │
│                                                                          │
│  STUFE 3: Globale Höhe (Fallback)                                       │
│  ════════════════════════════════                                        │
│  Bedingung: Immer verfügbar                                             │
│                                                                          │
│     Für alle Fassaden:                                                  │
│          │                                                               │
│          └─► z_min = bundle.terrain.reference_height_m                  │
│              z_max = z_min + bundle.traufhoehe_m                        │
│              Konfidenz: 0.5                                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Datenfluss im TerrainProfile (✅ T2 implementiert 14.01.2026):**

```python
@dataclass
class TerrainProfile:
    reference_height_m: float      # Terrain am Gebäude-Zentrum
    min_height_m: float            # Niedrigster Punkt
    max_height_m: float            # Höchster Punkt
    slope_m: float                 # Höhendifferenz
    is_sloped: bool                # > 1m Differenz
    slope_direction: str           # Haupt-Gefällerichtung

    # ✅ IMPLEMENTIERT 14.01.2026 (T2): Fassaden-Höhen
    facade_z_min: Dict[str, float] = field(default_factory=dict)
    # {"N": 541.0, "E": 543.5, ...} - Terrain-Höhe (m ü.M.) an der Fassade

    facade_z_max: Dict[str, float] = field(default_factory=dict)
    # {"N": 550.0, "E": 552.0, ...} - Wandoberkante (m ü.M.) an der Fassade

    facade_heights_source: str = "global"
    # "wall_layer" | "terrain_sampled" | "global"
```

**Implementierte Dateien:**
- `models.py:100-107` - TerrainProfile Datenklasse
- `service.py:850-920` - _collect_facade_heights() Methode
- `service.py:834-851` - Cache-aware Terrain-Loading mit Fassaden-Höhen

### TODO: Alpha-Shape für komplexe Gebäude

Der aktuelle WallFacadeMatcher verwendet **konvexe Hülle** zur Extraktion
der Wall-Basislinien. Dies funktioniert gut für einfache rechteckige Gebäude,
aber nicht für:

- **U-Form** (Innenhöfe werden ignoriert)
- **L-Form** (Einbuchtungen werden ausgefüllt)
- **Komplexe Grundrisse** (Details gehen verloren)

**Geplante Verbesserung:** Alpha-Shape statt konvexe Hülle

```python
# Aktuell (konvexe Hülle):
hull = MultiPoint(base_points_2d).convex_hull

# Geplant (Alpha-Shape):
from shapely.ops import alpha_shape
alpha = 0.5  # Anpassen je nach Gebäudegröße
shape = alpha_shape(base_points_2d, alpha=alpha)
```

**Priorität:** P3 (Nice-to-have, bei Bedarf implementieren)

---

## Datenstruktur

### Tabellen-Übersicht (building_3d.db)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           building_3d.db                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    buildings_3d (Haupttabelle)                   │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  egid              INTEGER PRIMARY KEY                           │    │
│  │  polygon           TEXT (JSON)         ← Gebäude-Grundriss       │    │
│  │  traufhoehe_m      REAL                ← Traufhöhe (relativ)     │    │
│  │  firsthoehe_m      REAL                ← Firsthöhe (relativ)     │    │
│  │  gebaeudehoehe_m   REAL                ← Gesamthöhe              │    │
│  │  center_e, center_n REAL               ← LV95 Zentroid           │    │
│  │  tile_id           TEXT                ← Referenz zum Tile       │    │
│  │  has_3d_layers     INTEGER DEFAULT 0   ← NEU: Flag für 3D-Daten  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                │                                         │
│                                │ 1:n (via EGID)                          │
│                                ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    building_roofs (Dach-Layer)                   │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  id                INTEGER PRIMARY KEY                           │    │
│  │  egid              TEXT NOT NULL       ← FK zu buildings_3d      │    │
│  │  gebaeudeeinheit   TEXT                ← Verknüpft mehrere Dächer│    │
│  │  ─────────────────────────────────────────────────────────────── │    │
│  │  dach_min          REAL                ← Traufhöhe (m ü.M.)      │    │
│  │  dach_max          REAL                ← Firsthöhe (m ü.M.)      │    │
│  │  ─────────────────────────────────────────────────────────────── │    │
│  │  roof_form         TEXT                ← 'satteldach', etc.      │    │
│  │  roof_orientation  TEXT                ← 'N-S', 'O-W', etc.      │    │
│  │  roof_angle_deg    REAL                ← Berechnete Neigung      │    │
│  │  ─────────────────────────────────────────────────────────────── │    │
│  │  geometry_wkb      BLOB                ← 3D-Geometrie (optional) │    │
│  │  z_levels          TEXT (JSON)         ← Z-Level Verteilung      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    building_walls (Wand-Layer)                   │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  id                INTEGER PRIMARY KEY                           │    │
│  │  egid              TEXT NOT NULL       ← FK zu buildings_3d      │    │
│  │  gebaeudeeinheit   TEXT                ← Verknüpfung             │    │
│  │  ─────────────────────────────────────────────────────────────── │    │
│  │  z_min             REAL                ← Bodenhöhe (m ü.M.)      │    │
│  │  z_max             REAL                ← Wandoberkante (m ü.M.)  │    │
│  │  ─────────────────────────────────────────────────────────────── │    │
│  │  geometry_wkb      BLOB                ← 3D-Fassaden (optional)  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

> **Hinweis:** Floor-Layer wird NICHT importiert (redundant zu Building_solid Polygon).

### Höhen: Relativ vs. Absolut

| Feld | Einheit | Beschreibung | Quelle |
|------|---------|--------------|--------|
| `traufhoehe_m` | m (relativ) | Traufhöhe über Terrain | buildings_3d (berechnet) |
| `firsthoehe_m` | m (relativ) | Firsthöhe über Terrain | buildings_3d (berechnet) |
| `dach_min` | m ü.M. | Traufhöhe absolut | building_roofs (direkt) |
| `dach_max` | m ü.M. | Firsthöhe absolut | building_roofs (direkt) |
| `z_min` | m ü.M. | Wand-Unterkante | building_walls (direkt) |
| `z_max` | m ü.M. | Wand-Oberkante | building_walls (direkt) |

**Umrechnung:**
```
traufhoehe_m = dach_min - gelaendepunkt
firsthoehe_m = dach_max - gelaendepunkt
```

### Dachform-Werte (roof_form)

| Wert | Beschreibung | Erkennung |
|------|--------------|-----------|
| `flachdach` | < 5° Neigung | 1-2 Z-Levels, geringe Variation |
| `satteldach` | First mittig | 2-3 Z-Levels, symmetrisch |
| `walmdach` | 4 geneigte Flächen | 3-4 Z-Levels, abgestuft |
| `pultdach` | 1 Neigungsrichtung | Asymmetrisch, 1 Seite höher |
| `zeltdach` | Spitz zulaufend | 1 Level zentral höher |
| `mansarddach` | Geknickte Flächen | >4 Z-Levels, komplex |
| `komplex` | Nicht klassifizierbar | Viele Levels, unregelmässig |

### Dach-Orientierung (roof_orientation)

| Wert | Bedeutung | First verläuft |
|------|-----------|----------------|
| `N-S` | Dach neigt nach Ost/West | Nord-Süd |
| `O-W` | Dach neigt nach Nord/Süd | Ost-West |
| `NO-SW` | Diagonal | Nordost-Südwest |
| `NW-SO` | Diagonal | Nordwest-Südost |

---

## TypeScript Datenstruktur (Frontend)

### Erweiterte Interfaces

```typescript
// hooks/useBuildingDataStream.ts

/**
 * 3D-Layer Daten aus swissBUILDINGS3D Roof/Wall Layer.
 * Werden im SSE-Stream mit dem 'heights' Event geliefert.
 */
export interface Layer3DData {
  /** Flag: Erweiterte 3D-Daten (Wall/Roof) wurden importiert */
  has_3d_layers: boolean;

  /** Flag: Echte 3D-Dachgeometrie (WKB) verfügbar */
  has_roof_geometry: boolean;

  /** Traufhöhe absolut (Meter über Meer) */
  roof_dach_min_m: number | null;

  /** Firsthöhe absolut (Meter über Meer) */
  roof_dach_max_m: number | null;

  /** Verknüpfung zu anderen Layern (UUID) */
  roof_gebaeudeeinheit: string | null;
}

/**
 * Erweiterte Höhendaten mit 3D-Layer Informationen.
 */
export interface HeightsData extends Layer3DData {
  /** Traufhöhe relativ zum Terrain (m) */
  traufhoehe_m: number | null;

  /** Firsthöhe relativ zum Terrain (m) */
  firsthoehe_m: number | null;

  /** Gesamthöhe des Gebäudes (m) */
  gebaeudehoehe_m: number | null;

  /** Datenquelle: 'swissBUILDINGS3D', 'gwr', 'default' */
  source: string;

  /** Dauer der Abfrage (ms) */
  duration_ms: number;
}

/**
 * Dach-Daten aus building_roofs Tabelle.
 */
export interface RoofLayerData {
  /** Erkannte Dachform */
  roof_form: 'flachdach' | 'satteldach' | 'walmdach' | 'pultdach' |
             'zeltdach' | 'mansarddach' | 'komplex' | null;

  /** First-Verlauf (N-S, O-W, etc.) */
  roof_orientation: 'N-S' | 'O-W' | 'NO-SW' | 'NW-SO' | null;

  /** Berechnete Dachneigung (°) */
  roof_angle_deg: number | null;

  /** Z-Level Verteilung für Analyse */
  z_levels: number[] | null;
}

/**
 * Wand-Daten aus building_walls Tabelle.
 */
export interface WallLayerData {
  /** Wand-Unterkante (m ü.M.) */
  z_min: number | null;

  /** Wand-Oberkante (m ü.M.) */
  z_max: number | null;

  /** Berechnete Wandhöhe (m) */
  wall_height: number | null;
}

/**
 * Vollständiges BuildingDataBundle mit 3D-Layer Erweiterungen.
 */
export interface BuildingDataBundle {
  // === Identifikation ===
  address_input: string;
  address_matched: string | null;
  egid: string | null;
  lv95_e: number | null;
  lv95_n: number | null;

  // === Polygon & Fassaden ===
  polygon: number[][] | null;
  sides: FacadeData[] | null;
  perimeter_m: number | null;
  footprint_area_m2: number | null;

  // === Höhen (relativ) ===
  traufhoehe_m: number | null;
  firsthoehe_m: number | null;
  gebaeudehoehe_m: number | null;

  // === GWR-Daten ===
  gwr_floors: number | null;
  gwr_area_m2: number | null;
  gwr_category: string | null;
  gwr_category_code: number | null;

  // === Terrain ===
  terrain: TerrainData | null;

  // === Zonen ===
  zones: ZoneData[] | null;
  complexity: string | null;

  // === Research ===
  building_name: string | null;
  building_type: string | null;
  architectural_style: string | null;
  research_source: string | null;

  // === NEU: 3D-Layer Daten (12.01.2026) ===
  has_3d_layers: boolean;
  has_roof_geometry: boolean;
  roof_dach_min_m: number | null;  // m ü.M.
  roof_dach_max_m: number | null;  // m ü.M.
  roof_gebaeudeeinheit: string | null;

  // Optional: Detaillierte Layer-Daten (bei has_3d_layers=true)
  roof_layer?: RoofLayerData;
  wall_layer?: WallLayerData;
}
```

---

## Anwendungsfälle

### 1. Qualitätsindikator im UI

```typescript
// components/BuildingCard.tsx

function QualityBadge({ data }: { data: BuildingDataBundle }) {
  if (data.has_3d_layers) {
    return (
      <Badge color="green" title="Echte 3D-Daten aus swissBUILDINGS3D">
        3D-Daten ✓
      </Badge>
    );
  }
  return (
    <Badge color="yellow" title="Höhen geschätzt aus GWR">
      Geschätzt
    </Badge>
  );
}
```

### 2. Präzise Dach-Orientierung im 3D-Viewer

```typescript
// threeDView/ScaffoldScene.tsx

function createRoofMesh(building: BuildingDataBundle): THREE.Mesh {
  // 1. Echte Daten verfügbar?
  if (building.has_roof_geometry && building.roof_layer?.roof_orientation) {
    // Verwende echte Dach-Orientierung aus DB
    const orientation = building.roof_layer.roof_orientation;
    const angle = building.roof_layer.roof_angle_deg || 30;

    return createRoofWithOrientation(
      building.polygon,
      orientation,  // "N-S", "O-W", etc.
      angle         // Echte Neigung
    );
  }

  // 2. Fallback: Heuristik aus Polygon
  const estimatedOrientation = calculatePolygonRoofOrientation(building.polygon);
  const estimatedAngle = estimateRoofAngle(
    building.traufhoehe_m,
    building.firsthoehe_m,
    getBuildingDepth(building.polygon)
  );

  return createRoofWithOrientation(
    building.polygon,
    estimatedOrientation,
    estimatedAngle
  );
}
```

### 3. Gerüsthöhen-Berechnung mit absoluten Höhen

```typescript
// services/scaffoldCalculator.ts

function calculateScaffoldHeight(
  building: BuildingDataBundle,
  terrainHeight: number  // Terrain am Gerüststandort (m ü.M.)
): number {
  // Bei 3D-Layer Daten: Absolute Höhen verwenden
  if (building.has_3d_layers && building.roof_dach_max_m) {
    // Gerüst muss bis First reichen
    const scaffoldTopAbsolute = building.roof_dach_max_m + 1.0;  // +1m Überstand
    return scaffoldTopAbsolute - terrainHeight;
  }

  // Fallback: Relative Höhe + Terrain-Referenz
  const terrainRef = building.terrain?.reference_height_m || terrainHeight;
  return (building.firsthoehe_m || 10) + 1.0;
}
```

### 4. Hanglage-Kompensation bei Fassaden

```typescript
// Bei Gebäuden am Hang kann die Wandhöhe je nach Fassade variieren

function getFacadeHeight(
  building: BuildingDataBundle,
  facadeIndex: number,
  facadeStartTerrain: number,  // Terrain-Höhe am Fassaden-Start (m ü.M.)
  facadeEndTerrain: number     // Terrain-Höhe am Fassaden-Ende (m ü.M.)
): { startHeight: number; endHeight: number } {

  if (building.has_3d_layers && building.wall_layer) {
    // Echte Wand-Oberkante aus DB
    const wallTop = building.wall_layer.z_max;

    return {
      startHeight: wallTop - facadeStartTerrain,
      endHeight: wallTop - facadeEndTerrain
    };
  }

  // Fallback: Konstante Höhe
  const height = building.traufhoehe_m || 10;
  return { startHeight: height, endHeight: height };
}
```

### 5. Komplexitäts-Erkennung verbessern

```typescript
// services/complexityDetector.ts

function detectComplexity(building: BuildingDataBundle): 'simple' | 'moderate' | 'complex' {
  // 3D-Layer Daten geben Hinweise auf Komplexität
  if (building.has_3d_layers && building.roof_layer) {
    const roofForm = building.roof_layer.roof_form;

    // Mansarddach oder komplex → definitiv COMPLEX
    if (roofForm === 'mansarddach' || roofForm === 'komplex') {
      return 'complex';
    }

    // Viele Z-Levels → wahrscheinlich komplex
    const zLevels = building.roof_layer.z_levels || [];
    if (zLevels.length > 4) {
      return 'complex';
    }
  }

  // Bestehende Logik als Fallback
  return existingComplexityLogic(building);
}
```

---

## Datenfluss: Vom Import bis zur Verwendung

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KOMPLETTER DATENFLUSS                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. TILE-IMPORT (tile_prefetch.py)                                      │
│  ═════════════════════════════════                                       │
│                                                                          │
│     swissBUILDINGS3D Tile (.gdb)                                        │
│          │                                                               │
│          ├─► Building_solid → buildings_3d                              │
│          │   • EGID, Polygon, Höhen (relativ)                           │
│          │   • center_e, center_n                                       │
│          │                                                               │
│          ├─► Roof_solid → building_roofs                                │
│          │   • dach_min, dach_max (absolut)                             │
│          │   • roof_form (aus Z-Level-Analyse)                          │
│          │   • roof_orientation (aus Geometrie)                         │
│          │                                                               │
│          └─► Wall (on-demand) → building_walls                          │
│              • z_min, z_max (absolut)                                   │
│              • geometry_wkb (3D-Fassaden)                               │
│                                                                          │
│          → has_3d_layers = 1 setzen                                     │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  2. SMARTBUILDINGSERVICE (service.py)                                   │
│  ═════════════════════════════════════                                   │
│                                                                          │
│     _collect_building_3d_data()                                         │
│          │                                                               │
│          ├─► buildings_3d Query → Polygon + relative Höhen              │
│          │                                                               │
│          └─► _load_roof_data_from_db()                                  │
│              │                                                           │
│              └─► building_roofs Query → Bundle-Felder:                  │
│                  • bundle.has_3d_layers = True                          │
│                  • bundle.has_roof_geometry = True                      │
│                  • bundle.roof_dach_min_m = dach_min                    │
│                  • bundle.roof_dach_max_m = dach_max                    │
│                  • bundle.roof_type = roof_form                         │
│                  • bundle.roof_orientation = roof_orientation           │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  3. REST API (main.py:3710)                                             │
│  ══════════════════════════                                              │
│                                                                          │
│     GET /api/v1/smart-building/data                                     │
│          │                                                               │
│          └─► Response enthält:                                          │
│              • "has_3d_layers": true  ✅                                │
│              • "has_roof_geometry": true  ✅                            │
│              • "roof_dach_min_m": 569.75  ✅                             │
│              • "roof_dach_max_m": 571.05  ✅                             │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  4. SSE STREAM (building_data_stream.py) - ✅ IMPLEMENTIERT             │
│  ══════════════════════════════════════════════════════════              │
│                                                                          │
│     GET /api/v1/geruestbau/building/data/stream                         │
│          │                                                               │
│          ├─► 'heights' Event:                                           │
│          │   • has_3d_layers  ✅                                        │
│          │   • has_roof_geometry  ✅                                    │
│          │   • roof_dach_min_m  ✅                                      │
│          │   • roof_dach_max_m  ✅                                      │
│          │                                                               │
│          └─► 'complete' Event (bundle):                                 │
│              • Alle 3D-Layer Felder  ✅                                 │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  5. FRONTEND (useBuildingDataStream.ts) - ✅ IMPLEMENTIERT              │
│  ═══════════════════════════════════════════════════════                 │
│                                                                          │
│     EventSource empfängt:                                               │
│          │                                                               │
│          └─► BuildingDataBundle mit 3D-Layer Feldern                    │
│              │                                                           │
│              ├─► ConfiguratorPage State  ✅                             │
│              │                                                           │
│              ├─► ScaffoldScene (3D-Viewer)  ✅                          │
│              │   • Echte Dach-Orientierung                              │
│              │   • Präzise Höhen                                        │
│              │                                                           │
│              └─► BuildingDataCard (UI)  ✅ 14.01.2026                   │
│                  • Data3DQualityBadge: Grün/Blau/Gelb                   │
│                  • FacadeHeightsInfo: Höhen pro Richtung                │
│                                                                          │
│  6. PROJECT-SERVICE (project_service.py) - ✅ NEU 14.01.2026            │
│  ════════════════════════════════════════════════════════                │
│                                                                          │
│     get_project_with_data():                                            │
│          │                                                               │
│          ├─► _get_bundle_from_smart_service(egid)                       │
│          │   • terrain mit facade_z_min/z_max  ✅                       │
│          │   • has_3d_layers Flag  ✅                                   │
│          │                                                               │
│          └─► geodata Dict für Frontend                                  │
│              • facade_z_min, facade_z_max  ✅                           │
│              • facade_heights_source  ✅                                │
│              • terrain_height_m, slope_m  ✅                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Prioritäten für Implementation

### P1: Kritisch (blockiert Features) - ✅ ERLEDIGT 12.01.2026 22:15

| Task | Datei | Status |
|------|-------|--------|
| SSE Stream: 3D-Layer Felder hinzufügen | `building_data_stream.py:218-232` | ✅ |
| Frontend Interface erweitern | `useBuildingDataStream.ts:91-103, 197-206` | ✅ |

### P2: Wichtig (verbessert UX) - ✅ ERLEDIGT 12.01.2026 23:00

| Task | Datei | Status |
|------|-------|--------|
| 3D-Viewer: Echte Dach-Orientierung | `ConfiguratorPage.tsx:617-650` | ✅ 12.01.2026 22:45 |
| UI: Qualitäts-Badge für 3D-Daten | `BuildingDataCard.tsx:56-75` | ✅ 12.01.2026 23:00 |

**P2.1 Details (Dach-Orientierung):**
- SSE Stream erweitert: `roof_type`, `roof_orientation`, `roof_angle_deg`
- `Geodata` Interface erweitert: `has_3d_layers`, `roof_*` Felder
- `ConfiguratorPage.tsx`: Echte Daten priorisiert, Fallback auf Heuristik
- Höhere Konfidenz (0.95) bei echten 3D-Layer Daten

**P2.2 Details (Qualitäts-Badge):**
- Neues Badge in `BuildingDataCard.tsx`: `Data3DQualityBadge`
- Grün: "3D-Daten ✓" wenn `has_3d_layers === true`
- Gelb: "Geschätzt" wenn keine echten 3D-Daten
- Tooltip mit Details zur Datenquelle

### P3: Fassaden-Höhen (T1-T4) - ✅ ALLE ERLEDIGT 14.01.2026

| Task | Datei | Status | Ergebnis |
|------|-------|--------|----------|
| **T1:** Wall→Facade Matching | `wall_facade_matcher.py` | ✅ 13.01.2026 | Prototyp funktioniert |
| **T2:** facade_heights in TerrainProfile | `models.py`, `service.py` | ✅ 14.01.2026 | 3-stufige Fallback-Kette |
| **T3:** facade_heights in API | `main.py`, `project_service.py` | ✅ 14.01.2026 | Serialisierung komplett |
| **T4:** Frontend: Fassaden-Höhen anzeigen | `BuildingDataCard.tsx` | ✅ 14.01.2026 | Badge + Höhen-Grid |

### P4: Fassaden-Höhen in Gerüst-Kalkulation - ✅ IMPLEMENTIERT 14.01.2026

| Task | Datei | Status | Beschreibung |
|------|-------|--------|--------------|
| Fassaden-Höhen bei Hanglage nutzen | `polygonSimplifier.ts` | ✅ | `sidesToFacades()` mit `facadeZMin`/`facadeZMax` |
| Types erweitern | `scaffold.types.ts` | ✅ | `SelectedFacade` mit `facade_z_min`, `facade_z_max`, `height_source` |
| FacadePanel Props | `FacadePanel.tsx` | ✅ | Props für Fassaden-Höhen |
| ScaffoldConfigurator Props | `ScaffoldConfigurator.tsx` | ✅ | Props-Durchreichung |
| ConfiguratorPage Integration | `ConfiguratorPage.tsx` | ✅ | `geodata.facade_z_min`/`facade_z_max` |

**Details:** Siehe [`3D_LAYER_USAGE_SCAFFOLDING.md`](3D_LAYER_USAGE_SCAFFOLDING.md)

### P5: Weitere 3D-Layer Erweiterungen (Geplant)

| Task | Datei | Status | Aufwand |
|------|-------|--------|---------|
| Alpha-Shape für komplexe Gebäude | `wall_facade_matcher.py` | 📋 Geplant | 2-3h |
| Komplexitäts-Erkennung verbessern | `complexityDetector.ts` | 📋 Geplant | 1h |

### T1 Details: WallFacadeMatcher (Implementiert)

**Dateien:**
- `backend/app/services/smart_building/wall_facade_matcher.py` (NEU)
- `backend/app/services/smart_building/__init__.py` (erweitert)

**Klassen:**
- `WallSegment` - Ein Wand-Segment aus dem Wall-Layer
- `FacadeHeight` - Höhendaten für eine Fassade
- `WallFacadeMatcher` - Matching-Service

**Matching-Algorithmus:**
1. Wall-Segmente für EGID aus DB laden
2. WKB → 2D-Basislinien extrahieren (konvexe Hülle der Bodenpunkte)
3. Für jede Side die beste Wall finden (Azimut, Distanz, Länge)
4. Scoring: Azimut (60%), Distanz (30%), Länge (10%), Threshold 0.3

**Limitierungen:**
- Matching-Rate: ~33% (getestet mit EGID 2245881)
- Konvexe Hülle: Nicht optimal für U-Form, L-Form
- Wall-Daten müssen erst on-demand importiert werden

**Verwendung:**
```python
from app.services.smart_building import get_wall_facade_matcher

matcher = get_wall_facade_matcher()
facade_heights = matcher.get_facade_heights(egid="2245881", sides=polygon_sides)
# → {"N": FacadeHeight(z_min=541.0, z_max=550.0), "E": ...}
```

---

---

## Aktueller Projektstand (14.01.2026 18:30)

### Implementierte Features

| Feature | Backend | Frontend | Status |
|---------|---------|----------|--------|
| 3D-Layer Import (Roof, Wall) | `roof_3d_service.py` | - | ✅ On-Demand |
| Dach-Orientierung | `service.py` | `ScaffoldScene.tsx` | ✅ |
| Qualitäts-Badge | - | `BuildingDataCard.tsx` | ✅ |
| Fassaden-Höhen (T1-T4) | `service.py`, `project_service.py` | `BuildingDataCard.tsx` | ✅ |

### Service-Layer Verantwortlichkeiten

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WO WELCHE DATEN HERKOMMEN                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Daten-Quelle           Service                     Datei               │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  swissBUILDINGS3D       Building3DService          building_3d_service.py│
│  (Polygon, Höhen)       → buildings_3d Tabelle     → Stufe 1 Lookup     │
│                                                                         │
│  swissBUILDINGS3D       Roof3DService              roof_3d_service.py   │
│  (Roof/Wall Layer)      → building_roofs/walls    → On-Demand Fetch    │
│                                                                         │
│  swissALTI3D            TerrainService             terrain.py           │
│  (Terrain-Höhen)        → API-Call pro Punkt       → Terrain-Sampling  │
│                                                                         │
│  Cache                  SmartBuildingService       service.py           │
│  (building_environment) → building_contexts.db     → TerrainProfile     │
│                                                                         │
│  Projekt-Daten          ProjectService             project_service.py   │
│  (Geodata für UI)       → geruestbau.db + Bundle  → get_project_with_data│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Cache-Refresh Mechanismus (NEU 14.01.2026 20:00)

**Problem:** Alte Cache-Einträge (erstellt vor T2-T4 Implementation) enthalten keine:
- `has_3d_layers` Flag
- `facade_z_min` / `facade_z_max` Dicts
- `facade_heights_source` String

**Lösung:** `_refresh_bundle_from_db()` in `service.py`

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CACHE-REFRESH MECHANISMUS                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  get_bundle_by_egid(egid)                                              │
│       │                                                                 │
│       ├─► smart_building_cache Query (SQLite)                          │
│       │   • Cache-Hit: bundle_json laden                               │
│       │   • Cache-Miss: → None (Caller muss collect_all_data nutzen)   │
│       │                                                                 │
│       └─► _dict_to_bundle(data)                                        │
│           │                                                             │
│           └─► _refresh_bundle_from_db(bundle, egid)  ◄── NEU!          │
│               │                                                         │
│               ├─► Building3DService.get_by_egid(egid)                  │
│               │   • has_3d_layers aus buildings_3d Tabelle             │
│               │   • Immer frisch (nicht gecacht)                       │
│               │                                                         │
│               └─► WallFacadeMatcher.get_facade_heights()               │
│                   • Nur wenn bundle.terrain.facade_z_min leer          │
│                   • Nur wenn bundle.sides vorhanden                    │
│                   • Ergebnis: facade_z_min/z_max pro Richtung          │
│                                                                         │
│  Ergebnis: Bundle mit aktuellen 3D-Daten auch bei altem Cache!         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Implementierte Dateien:**
- `service.py:194-253` - `get_bundle_by_egid()` mit Refresh-Aufruf
- `service.py:205-253` - `_refresh_bundle_from_db()` Methode
- `service.py:353` - `has_3d_layers` in `_dict_to_bundle()` restaurieren

**Wann wird refresht?**

| Feld | Aus Cache | Refresht aus |
|------|-----------|--------------|
| `has_3d_layers` | Immer False bei alten | `buildings_3d.has_3d_layers` |
| `facade_z_min` | Leer `{}` bei alten | WallFacadeMatcher oder Terrain |
| `facade_z_max` | Leer `{}` bei alten | WallFacadeMatcher oder Terrain |
| `facade_heights_source` | "global" bei alten | Aus Matching-Ergebnis |

**Performance:** ~10-20ms zusätzlich pro Request (1x DB-Query + optionales Matching)

### Nächste Schritte (Vorschläge)

| Priorität | Task | Beschreibung |
|-----------|------|--------------|
| ~~P4~~ | ~~Fassaden-Höhen in Gerüst-Kalkulation~~ | ✅ ERLEDIGT 14.01.2026 |
| P5 | Alpha-Shape für komplexe Polygone | Besseres Wall-Matching für U-Form, L-Form |
| P5 | 3D-Terrain im Viewer | Gelände-Mesh statt flache Ebene |
| P5 | Echte Wall-Geometrie rendern | 3D-Wände aus WKB |

---

## 3D-Dach-Rendering für ALLE Gebäude (NEU 14.01.2026)

### Problem

Das Frontend ignorierte echte 3D-Dachgeometrie für komplexe Gebäude mit Spezialzonen
(Kuppel, Turm, Treppenhaus). Die Prüfung `shouldRenderRoof` war `false` für solche
Gebäude, wodurch der gesamte Dach-Rendering-Block übersprungen wurde.

### Lösung: Echte Geometrie IMMER priorisieren

```typescript
// ScaffoldScene.tsx - FIX 14.01.2026 13:35

// NEU: Prüfe echte 3D-Geometrie UNABHÄNGIG von Komplexität
const hasReal3DGeometry = config.roof?.has_roof_geometry &&
                           config.roof?.roof_geometry_coords?.length > 0 &&
                           config.roof?.roof_dach_min_m;

if (hasReal3DGeometry) {
  // IMMER echte Geometrie verwenden wenn verfügbar
  parent.add(createRoofFrom3DGeometry(...));
} else {
  // Fallback: Heuristisches Dach NUR für einfache Gebäude ohne echte Daten
  const shouldRenderHeuristicRoof = !hasSpecialZones || buildingComplexity === 'simple';
  if (shouldRenderHeuristicRoof) {
    parent.add(createRoofFromPolygon(...));
  }
}
```

**Betroffene Datei:**
- `geruestbau-app/src/features/.../ScaffoldScene.tsx:1105-1145`

**Ergebnis:**
- Bundeshaus: 12 Polygone Dachgeometrie werden jetzt korrekt gerendert
- Alle komplexen Gebäude: Echte 3D-Dächer sichtbar

---

---

## NEU: facades[] Array (18.01.2026)

### Übersicht

Das `facades[]` Array kombiniert Fassaden-Geometrie mit Höhen- und Giebel-Informationen.
Es wird im `SmartBuildingService._build_facades_array()` aufgebaut und im API-Response mitgeliefert.

### Datenstruktur

```typescript
interface Facade {
  index: number;              // Fassaden-Index (0-basiert)
  direction: string;          // Himmelsrichtung: "N", "E", "S", "W", "NW", etc.
  start_point: [number, number];  // LV95 Koordinaten
  end_point: [number, number];    // LV95 Koordinaten
  length_m: number;           // Fassadenlänge in Metern

  // FIX 18.01.2026: Höhe ist KONSTANT (Traufhöhe)
  height_m: number;           // KONSTANTE Gerüsthöhe = Traufhöhe

  // NEU 18.01.2026: Giebel-Erkennung
  is_gable: boolean;          // True für Giebel-Fassaden (brauchen mehr Gerüst bis First)

  // Terrain-Daten (nur für Stellspindeln/Nivelierung)
  terrain_z_min: number;      // Terrain-Höhe (m ü.M.) an dieser Fassade
  slope_m: number;            // Terrain-Gefälle in Metern
}
```

### Giebel-Erkennung

Die Giebel-Fassaden werden aus der `roof_orientation` ermittelt:

```
roof_orientation beschreibt wohin das Dach ZEIGT (Neigungsrichtung).
Der First verläuft SENKRECHT zur Neigung.
Giebel sind an den ENDEN des Firsts (senkrecht zur Neigung).

| roof_orientation | Dach neigt nach | First verläuft | Giebel auf |
|------------------|-----------------|----------------|------------|
| O-W (E-W)        | Ost ↔ West      | Nord-Süd       | N, S       |
| N-S              | Nord ↔ Süd      | Ost-West       | E, W (O)   |
| NO-SW            | Diagonal        | Senkrecht      | NW, SO     |
| NW-SO            | Diagonal        | Senkrecht      | NO, SW     |
```

### Datenfluss

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FACADES[] DATENFLUSS                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. SmartBuildingService.collect_all_data()                                      │
│     └─ _build_facades_array(bundle)                                              │
│                                                                                  │
│  2. Für jede Side aus bundle.sides:                                              │
│     ├─ direction, start_point, end_point, length_m übernehmen                   │
│     ├─ height_m = bundle.traufhoehe_m (KONSTANT!)                               │
│     ├─ is_gable = direction in _get_gable_directions(roof_orientation)          │
│     └─ terrain_z_min, slope_m aus TerrainProfile                                │
│                                                                                  │
│  3. bundle.facades = facades[] Array                                             │
│                                                                                  │
│  4. API Response (main.py)                                                       │
│     └─ "facades": bundle.facades                                                 │
│                                                                                  │
│  5. SSE Stream (building_data_stream.py)                                         │
│     └─ event: complete → facades[] enthalten                                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Verwendung im Frontend

```typescript
// Gerüsthöhe für Fassadenarbeit
const scaffoldHeight = facade.height_m;  // Konstante Traufhöhe

// Giebel-Fassaden brauchen zusätzliches Gerüst
if (facade.is_gable) {
  console.log(`Fassade ${facade.direction}: Giebel-Seite - Gerüst bis First nötig`);
}

// Terrain-Daten für Stellspindel-Berechnung
const levelingHeight = facade.terrain_z_min;
const slopeCompensation = facade.slope_m;
```

### Warum height_m KONSTANT sein muss

**Problem (vor dem Fix):**
```
height_m = wall_z_max - terrain_z_min
→ Bei Hanglagen: Fassaden hatten unterschiedliche Höhen
→ Gerüst wurde zu hoch berechnet
```

**Lösung:**
```
height_m = bundle.traufhoehe_m (KONSTANT)
→ Alle Fassaden haben gleiche Gerüsthöhe (bis Traufe)
→ Giebel-Fassaden: is_gable=true → separates Giebel-Gerüst
→ Terrain-Ausgleich: slope_m + terrain_z_min für Stellspindeln
```

### Betroffene Dateien

| Datei | Funktion |
|-------|----------|
| `backend/app/services/smart_building/service.py:1193-1293` | `_build_facades_array()`, `_get_gable_directions()` |
| `backend/app/main.py:4135` | facades im API-Response |
| `backend/app/services/building_data_stream.py` | facades im SSE-Stream |

---

## NEU: WorkType 'Spengler' (27.01.2026)

### Übersicht

Der WorkType `'full'` (Komplett) wurde durch `'roofer'` (Spengler) ersetzt.

### Work-Types

| Type | Label | Beschreibung | Berechnung |
|------|-------|--------------|------------|
| `facade` | Fassade | Bis Traufe | `traufhoehe_m` |
| `roof` | Dacharbeiten | +1m Absturzsicherung | `traufhoehe_m + 1m` |
| `roofer` | Spengler | First -1m für Arbeitsplatz | `firsthoehe_m - 1m` (mit Giebel-Trapez) |

### Giebel-Trapez-Berechnung (NEU)

Bei `'roofer'` WorkType wird für Giebel-Fassaden eine Trapez-Form berechnet:

```typescript
// calculations.ts - calculateTargetHeight()
if (workType === 'roofer' && isGiebel && giebelHeightM) {
  // Giebel-Fassade: Trapez bis First - 1m
  return traufhoeheM + giebelHeightM - 1.0;
}
```

### Neue Felder in ScaffoldFacade

```typescript
interface ScaffoldFacade {
  // ... bestehende Felder ...
  first_height_m?: number;   // Firsthöhe für Spengler-Modus
  is_giebel?: boolean;       // Giebel-Fassade?
  giebel_height_m?: number;  // Höhe des Giebel-Dreiecks
}
```

### Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `scaffold.types.ts` | WorkType, ScaffoldFacade Interface |
| `WorkTypeSelector.tsx` | UI-Labels |
| `calculations.ts` | `calculateTargetHeight()` mit Giebel-Logik |
| `useScaffoldConfig.ts` | `createFacadeElement()`, `setWorkType()` |

---

## BUG-031: 3D-Höhen-Diskrepanz (Gebäude vs. Gerüst) - GEFIXT

> **Status:** ✅ Gefixt am 27.01.2026 11:00
> **Problem (behoben):** Das Gerüst erschien in der 3D-Ansicht kleiner als erwartet,
> weil die Multi-Building-Traufhöhe falsch berechnet wurde.

### Symptome

1. **Fassadenarbeit:** Gerüst sollte exakt bis zur Traufe reichen, ist aber kürzer
2. **Dacharbeit:** Gerüst sollte 1m über die Traufe ragen, erreicht aber gerade die Traufe

### Ursache: Unterschiedliche Terrain-Referenzen

Das Gebäude-Mesh und das Gerüst verwenden **unterschiedliche Terrain-Werte**:

```
┌─────────────────────────────────────────────────────────────────┐
│                 HÖHEN-DISKREPANZ ANALYSE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GEBÄUDE-MESH (ScaffoldScene.tsx):                             │
│  ══════════════════════════════════                             │
│  buildingHeight = roof_dach_min_m - terrain_z_min              │
│                                                                 │
│  Beispiel:                                                      │
│    roof_dach_min_m = 562.94m (Traufe, m ü.M.)                  │
│    terrain_z_min = 555.80m (niedrigstes Terrain)               │
│    → buildingHeight = 7.14m                                     │
│                                                                 │
│  GERÜST (useScaffoldConfig.ts):                                │
│  ═══════════════════════════════                                │
│  facade.height_m = trauf_height_m (aus API)                    │
│  levels = Math.ceil(facade.height_m / levelHeight)             │
│  Gerüsthöhe = levels × levelHeight                             │
│                                                                 │
│  Beispiel:                                                      │
│    facade.height_m = 5.49m (aus API - ANDERER Terrain-Wert!)   │
│    levels = Math.ceil(5.49 / 2.0) = 3                          │
│    → Gerüsthöhe = 6.0m                                          │
│                                                                 │
│  DISKREPANZ: 7.14m (Gebäude) vs. 6.0m (Gerüst) = 1.14m Differenz│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Warum unterschiedliche Terrain-Werte?

| Quelle | Terrain-Berechnung | Verwendet für |
|--------|-------------------|---------------|
| **API** (`geruestbau.py:558-589`) | `min(facade_z_min)` aus swissALTI3D | `trauf_height_m` (Fassaden) |
| **3D-Scene** (`ScaffoldScene.tsx:1346-1348`) | `terrain_z_min` aus SSE/API | `buildingHeight` (Mesh) |

Diese können unterschiedlich sein weil:
1. `facade_z_min` ist das Minimum über alle Fassaden-Eckpunkte
2. `terrain_z_min` kann ein anderer Wert sein (z.B. vom SSE-Stream)

### Lösung (Implementiert 27.01.2026)

Die Multi-Building-Logik in `_calculate_object_data()` verwendet jetzt die korrekte
Traufhöhenberechnung: `roof_dach_min_m - min(terrain_z_min)` statt `bundle.traufhoehe_m`.

```python
# FIX 27.01.2026 (building_data_stream.py:95-115)
if bundle.roof_dach_min_m and bundle.terrain and bundle.terrain.facade_z_min:
    min_terrain = min(bundle.terrain.facade_z_min.values())
    corrected_trauf = bundle.roof_dach_min_m - min_terrain  # Echte 3D-Daten!
```

### Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `building_data_stream.py:95-115` | Korrigierte Traufhöhenberechnung in `_calculate_object_data()` |
| `geruestbau.py:588-601` | Korrigierter Fallback für Multi-Building Response |

### Ergebnis

Gebäude und Gerüst verwenden jetzt **dieselbe Terrain-Referenz** (`min(facade_z_min)`).
Die visuelle Diskrepanz in der 3D-Ansicht ist behoben.

---

## Referenzen

- [`STREAMING_ARCHITECTURE.md`](STREAMING_ARCHITECTURE.md) - SSE-Stream Details
- [`BUILDING_3D_SCHEMA.md`](BUILDING_3D_SCHEMA.md) - DB-Schema Konzept
- [`SWISSBUILDINGS3D_ANALYSE.md`](SWISSBUILDINGS3D_ANALYSE.md) - Layer-Details
- [`3D_LAYER_ANALYSIS.md`](3D_LAYER_ANALYSIS.md) - Detailanalyse, Service-Layer Diagramme
- [`3D_LAYER_USAGE_3D_VIEW.md`](3D_LAYER_USAGE_3D_VIEW.md) - 3D-View Rendering Details
- [`RAILWAY_DEPLOYMENT.md`](RAILWAY_DEPLOYMENT.md) - Railway Volume & Deployment Guide