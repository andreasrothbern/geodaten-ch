# 3D-Layer Datenverwendung

> **Datum:** 14.01.2026 22:00
> **Status:** P1 + P2 + P3 (T1-T4) + P4 ✅ ALLE IMPLEMENTIERT
> **Basis:** BUILDING_3D_SCHEMA.md, SWISSBUILDINGS3D_ANALYSE.md, 3D_LAYER_ANALYSIS.md
> **Siehe auch:** [`3D_LAYER_USAGE_SCAFFOLDING.md`](3D_LAYER_USAGE_SCAFFOLDING.md) - Gerüst-Kalkulation Details

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

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FASSADEN-HÖHEN FALLBACK-KETTE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STUFE 1: Wall-Layer Matching (höchste Präzision)                       │
│  ════════════════════════════════════════════════                        │
│  Bedingung: has_3d_layers=1 UND building_walls Einträge vorhanden       │
│                                                                          │
│     WallFacadeMatcher.get_facade_heights(egid, sides)                   │
│          │                                                               │
│          └─► Für jede Fassade: z_min, z_max aus Wall-Geometrie          │
│              • z_min = Terrain-Höhe (m ü.M.) an dieser Fassade          │
│              • z_max = Wandoberkante (m ü.M.)                           │
│              • Konfidenz: 0.3 - 1.0 (abhängig vom Matching-Score)       │
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

## Referenzen

- [`STREAMING_ARCHITECTURE.md`](STREAMING_ARCHITECTURE.md) - SSE-Stream Details
- [`BUILDING_3D_SCHEMA.md`](BUILDING_3D_SCHEMA.md) - DB-Schema Konzept
- [`SWISSBUILDINGS3D_ANALYSE.md`](SWISSBUILDINGS3D_ANALYSE.md) - Layer-Details
- [`3D_LAYER_ANALYSIS.md`](3D_LAYER_ANALYSIS.md) - Detailanalyse, Service-Layer Diagramme