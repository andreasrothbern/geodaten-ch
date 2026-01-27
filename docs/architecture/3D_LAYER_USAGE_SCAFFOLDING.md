# 3D-Layer Verwendung: Gerüst-Kalkulation

> **Stand 27.01.2026 14:00**
> **Status:** ✅ P1-Bug gefixt (Höhenberechnung)
>            ✅ P2 implementiert (Pro-Fassade Z-Matching)
>            ✅ P3 implementiert (Giebel-Erkennung mit is_giebel Flag)
>            🔄 REFACTORING GEPLANT: Höhenberechnung + Gerüst-Abstand
>
> **FIX 24.01.2026:** Frontend verwendet jetzt API-Traufhöhe statt Geometrie-Berechnung.
> Siehe "Konzept-Trennung" für Details.
>
> **NEU 25.01.2026:** Giebel-Erkennung in `matchFacadeToWall()` implementiert.
> `is_giebel` und `giebel_height_m` werden jetzt pro Fassade berechnet.
>
> **NEU 27.01.2026:** WorkType `'full'` → `'roofer'` (Spengler) mit Giebel-Trapez.
> Siehe "WorkType Spengler" für Details.
>
> **Aktuelle DB-Statistiken (14.01.2026 00:15):**
> | Tabelle | Anzahl | Bemerkung |
> |---------|--------|-----------|
> | buildings_3d | 4,832 | Tile 1322-21 = 4,827 |
> | building_roofs | 30,443 | ~6.3 Dächer/Gebäude |
> | building_walls | 29,927 | ~6.2 Wände/Gebäude |
> | **DB-Größe** | **402 MB** | DuckDB komprimiert |

---

## 🔄 GEPLANTES REFACTORING: 3D-Geometrie-basierte Gerüstplanung (27.01.2026)

### Motivation

Das aktuelle System hat drei Probleme:

1. **Höhenberechnung:** 7+ Stellen im Backend berechnen `traufhoehe_m`/`firsthoehe_m` - aber das sind KEINE Rohdaten!
2. **Gerüst-Abstand:** Fix 0.5m, obwohl der Abstand je nach Work-Type und Dachüberstand variieren sollte
3. **Terrain:** Nur 1 Punkt (`terrain_z_min`) - reicht nicht für Stellspindel-Berechnung bei Gefälle!

### Was sind Rohdaten?

**ECHTE ROHDATEN** = 3D-Geometrie aus swissBUILDINGS3D:
- `building_walls[].geometry` - 3D-Polygone mit `[x, y, z]` Koordinaten
- `building_roofs[].geometry` - 3D-Dach-Polygone mit `[x, y, z]` Koordinaten

**KEINE ROHDATEN** = Bereits aggregierte/berechnete Werte:
- `roof_dach_min_m` ← Minimum aller Dach-Z-Werte (berechnet)
- `terrain_z_min` ← Minimum aller Terrain-Z-Werte (berechnet)
- `traufhoehe_m` ← `dach_min - terrain_z_min` (berechnet)

### Ziel-Architektur: Gerüst folgt exakt der 3D-Geometrie

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 NEUE ARCHITEKTUR: 3D-GEOMETRIE-BASIERT                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BACKEND liefert ECHTE Rohdaten (3D-Geometrie):                            │
│  ═══════════════════════════════════════════════                            │
│  {                                                                          │
│    "building_walls": [{                                                    │
│      "egid": "1234567",                                                    │
│      "geometry_type": "MultiPolygon",                                      │
│      "coords_3d": [[[[x1,y1,z1], [x2,y2,z2], ...]]]  // ← ECHTE 3D-DATEN! │
│    }],                                                                     │
│    "building_roofs": [{                                                    │
│      "geometry_coords": [[[x1,y1,z1], [x2,y2,z2], ...]],                  │
│      "dach_min": 562.94,    // NUR als Referenz                           │
│      "dach_max": 570.08     // NUR als Referenz                           │
│    }],                                                                     │
│    "roof_overhang_m": 0.45  // Aus Sonnendach.ch                          │
│  }                                                                          │
│                                                                             │
│  FRONTEND berechnet aus 3D-Geometrie (SINGLE SOURCE OF TRUTH):             │
│  ═════════════════════════════════════════════════════════════              │
│                                                                             │
│  1. GERÜST-PLATZIERUNG: Exakt entlang der Wall-Polygone                   │
│     ┌─────────────────────────────────────────────────────────────────┐   │
│     │  Wall-Polygon:    [x1,y1,z1] → [x2,y2,z2] → [x3,y3,z3] → ...   │   │
│     │  Gerüst folgt:    ════════════════════════════════════════════  │   │
│     │                   Exakt entlang der Kontur, nicht vereinfacht!  │   │
│     └─────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  2. FASSADEN-HÖHE: Pro Fassade aus Wall-Vertices                          │
│     - z_min = niedrigstes Z der Fassaden-Vertices (Terrain)               │
│     - z_max = höchstes Z der Fassaden-Vertices (Traufe/Giebel)            │
│     - Höhe = z_max - z_min (pro Fassade individuell!)                     │
│                                                                             │
│  3. TERRAIN-PROFIL: Mehrere Punkte pro Fassade für Stellspindeln          │
│     ┌─────────────────────────────────────────────────────────────────┐   │
│     │  Fassade (12m Länge): ══════════════════════════════════════   │   │
│     │  Terrain-Punkte:       z=555.8  z=556.1  z=556.5  z=557.2     │   │
│     │  Differenz zu min:      0.0m     0.3m     0.7m     1.4m       │   │
│     │  Stellspindel:         keine    keine    0.4m     0.8m+0.6m  │   │
│     └─────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  4. GERÜST-ABSTAND: Je nach WorkType + roof_overhang_m                    │
│     facade:  0.30m fix (Putz/Maler)                                       │
│     roof:    roof_overhang_m (am Dachrand vorbei)                         │
│     roofer:  roof_overhang_m - 0.2m (unter dem Dach)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Warum mehrere Terrain-Punkte?

Ein einzelner `terrain_z_min` Wert reicht NICHT für die Ausnivellierung:

```
PROBLEM mit 1 Punkt:
  terrain_z_min = 555.8 (globales Minimum)
  → Wir wissen nur: "irgendwo ist das Terrain auf 555.8m"
  → Wir wissen NICHT: "wo genau?" und "wie verläuft das Gefälle?"

LÖSUNG mit mehreren Punkten (Z-Werte der Wall-Vertices):
  Feld 1: z=555.8m → Stellspindel: 0.0m (Referenz)
  Feld 2: z=556.1m → Stellspindel: 0.3m
  Feld 3: z=556.5m → Stellspindel: 0.7m
  Feld 4: z=557.2m → Stellspindel: 1.4m (Ausgleichsrahmen!)

  → EXAKTE Materialliste pro Feld!
```

Siehe "Ausnivellierung bei Hanglage" unten für Details zur Stellspindel-Berechnung.

### ✅ ANALYSE 27.01.2026: Z-Daten sind bereits vorhanden!

Die benötigten Terrain-Z-Werte sind **bereits in `building_walls[].geometry`** enthalten.
Kein zusätzliches Terrain-Mesh erforderlich!

**Vorhandene Datenstrukturen (Frontend):**

| Interface/Funktion | Datei | Liefert |
|--------------------|-------|---------|
| `BuildingWall.geometry` | `project.ts:114-119` | 3D-Polygone mit `[x, y, z]` Vertices |
| `extractWallRingsWithZ()` | `polygonSimplifier.ts:525-561` | `coords2d` + `coords3d` mit Z-Werten |
| `extractZFromRing()` | `polygonSimplifier.ts:566-579` | `z_min`, `z_max` pro Polygon-Ring |
| `matchFacadeToWall()` | `polygonSimplifier.ts:597-684` | Wall-Match mit `polygon_z_min`, `polygon_z_max` |

**Struktur der Wall-Geometrie:**
```typescript
// BuildingWall.geometry enthält 3D-Koordinaten:
// - Polygon: [[[x,y,z], ...], [[hole], ...]]
// - MultiPolygon: [[[[x,y,z], ...]], [...]]

// Beispiel für ein Wand-Polygon (Rechteck mit 4 Ecken):
// Untere Kante: [x1, y1, 555.8], [x2, y2, 556.3]  ← Terrain-Höhe!
// Obere Kante:  [x1, y1, 562.9], [x2, y2, 562.9]  ← Trauf-Höhe!
```

**Was das bedeutet:**
1. **Terrain-Profil:** Die unteren Vertices jeder Wand = Terrain-Höhe an diesem Punkt
2. **Pro Feld:** Alle Z-Werte entlang einer Fassade → Stellspindel-Material pro Feld
3. **Kein API-Call:** Alles bereits in `building_walls[]` vorhanden

**✅ IMPLEMENTIERT 27.01.2026:**

| Funktion | Zeile | Beschreibung |
|----------|-------|--------------|
| `extractTerrainProfile()` | `polygonSimplifier.ts:529-602` | Extrahiert Terrain-Z-Werte aus Wall-Vertices |
| `calculateLevelingSpindles()` | `polygonSimplifier.ts:604-622` | Berechnet Stellspindel-Höhen pro Position |
| `TerrainProfilePoint` | `polygonSimplifier.ts:521-527` | Interface für Terrain-Profil-Punkte |
| `WallMatchResult.terrain_profile` | `polygonSimplifier.ts:518` | Terrain-Profil im Match-Result |

**Verwendung:**
```typescript
const result = matchFacadeToWall(facadeStart, facadeEnd, buildingWalls);
// result.terrain_profile enthält Z-Werte entlang der Fassade:
// [{position_m: 0, z_terrain: 555.8, z_traufe: 562.9, scaffold_height_m: 7.1}, ...]

const spindles = calculateLevelingSpindles(result.terrain_profile);
// [{position_m: 0, spindle_height_m: 0}, {position_m: 4, spindle_height_m: 0.3}, ...]
```

### Analyse: Backend-Stellen mit Höhenberechnung (zu bereinigen)

| # | Datei | Zeilen | Beschreibung | Aktion |
|---|-------|--------|--------------|--------|
| 1 | `geruestbau.py` | 589-601, 1008-1025 | Berechnet `traufhoehe_m` | → ENTFERNEN (Frontend macht das) |
| 2 | `building_data_stream.py` | 97-117, 627-628 | SSE-Stream mit Fallback | → ENTFERNEN |
| 3 | `smart_building/service.py` | 717-718, 801-802, 890+ | Bundle-Befüllung | → NUR 3D-Geometrie liefern |
| 4 | `roof.py` | 388-403 | Fallback aus GWR (Geschosse×3.2m) | → ENTFERNEN |
| 5 | `tile_prefetch.py` | 1987-1988 | Legacy UPSERT | → Unverändert (Speicherung) |
| 6 | `data_cache.py` | 186-196 | Alter Cache | → Prüfen ob noch verwendet |
| 7 | `main.py` | 1167-1169, 1340-1341 | Legacy-Endpunkte | → Prüfen ob noch verwendet |

### Analyse: Gerüst-Abstand (aktuell fix)

| Stelle | Wert | Beschreibung |
|--------|------|--------------|
| `ScaffoldScene.tsx:781` | `scaffoldGap = 0.5` | Fix 0.5m für 3D-Visualisierung |
| `npk114_calculator.py:35` | `fassadenabstand_m = 0.30` | Fix 0.3m für NPK-Ausmass |

**Ziel:** Dynamisch aus `roof_overhang_m` + WorkType:

```typescript
// ScaffoldScene.tsx (NEU)
const getScaffoldGap = (workType: WorkType, roofOverhang: number): number => {
  switch (workType) {
    case 'facade':
      return 0.30;  // Fix für Putz-/Malerarbeiten
    case 'roof':
      return roofOverhang;  // Am Dachrand vorbei für Absturzsicherung
    case 'roofer':
      return Math.max(0.20, roofOverhang - 0.20);  // Unter dem Dach, min. 20cm
  }
};
```

### Implementierungsplan

| Phase | Task | Aufwand | Beschreibung |
|-------|------|---------|--------------|
| **1. ANALYSE** | ✅ Erledigt | - | Architektur definiert, 3D-Geometrie als Basis |
| **2. FRONTEND** | 3D-Geometrie verwenden | Mittel | Gerüst folgt exakt den Wall-Polygonen |
| **3. FRONTEND** | ✅ Terrain-Profil pro Fassade | Erledigt | `extractTerrainProfile()` + `calculateLevelingSpindles()` |
| **4. FRONTEND** | Dynamischer Abstand | Klein | `ScaffoldScene.tsx`: Abstand je WorkType + `roof_overhang_m` |
| **5. BACKEND** | 3D-Geometrie liefern | Klein | `building_walls` mit vollständiger `coords_3d` |
| **6. CLEANUP** | Legacy entfernen | Mittel | Berechnete Höhenwerte im Backend entfernen |

### Betroffene Dateien

**Frontend (ändern):**
- `ScaffoldScene.tsx` - Gerüst entlang 3D-Geometrie, dynamischer Abstand
- `useScaffoldConfig.ts` - Höhen aus 3D-Vertices berechnen
- `polygonSimplifier.ts` - Terrain-Z-Werte pro Fassaden-Segment

**Backend (vereinfachen):**
- `geruestbau.py` - Nur `building_walls` mit 3D-Koordinaten liefern
- `smart_building/service.py` - Keine berechneten Höhen mehr ins Bundle
- `roof.py` - Fallback entfernen (keine GWR-Schätzung mehr)

### Kein Fallback mehr!

**Begründung:** Wir haben zuverlässige 3D-Daten für alle Gebäude via swissBUILDINGS3D STAC API.
Ein Fallback auf GWR-Schätzung (Geschosse × 3.2m) ist:
- Ungenau (±2-3m)
- Inkonsistent mit 3D-Visualisierung
- Verwirrend für Benutzer

**Wenn keine 3D-Daten:** Fehler anzeigen, nicht raten!

### Datenfluss: 3D-Geometrie → Gerüst

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATENFLUSS: 3D-GEOMETRIE → GERÜST                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. BACKEND: swissBUILDINGS3D Tile laden                                   │
│     └─ building_walls Tabelle: geometry_wkb (3D MultiPolygon)              │
│                                                                             │
│  2. API: /configurator/facades                                             │
│     └─ building_walls[].coords_3d = [[[[x,y,z], [x,y,z], ...]]]           │
│                                                                             │
│  3. FRONTEND: ConfiguratorPage.tsx                                         │
│     └─ buildingWalls an ScaffoldScene übergeben                            │
│                                                                             │
│  4. FRONTEND: ScaffoldScene.tsx                                            │
│     ├─ Pro Fassade: Wall-Vertices matchen (2D-Position)                   │
│     ├─ Z-Werte extrahieren → z_min[], z_max[]                             │
│     ├─ Terrain-Profil: Array von Z-Werten entlang Fassade                 │
│     ├─ Stellspindeln: diff[i] = z[i] - min(z[])                           │
│     └─ Gerüst: Exakt entlang der 3D-Kontur platzieren                     │
│                                                                             │
│  5. MATERIALLISTE: layher_catalog.py                                       │
│     └─ Terrain-Profil → Stellspindel-Typen pro Feld berechnen             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## WorkType Spengler (NEU 27.01.2026)

### Änderung

Der WorkType `'full'` (Komplett) wurde durch `'roofer'` (Spengler) ersetzt:

| Type | Label | Berechnung | Gerüst-Position |
|------|-------|------------|-----------------|
| `facade` | Fassade | `traufhoehe_m` | 0.3m von Fassade |
| `roof` | Dacharbeiten | `traufhoehe_m + 1m` | Am Dachrand |
| `roofer` | **Spengler** | `firsthoehe_m - 1m` | Unter dem Dach |

### Giebel-Trapez für Spengler

Bei Giebel-Fassaden (z.B. Ost/West bei O-W-Dach) wird das Gerüst als **Trapez** berechnet:

```
TRAUF-FASSADE (N/S):           GIEBEL-FASSADE (E/W):
┌────────────────┐             ┌────────────────┐
│                │                    /\
│   RECHTECK     │                   /  \
│   bis First-1m │                  /    \
│                │                 / TRAPEZ\
│                │                /  bis    \
└────────────────┘               /  First-1m \
                               ────────────────
                               Traufe + Giebel - 1m
```

**Berechnung:**
- **Trauf-Fassade:** `target_height = firsthoehe_m - 1.0`
- **Giebel-Fassade:** `target_height = traufhoehe_m + giebel_height_m - 1.0`

### Betroffene Dateien

- `scaffold.types.ts` - WorkType, ScaffoldFacade.is_giebel, ScaffoldFacade.giebel_height_m
- `WorkTypeSelector.tsx` - UI "Spengler" statt "Komplett"
- `calculations.ts` - `calculateTargetHeight()` mit Giebel-Logik
- `useScaffoldConfig.ts` - `setWorkType()` mit Giebel-Parametern
- `ScaffoldGrid.tsx`, `ScaffoldScene.tsx` - `'full'` → `'roofer'`

---

## Übersicht

Dieses Dokument beschreibt, wie die 3D-Layer-Daten (swissBUILDINGS3D) in der Gerüst-Kalkulation verwendet werden.

## ⚠️ WICHTIG: Konzept-Trennung (NEU 24.01.2026)

Die `facade_z_min` / `facade_z_max` Werte werden für **ZWEI VERSCHIEDENE ZWECKE** verwendet:

| Konzept | Zweck | Höhenberechnung | Datei |
|---------|-------|-----------------|-------|
| **3D-Visualisierung** | Gerüst-Darstellung | `height = traufhoehe_m` (KONSTANT) | `ConfiguratorPage.tsx` |
| **NPK 114 Ausmass** | Abrechnung/Fläche | `height = z_max - z_min` (PRO FASSADE) | `npk114_calculator.py` |
| **Stellspindeln** | Material-Berechnung | `diff = max(z_min) - min(z_min)` | `layher_catalog.py` |

### Warum KONSTANTE Höhe für 3D-Visualisierung?

**NPK 114 Grundprinzip:** Das Gerüst hat überall die **gleiche physische Höhe** (= Traufhöhe).
Terrain-Differenzen werden durch **Stellspindeln am Boden** ausgeglichen, NICHT durch höheres Gerüst!

```
KORREKT (NPK 114):                    FALSCH (alter Bug):
  ┌──────────────────┐                   ┌──────────────────┐
  │                  │                   │                  │
  │  GERÜST (5.5m)   │                   │  GERÜST (11.2m!) │
  │                  │                   │                  │
  └──────────────────┘                   │                  │
   ╱────────────────╲                    │                  │
   TERRAIN (schräg)                      │                  │
   + Stellspindeln                       └──────────────────┘
                                         Giebel + Terrain inkludiert!
```

### Was der Bug war (ConfiguratorPage.tsx)

```typescript
// BUG (vor 24.01.2026):
facadeHeight = zMax - zMin;  // Bei Giebel: First-Spitze - tiefstes Terrain = 11.23m!

// FIX (nach 24.01.2026):
facadeHeight = traufHeight;  // API-Wert = 5.49m (konstant für alle Fassaden)
```

**Kernkonzept für Hanglage:** Die 3D-Layer-Daten liefern präzise Terrain-Höhen pro Fassade für **Stellspindel-Berechnung** und **NPK 114 Ausmass** - aber NICHT für die 3D-Gerüst-Visualisierung.

## Datenfluss: 3D-Daten → Gerüst-Kalkulation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATENFLUSS GERÜST-KALKULATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │ swissBUILDINGS3D │    │ Wall-Layer       │    │ Terrain-Sampling │      │
│  │ (STAC API)       │───▶│ (building_walls) │ OR │ (swissALTI3D)    │      │
│  └──────────────────┘    └────────┬─────────┘    └────────┬─────────┘      │
│                                   │                       │                 │
│                                   ▼                       ▼                 │
│                          ┌──────────────────────────────────────┐          │
│                          │ facade_z_min / facade_z_max          │          │
│                          │ (Dict pro Himmelsrichtung)           │          │
│                          │                                      │          │
│                          │ Beispiel Hanglage:                   │          │
│                          │   N: z_min=543.0, z_max=555.0        │          │
│                          │   S: z_min=540.0, z_max=555.0        │          │
│                          └──────────────────┬───────────────────┘          │
│                                             │                              │
│      ┌──────────────────────────────────────┼──────────────────────────┐   │
│      │                                      │                          │   │
│      ▼                                      ▼                          ▼   │
│  ┌────────────────────┐   ┌────────────────────────┐   ┌──────────────────┐│
│  │ 3D-VISUALISIERUNG  │   │ NPK114 AUSMASS         │   │ STELLSPINDELN    ││
│  │ (ScaffoldScene.tsx)│   │ (npk114_calculator.py) │   │ (layher_catalog) ││
│  ├────────────────────┤   ├────────────────────────┤   ├──────────────────┤│
│  │                    │   │                        │   │                  ││
│  │ height = traufhöhe │   │ height = z_max - z_min │   │ diff = max(z_min)││
│  │ (KONSTANT!)        │   │ (PRO FASSADE!)         │   │      - min(z_min)││
│  │                    │   │                        │   │                  ││
│  │ → Gerüst-Rechteck  │   │ → Abrechnungsfläche    │   │ → Ausgleichs-    ││
│  │   gleiche Höhe     │   │   pro Fassade          │   │   material       ││
│  └────────────────────┘   └────────────────────────┘   └──────────────────┘│
│                                                                             │
│  ✅ FIX 24.01.2026: 3D-Visualisierung verwendet jetzt traufhoehe_m aus API │
│                     NICHT mehr z_max - z_min (enthielt Giebel-Spitze!)     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Komponenten-Übersicht

### Frontend (geruestbau-app)

| Datei | Funktion |
|-------|----------|
| `src/types/project.ts` | `Geodata` Interface mit `facade_z_min`, `facade_z_max` |
| `src/features/scaffold-configurator/utils/polygonSimplifier.ts` | `sidesToFacades()` - konvertiert Polygon-Seiten zu Fassaden |
| `src/features/scaffold-configurator/components/FacadePanel.tsx` | Aufrufer von `sidesToFacades()` |
| `src/features/scaffold-configurator/hooks/useScaffoldConfig.ts` | Zustand-Store für Gerüst-Konfiguration |
| `src/features/scaffold-configurator/types/scaffold.types.ts` | `SelectedFacade`, `ScaffoldFacade` Types |

### Backend (Python)

| Datei | Funktion |
|-------|----------|
| `app/services/smart_building/service.py` | Sammelt 3D-Daten, berechnet Fassaden-Höhen |
| `app/services/smart_building/wall_facade_matcher.py` | Ordnet Wall-Layer Daten zu Himmelsrichtungen |
| `app/services/npk114_calculator.py` | NPK 114 Ausmass-Berechnung |

## Fassaden-Höhen Quellen

### 1. Wall-Layer (Beste Qualität)

Wenn der swissBUILDINGS3D Wall-Layer verfügbar ist (`has_3d_layers = true`):

```
Wall-Feature Attribute:
  - GELAENDEPUNKT (z_min): Terrain-Höhe am Wandfuss
  - GESAMTHOEHE: Höhe der Wand
  → z_max = GELAENDEPUNKT + GESAMTHOEHE
```

**Matching:** `wall_facade_matcher.py` ordnet Wall-Features zu Fassaden-Richtungen basierend auf Azimut.

### 2. Terrain-Sampling (Fallback)

Wenn kein Wall-Layer verfügbar ist, werden die Polygon-Ecken mit swissALTI3D abgetastet:

```python
# service.py: _sample_facade_heights_from_terrain()
for side in bundle.sides:
    start_height = terrain_service.get_height(side.start)
    end_height = terrain_service.get_height(side.end)
    z_min[direction] = min(start_height, end_height)
    z_max[direction] = traufhoehe_m + min_terrain  # Relative zur tiefsten Ecke
```

### 3. Global (Legacy-Fallback)

Ohne 3D-Daten wird eine globale Traufhöhe für alle Fassaden verwendet:

```
traufhoehe_m (aus swissBUILDINGS3D Building_solid oder GWR-Schätzung)
```

## Hanglage-Beispiel

**Knospenweg, Bern** (Hanglage nach Süden):

```
Terrain-Höhen:
  Nordseite:  543.0 m ü.M.
  Südseite:   540.0 m ü.M.
  → Gefälle: 3.0 m

Traufhöhe absolut: 555.0 m ü.M.

Gerüsthöhen pro Fassade:
  Nord: 555.0 - 543.0 = 12.0 m Gerüst
  Süd:  555.0 - 540.0 = 15.0 m Gerüst (3m höher!)

NPK 114 Ausmass:
  Nord: LA × (12.0 + 1.0) = LA × 13.0 m
  Süd:  LA × (15.0 + 1.0) = LA × 16.0 m

→ 23% mehr Gerüstfläche an der Südseite!
```

## UI-Anzeige

### BuildingDataCard

Zeigt Fassaden-Höhen in einer Tabelle pro Himmelsrichtung:

```
┌─────────────────────────────────────────┐
│ Fassaden-Höhen (aus 3D-Layer)           │
├──────┬──────────┬──────────┬────────────┤
│ Dir  │ z_min    │ z_max    │ Höhe       │
├──────┼──────────┼──────────┼────────────┤
│  N   │ 543.0 m  │ 555.0 m  │ 12.0 m     │
│  NE  │ 542.5 m  │ 555.0 m  │ 12.5 m     │
│  E   │ 541.0 m  │ 555.0 m  │ 14.0 m     │
│  S   │ 540.0 m  │ 555.0 m  │ 15.0 m ⚠️  │
│  ...                                     │
└──────────────────────────────────────────┘
```

⚠️ = Höchste Gerüsthöhe (Hanglage-Indikator)

### FacadeCards (geplant)

Jede Fassade zeigt ihre spezifische Höhe:

```
┌───────────────────────────┐
│ Fassade Nord              │
│ Länge: 12.5 m             │
│ Höhe: 12.0 m              │
│ (Terrain: 543.0 m ü.M.)   │ ← Neu: Terrain-Info
└───────────────────────────┘
```

## NPK 114 Kalkulation

### Aktuelle Formel (global)

```python
# npk114_calculator.py
LA = length_m + 2 * LS  # LS = 1.0m (stirnseitiger Abschluss)
HA = traufhoehe_m + HOEHENZUSCHLAG  # Zuschlag = 1.0m
Fläche = LA * HA
```

### Geplante Formel (pro Fassade)

```python
def calculate_facade_ausmass(self, side, facade_z_min, facade_z_max, global_traufhoehe):
    # Höhe bestimmen
    if facade_z_min is not None and facade_z_max is not None:
        height_m = facade_z_max - facade_z_min
    else:
        height_m = global_traufhoehe  # Fallback

    # NPK 114 Formel
    LA = side['length_m'] + 2 * self.LS
    HA = height_m + self.HOEHENZUSCHLAG

    return FassadenAusmass(
        direction=side['direction'],
        length_m=side['length_m'],
        height_m=height_m,
        la=LA,
        ha=HA,
        area_m2=LA * HA
    )
```

## Datenbank-Felder

### buildings_3d (DuckDB)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `has_3d_layers` | INT | 1 wenn Wall/Roof-Layer vorhanden |
| `traufhoehe_m` | DOUBLE | Globale Traufhöhe (Fallback) |
| `firsthoehe_m` | DOUBLE | Globale Firsthöhe |

### building_walls (SQLite)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `egid` | TEXT | Gebäude-ID |
| `z_min` | REAL | Terrain-Höhe (m ü.M.) |
| `z_max` | REAL | Wandoberkante (m ü.M.) |
| `azimuth_deg` | REAL | Ausrichtung der Wand |
| `direction` | TEXT | Himmelsrichtung (N, NE, E, ...) |

### smart_building_cache (SQLite)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `facade_z_min` | JSON | `{"N": 543.0, "E": 541.0, ...}` |
| `facade_z_max` | JSON | `{"N": 555.0, "E": 555.0, ...}` |
| `facade_heights_source` | TEXT | "wall_layer" / "terrain_sampled" / "global" |

---

## Plan: Fassaden-Höhen in Gerüst-Kalkulation

**Stand 24.01.2026 18:30 - ⚠️ KONZEPT KORRIGIERT**

### Ursprüngliches Problem (falsch verstanden)

~~Bei Gebäuden am Hang haben verschiedene Fassaden unterschiedliche Höhen:~~
~~- Nordseite: Terrain auf 543m → Traufe auf 555m → **12m Gerüst**~~
~~- Südseite: Terrain auf 540m → Traufe auf 555m → **15m Gerüst**~~

### Korrektes Verständnis (NPK 114)

**Das Gerüst hat ÜBERALL die gleiche physische Höhe** (= Traufhöhe von der Gebäudewand).
Terrain-Differenzen werden durch **Stellspindeln** ausgeglichen, NICHT durch höheres Gerüst!

```
BEISPIEL HANGLAGE:

  Nordseite (höheres Terrain):    Südseite (tieferes Terrain):
  ┌────────────────┐              ┌────────────────┐
  │                │              │                │
  │  GERÜST 5.5m   │              │  GERÜST 5.5m   │  ← GLEICHE HÖHE!
  │                │              │                │
  └────────────────┘              └────────────────┘
  ═════════════════              │ Stellspindel   │
  Terrain                        └────────────────┘
                                 ════════════════════
                                 Terrain (3m tiefer)

→ Gerüst-HÖHE ist identisch (5.5m)
→ STELLSPINDELN sind 3m länger auf Südseite
→ NPK 114 AUSMASS berücksichtigt den Höhenunterschied (Fläche)
```

### Datenfluss (KORRIGIERT 24.01.2026)

```
3D-VISUALISIERUNG (ScaffoldScene):
  Geodata.traufhoehe_m = 5.5m (KONSTANT für alle Fassaden!)
       ↓
  ScaffoldFacade.target_height_m = 5.5m
       ↓
  Gerüst wird mit einheitlicher Höhe gerendert
  + Stellspindel-Visualisierung basierend auf terrain_diff_m

NPK 114 AUSMASS (Backend):
  Geodata.facade_z_min["N"] = 543.0    Geodata.facade_z_max["N"] = 555.0
  Geodata.facade_z_min["S"] = 540.0    Geodata.facade_z_max["S"] = 555.0
       ↓
  Ausmass["N"].height_m = 555.0 - 543.0 = 12.0m
  Ausmass["S"].height_m = 555.0 - 540.0 = 15.0m
       ↓
  Abrechnung berücksichtigt Terrain-Differenz (23% mehr Fläche!)
```

### Implementierung

#### Schritt 1: TypeScript Types erweitern

**Datei:** `geruestbau-app/src/types/project.ts`

```typescript
interface FacadeConfig {
  // ... bestehende Felder ...

  // NEU: Fassaden-spezifische Höhen aus 3D-Daten
  facade_z_min?: number      // Terrain-Höhe an dieser Fassade (m ü.M.)
  facade_z_max?: number      // Wandoberkante an dieser Fassade (m ü.M.)
  facade_height_m?: number   // Berechnet: z_max - z_min
  height_source?: 'wall_layer' | 'terrain_sampled' | 'global'
}
```

#### Schritt 2: `sidesToFacades()` anpassen (KERN-ÄNDERUNG)

**Datei:** `geruestbau-app/src/features/scaffold-configurator/utils/polygonSimplifier.ts`

Zeilen 320-345 - `sidesToFacades()` Funktion:

```typescript
// AKTUELL (Zeile 336-344):
return sides.map((side, idx) => ({
  id: `facade-${idx + 1}`,
  direction: side.direction as FacadeDirection,
  length_m: side.length_m,
  height_m: defaultHeight,  // ← GLEICHE HÖHE FÜR ALLE!
  slope_percent: 0,
  start_point: [side.start.x, side.start.y],
  end_point: [side.end.x, side.end.y],
}));

// NEU:
export function sidesToFacades(
  sides: Side[],
  defaultHeight: number,
  facadeZMin?: Record<string, number>,  // NEU
  facadeZMax?: Record<string, number>   // NEU
): SelectedFacade[] {
  return sides.map((side, idx) => {
    // Fassaden-spezifische Höhe wenn verfügbar
    let height = defaultHeight;
    if (facadeZMin?.[side.direction] && facadeZMax?.[side.direction]) {
      height = facadeZMax[side.direction] - facadeZMin[side.direction];
    }

    return {
      id: `facade-${idx + 1}`,
      direction: side.direction as FacadeDirection,
      length_m: side.length_m,
      height_m: height,  // ← JETZT PRO FASSADE!
      slope_percent: 0,
      start_point: [side.start.x, side.start.y],
      end_point: [side.end.x, side.end.y],
    };
  });
}
```

#### Schritt 3: FacadeCards Anzeige erweitern

**Datei:** `geruestbau-app/src/features/scaffold-configurator/components/overview/FacadeCards.tsx`

Zusätzliche Info wenn Fassaden-Höhe von global abweicht:

```typescript
{facade.height_source !== 'global' && (
  <span className="text-xs text-blue-500">
    (Terrain: {facade.facade_z_min?.toFixed(1)}m)
  </span>
)}
```

#### Schritt 4: NPK114 Backend Berechnung anpassen

**Datei:** `backend/app/services/npk114_calculator.py`

Die `calculate()` Methode erhält bereits `sides` mit Längen. Erweitern um Höhen:

```python
def calculate_facade_ausmass(
    self,
    side: Dict,
    facade_z_min: Optional[float],
    facade_z_max: Optional[float],
    global_traufhoehe: float
) -> FassadenAusmass:
    # Höhe bestimmen
    if facade_z_min is not None and facade_z_max is not None:
        height_m = facade_z_max - facade_z_min
    else:
        height_m = global_traufhoehe

    # NPK114 Formel
    la = side['length_m'] + 2 * self.LS  # Länge + beidseitiger Abschluss
    ha = height_m + self.HOEHENZUSCHLAG   # Höhe + Zuschlag

    return FassadenAusmass(
        fassade_index=side['index'],
        direction=side['direction'],
        length_m=side['length_m'],
        height_m=height_m,
        la=la,
        ha=ha,
        area_m2=la * ha
    )
```

### Kritische Dateien

| Datei | Änderung |
|-------|----------|
| `geruestbau-app/src/types/project.ts` | FacadeConfig erweitern |
| `geruestbau-app/src/features/scaffold-configurator/utils/polygonSimplifier.ts` | sidesToFacades() erweitern |
| `geruestbau-app/src/features/scaffold-configurator/components/FacadePanel.tsx` | facade heights übergeben |
| `geruestbau-app/src/features/scaffold-configurator/hooks/useScaffoldConfig.ts` | getFacadeHeight() Funktion |
| `geruestbau-app/src/features/scaffold-configurator/components/overview/FacadeCards.tsx` | Terrain-Höhe anzeigen |
| `backend/app/services/npk114_calculator.py` | Pro-Fassade Berechnung |

### Testfall

**Knospenweg, Bern** (Hanglage):
- Erwartung: Unterschiedliche Gerüsthöhen pro Fassade
- Validierung: Höhen in FacadeCards sollten variieren

---

## Implementation Status (14.01.2026)

### ✅ Implementierte Dateien

| Datei | Änderung | Status |
|-------|----------|--------|
| `scaffold.types.ts` | `SelectedFacade` mit `facade_z_min`, `facade_z_max`, `height_source` | ✅ |
| `polygonSimplifier.ts` | `sidesToFacades()` mit Fassaden-Höhen-Berechnung | ✅ |
| `FacadePanel.tsx` | Props `facadeZMin`, `facadeZMax` hinzugefügt | ✅ |
| `ScaffoldConfigurator.tsx` | Props Durchreichung an FacadePanel | ✅ |
| `ConfiguratorPage.tsx` | `geodata.facade_z_min`/`facade_z_max` zu Props | ✅ |

### Noch offen

| Task | Priorität | Beschreibung |
|------|-----------|--------------|
| Test mit echtem Hanglage-Gebäude | P2 | Gebäude mit >3m Gefälle testen |
| NPK114 Backend-Anpassung | P3 | Pro-Fassade Berechnung (aktuell Frontend-only) |
| FacadeCards Terrain-Anzeige | P4 | Terrain-Höhe in UI darstellen |

### Test-Ergebnisse (14.01.2026)

**API-Test erfolgreich** - Datenfluss funktioniert:

| Gebäude | Gefälle | Fassaden | facade_heights_source |
|---------|---------|----------|----------------------|
| Knospenweg 2, Bern | 1.0m | 4 (N,E,S,W) | terrain_sampled |
| Aargauerstalden 10, Bern | 0.5m | 5 (N,E,S,W,NW) | terrain_sampled |

**Beispiel Knospenweg 2:**
```
Fassaden-Höhen (z_min / z_max -> Höhe):
  N: 557.0 / 562.53 -> 5.5m
  E: 557.4 / 562.93 -> 5.5m
  S: 557.5 / 563.03 -> 5.5m
  W: 557.6 / 563.13 -> 5.5m
```

→ Terrain-Höhen variieren pro Richtung (N=557.0m bis W=557.6m)
→ Bei Gebäuden mit mehr Gefälle werden Fassaden-Höhen stärker variieren

---

## Hanglage-Behandlung (NEU 14.01.2026 23:30)

### z_max Berechnung (BUG FIX)

**Problem gefunden:** Die z_max Berechnung war falsch!

```python
# FALSCH (vorher):
z_max[direction] = terrain_height + bundle.traufhoehe_m  # Pro Fassade unterschiedlich!

# RICHTIG (jetzt):
absolute_dach_hoehe = reference_height + bundle.traufhoehe_m  # Einmal berechnen
z_max[direction] = absolute_dach_hoehe  # KONSTANT für alle Fassaden!
```

**Warum?** Bei Gebäuden mit horizontalem Dach ist die Dachkanten-Höhe (z_max)
für ALLE Fassaden GLEICH. Nur das Terrain (z_min) variiert pro Fassade!

```
                    ← z_max KONSTANT (555.0m ü.M.) →
                    ┌─────────────────────────────────┐
                    │                                 │
                    │         DACH (horizontal)       │
    Fassade N       │                                 │       Fassade S
    Höhe: 12.0m     │                                 │       Höhe: 15.0m
                    │                                 │
    ─────┬──────────┴─────────────────────────────────┴──────────┬─────
         │                      TERRAIN                          │
   543.0 m ü.M. ─────────────────────────────────────── 540.0 m ü.M.
   z_min["N"]                                           z_min["S"]
```

**Fix in:** `backend/app/services/smart_building/service.py:850-870`

### Anzeige mit 2 Dezimalstellen

Die Fassaden-Höhen werden jetzt mit 2 Dezimalstellen angezeigt für präzise Messungen:

```typescript
// BuildingDataCard.tsx
{height !== null ? `${height.toFixed(2)}m` : '–'}
```

### Hanglage-Erkennung im Frontend

Die `BuildingDataCard` erkennt automatisch Hanglage und zeigt einen Hinweis:

```typescript
// Hanglage-Erkennung: Terrain-Differenz > 0.5m
const zMinValues = heights.map(h => h.zMin).filter(v => v !== undefined)
const terrainDiff = Math.max(...zMinValues) - Math.min(...zMinValues)
const hasSlope = terrainDiff > 0.5

// Höchste Fassade markieren bei Hanglage
const isMax = hasSlope && height === maxHeight
```

**UI-Anzeige:**
- ⚠️ Hanglage erkannt
- Terrain-Differenz: X.XXm | Höhen-Differenz: X.XXm
- → Gerüst am Grund ausnivellieren erforderlich

---

## Ausnivellierung bei Hanglage (GEPLANT)

### Konzept

Bei Gebäuden am Hang muss das Gerüst am Grund ausgeglichen werden:

```
                    ┌──────────────────────┐
                    │   GERÜST-AUFBAU      │
                    │   (alle Lagen)       │
                    │                      │
                    │                      │
   ┌────────────────┼──────────────────────┤
   │ Stellspindel   │                      │ Stellspindel
   │ 0.4m           │                      │ 0.0m
   └────────────────┴──────────────────────┘
         │                                       │
   ──────┴───────────────────────────────────────┴──────
              SCHRÄGER BODEN (Terrain)
```

### Layher Blitz Ausnivellierungs-Material

| Höhe Ausgleich | Material | Art.-Nr. | Gewicht |
|----------------|----------|----------|---------|
| 0 - 0.40m | Stellspindel 0.4m | 0730.020 | 4.2 kg |
| 0.40 - 0.80m | Ausgleichsrahmen 0.5m | 0731.050 | 8.5 kg |
| 0.80 - 1.30m | Ausgleichsrahmen 1.0m | 0731.100 | 14.0 kg |
| > 1.30m | Zusätzliche Startlagen | - | variabel |

### Berechnung Ausgleichsmaterial

```typescript
function calculateLevelingMaterial(terrainDiff: number): LevelingMaterial[] {
  const materials: LevelingMaterial[] = []
  const numFields = facade.fields  // Anzahl Felder pro Fassade

  // An der tiefsten Seite: voller Ausgleich nötig
  // An der höchsten Seite: kein Ausgleich
  // Dazwischen: linear interpoliert

  for (let field = 0; field < numFields; field++) {
    const fieldOffset = (terrainDiff / numFields) * field

    if (fieldOffset > 0.4) {
      materials.push({ type: 'Ausgleichsrahmen', height: 0.5 })
    } else if (fieldOffset > 0) {
      materials.push({ type: 'Stellspindel', extension: fieldOffset })
    }
  }

  return materials
}
```

### Einfluss auf Materialliste

Bei Hanglage werden zusätzlich benötigt:

| Material | Menge | Berechnung |
|----------|-------|------------|
| Stellspindeln verlängert | 2 × Ständer | Auf Hangseite |
| Ausgleichsrahmen | n × Felder | Bei >0.4m Differenz |
| Fussplatten breit | 2 × Ständer | Für Stabilität |

### Einfluss auf Gewicht

```
Standard-Gerüst: 20 kg/m²

Mit Ausnivellierung:
  + Stellspindeln: +0.5 kg/m²
  + Ausgleichsrahmen: +1-2 kg/m²

→ Gesamt bei Hanglage: 21-23 kg/m²
```

### Editor-Visualisierung (✅ IMPLEMENTIERT 15.01.2026)

**Datei:** `ScaffoldGrid.tsx`

**Implementierte Funktionen:**

1. **`renderGround()`** - Zeichnet schräge Bodenlinie bei Hanglage
   - Bodenlinie steigt von links nach rechts basierend auf `terrain_diff_m`
   - Braune Farbe (#8B4513) bei Hanglage statt Standard-Grau
   - Terrain-Schraffur als Polygon
   - Terrain-Differenz-Anzeige (⚠ X.XXm)

2. **`renderLevelingSpindles()`** - Zeichnet Stellspindeln/Ausgleichsrahmen
   - Lineare Interpolation: links = max Verlängerung, rechts = keine
   - Farbkodierung nach Verlängerung:
     - Grau (#666666): Stellspindel bis 0.4m
     - Orange (#f97316): Lange Stellspindel 0.4-0.8m
     - Rot (#dc2626): Ausgleichsrahmen >0.8m
   - Fussplatten-Anzeige
   - Höhenangabe am ersten Feld

**Datenfluss:**

```
Geodata.facade_z_min (pro Richtung)
    │
    ├─ createElementsFromFacades() berechnet:
    │   globalTerrainDiff = max(z_min) - min(z_min)
    │
    └─ ScaffoldFacade enthält:
           terrain_z_min, terrain_z_max, terrain_diff_m
               │
               └─ ScaffoldGrid rendert:
                    renderGround() + renderLevelingSpindles()
```

### Datenfluss für Hanglage

```
Geodata.facade_z_min (pro Richtung)
    │
    ├─ terrain_diff = max(z_min) - min(z_min)
    │
    ├─ is_sloped = terrain_diff > 0.5m
    │
    └─ ScaffoldFacade.terrain_diff_m
           │
           ├─ Editor: renderSlopedGround()
           │
           └─ MaterialList: calculateLevelingMaterial()
```

---

## Materialliste Integration (Stand 13.01.2026 23:40) ✅ IMPLEMENTIERT

### Vollständiger Datenfluss: Frontend → Backend → MaterialList

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DATENFLUSS: MATERIALLISTE MIT STELLSPINDELN                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    1. GEODATA (SmartBuildingService)                     │  │
│  ├──────────────────────────────────────────────────────────────────────────┤  │
│  │  BuildingDataBundle:                                                     │  │
│  │    facade_z_min: {"N": 543.0, "S": 540.0, ...}   ← swissALTI3D          │  │
│  │    facade_z_max: {"N": 555.0, "S": 555.0, ...}   ← swissBUILDINGS3D     │  │
│  │    terrain.slope_m: 3.0                          ← max(z_min)-min(z_min) │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    2. FRONTEND (geruestbau-app)                          │  │
│  ├──────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                          │  │
│  │  ConfiguratorPage.tsx                                                    │  │
│  │       │                                                                  │  │
│  │       └─ geodata.facade_z_min, geodata.facade_z_max                      │  │
│  │              │                                                           │  │
│  │              ▼                                                           │  │
│  │  useScaffoldConfig.ts: createElementsFromFacades()                       │  │
│  │       │                                                                  │  │
│  │       ├─ globalTerrainDiff = max(z_min) - min(z_min)                     │  │
│  │       │                                                                  │  │
│  │       └─ ScaffoldFacade.terrain_diff_m = globalTerrainDiff               │  │
│  │              │                                                           │  │
│  │              ├──────────────────────┬──────────────────┐                 │  │
│  │              ▼                      ▼                  ▼                 │  │
│  │      ScaffoldGrid.tsx       ThreeDPanel.tsx     MaterialListModal        │  │
│  │      ├─ renderGround()      ├─ 3D-Ansicht       ├─ 📦 Button             │  │
│  │      └─ renderLeveling      └─ Zusammenfassung  └─ → API-Call            │  │
│  │         Spindles()                                                       │  │
│  │         ✅ IMPLEMENTIERT    ✅ IMPLEMENTIERT     ✅ IMPLEMENTIERT        │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│                                      │ API-Call mit terrain_diff_m, field_count │
│                                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    3. BACKEND (FastAPI)                                  │  │
│  ├──────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                          │  │
│  │  GET /api/v1/catalog/estimate                                            │  │
│  │       │                                                                  │  │
│  │       ├─ system_id: "blitz70"                    ✅ vorhanden            │  │
│  │       ├─ area_m2: 460                            ✅ vorhanden            │  │
│  │       ├─ short_field_ratio: 0.33                 ✅ vorhanden            │  │
│  │       ├─ terrain_diff_m: 3.0                     ✅ IMPLEMENTIERT        │  │
│  │       └─ field_count: 8                          ✅ IMPLEMENTIERT        │  │
│  │              │                                                           │  │
│  │              ▼                                                           │  │
│  │  layher_catalog.py: estimate_material_quantities()                       │  │
│  │       │                                                                  │  │
│  │       ├─ Standard-Material berechnen             ✅ funktioniert         │  │
│  │       │                                                                  │  │
│  │       └─ if terrain_diff_m > 0.1:                                        │  │
│  │              │                                                           │  │
│  │              └─ calculate_leveling_materials()   ✅ IMPLEMENTIERT        │  │
│  │                    │                                                     │  │
│  │                    ├─ Fussspindel 0.40m (0-0.4m)                         │  │
│  │                    ├─ Fussspindel 0.60m (0.4-0.6m)                       │  │
│  │                    ├─ Fussspindel 0.80m (0.6-0.8m)                       │  │
│  │                    ├─ Ausgleichsrahmen 1.00m (0.8-1.0m)                  │  │
│  │                    ├─ Ausgleichsrahmen 1.50m (1.0-1.5m)                  │  │
│  │                    └─ Ausgleichsrahmen 2.00m (1.5-2.0m)                  │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Implementierungsstatus ✅ KOMPLETT

| Komponente | Datei | Status |
|------------|-------|--------|
| Terrain-Daten sammeln | `service.py` | ✅ Implementiert |
| Fassaden-Höhen pro Richtung | `scaffold.types.ts` | ✅ Implementiert |
| globalTerrainDiff berechnen | `useScaffoldConfig.ts:201-207` | ✅ Implementiert |
| terrain_diff_m in ScaffoldFacade | `useScaffoldConfig.ts:175` | ✅ Implementiert |
| Schräge Bodenlinie zeichnen | `ScaffoldGrid.tsx:renderGround()` | ✅ Implementiert |
| Stellspindeln visualisieren | `ScaffoldGrid.tsx:renderLevelingSpindles()` | ✅ Implementiert |
| calculate_leveling_materials() | `layher_catalog.py:164-244` | ✅ Implementiert |
| Integration in estimate_material | `layher_catalog.py:338-356` | ✅ Implementiert |
| API-Endpunkt mit terrain_diff_m | `main.py:1589-1650` | ✅ Implementiert |
| API-Funktion estimateMaterials | `geruestbau.ts` | ✅ Implementiert |
| Frontend MaterialList Button | `ThreeDPanel.tsx:310-327` | ✅ Implementiert |
| MaterialListModal | `ThreeDPanel.tsx:329-463` | ✅ Implementiert |

### API-Test (13.01.2026 23:40)

```bash
curl "http://localhost:8000/api/v1/catalog/estimate?system_id=blitz70&area_m2=200&terrain_diff_m=1.5&field_count=8"
```

**Ergebnis:**
```json
{
  "summary": {
    "total_pieces": 312,
    "total_weight_kg": 3535.0,
    "has_leveling": true,
    "leveling_pieces": 8,
    "leveling_weight_kg": 72.0
  },
  "materials": [
    // ... Standard-Material ...
    {"category": "Ausnivellierung (Hanglage)", "name": "Fussspindel 0.40m", "quantity_typical": 2},
    {"category": "Ausnivellierung (Hanglage)", "name": "Fussspindel 0.60m", "quantity_typical": 1},
    {"category": "Ausnivellierung (Hanglage)", "name": "Fussspindel 0.80m", "quantity_typical": 1},
    {"category": "Ausnivellierung (Hanglage)", "name": "Ausgleichsrahmen 1.00m", "quantity_typical": 1},
    {"category": "Ausnivellierung (Hanglage)", "name": "Ausgleichsrahmen 1.50m", "quantity_typical": 3}
  ]
}
```

### Berechnung der Stellspindeln (layher_catalog.py)

```
Beispiel: Hanglage 2.5m, 6 Felder entlang der Fassade

Feld 0 (links/oben):    0.0m Ausgleich → keine Verlängerung
Feld 1:                 0.5m Ausgleich → Fussspindel 0.60m
Feld 2:                 1.0m Ausgleich → Ausgleichsrahmen 1.00m
Feld 3:                 1.5m Ausgleich → Ausgleichsrahmen 1.50m
Feld 4:                 2.0m Ausgleich → Ausgleichsrahmen 2.00m
Feld 5 (rechts/unten):  2.5m Ausgleich → Ausgleichsrahmen 2.00m + Stellspindel

Ergebnis:
  - 1× Fussspindel 0.60m
  - 1× Ausgleichsrahmen 1.00m
  - 1× Ausgleichsrahmen 1.50m
  - 2× Ausgleichsrahmen 2.00m
```

### Implementierte Dateien

| Datei | Änderung | Status |
|-------|----------|--------|
| `backend/app/main.py:1589-1650` | API mit `terrain_diff_m`, `field_count` | ✅ |
| `backend/app/services/layher_catalog.py` | `calculate_leveling_materials()` | ✅ |
| `geruestbau-app/src/api/geruestbau.ts` | `estimateMaterials()` API-Funktion | ✅ |
| `geruestbau-app/src/features/scaffold-configurator/components/ThreeDPanel.tsx` | Button + Modal inline | ✅ |

---

## Parquet-Pipeline (C.1-C.4) ✅ IMPLEMENTIERT (14.01.2026)

### Übersicht

Die Parquet-Pipeline ersetzt das sequentielle GDB-Parsing durch eine effiziente
Streaming-Architektur mit paralleler Parquet-Konvertierung und DuckDB Bulk-Load.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PARQUET-PIPELINE ARCHITEKTUR                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────────┐  │
│  │ GDB-Datei    │    │ Parquet-Writer   │    │ DuckDB                   │  │
│  │ (swissB3D)   │───▶│ (Parallel I/O)   │───▶│ (Bulk COPY)              │  │
│  └──────────────┘    └──────────────────┘    └──────────────────────────┘  │
│        │                    │                         │                     │
│        │                    │                         │                     │
│        ▼                    ▼                         ▼                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ C.1: Feature-Generatoren        C.2: ParquetWriter                  │  │
│  │ C.3: Parallele Schreiber        C.4: Bulk-Load Integration          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Performance-Vergleich

| Methode | Zeit (7197 Gebäude) | pro Gebäude | Speedup |
|---------|---------------------|-------------|---------|
| **Baseline** (INSERT) | 147.2s | 20.5ms | 1.0× |
| **Parquet-Pipeline** | 51.2s | 7.1ms | **2.88×** |

### Komponenten

#### C.1: Feature-Generatoren (`tile_prefetch.py`)

Streaming-Generatoren für Buildings, Roofs, Walls:

```python
def _generate_building_features(gdb_path: str) -> Iterator[Dict]:
    """Generiert Building-Features ohne Speicherallokation."""
    with fiona.open(gdb_path, layer="Building_solid") as src:
        for feature in src:
            yield _parse_building_feature(feature)

def _generate_roof_features(gdb_path: str) -> Iterator[Dict]:
    """Generiert Roof-Features (Roof + Roof_solid kombiniert)."""
    ...

def _generate_wall_features(gdb_path: str) -> Iterator[Dict]:
    """Generiert Wall-Features mit z_min/z_max."""
    ...
```

#### C.2: ParquetWriter (`parquet_writer.py`)

Buffered Writer mit PyArrow für effiziente Parquet-Erstellung:

```python
class ParquetWriter:
    """Schreibt Features gepuffert in Parquet-Dateien."""

    def __init__(self, output_path: str, schema: pa.Schema, buffer_size: int = 1000):
        self.buffer: List[Dict] = []
        self.buffer_size = buffer_size

    def write(self, feature: Dict) -> None:
        """Puffert Feature, schreibt bei Überlauf."""
        self.buffer.append(feature)
        if len(self.buffer) >= self.buffer_size:
            self._flush()

    def _flush(self) -> None:
        """Schreibt Buffer als Parquet Row-Group."""
        table = pa.Table.from_pylist(self.buffer, schema=self.schema)
        pq.write_to_dataset(table, self.output_path, ...)
```

#### C.3: Parallele Schreiber

ThreadPoolExecutor für paralleles Schreiben von Buildings/Roofs/Walls:

```python
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(write_buildings_parquet, gdb_path, buildings_path),
        executor.submit(write_roofs_parquet, gdb_path, roofs_path),
        executor.submit(write_walls_parquet, gdb_path, walls_path),
    ]
    for future in as_completed(futures):
        future.result()  # Propagiert Exceptions
```

#### C.4: DuckDB Bulk-Load

COPY-Befehl für direkten Parquet-Import:

```python
def bulk_load_from_parquet(parquet_dir: str, tile_id: str) -> Dict[str, int]:
    """Lädt alle Parquet-Dateien in DuckDB."""
    conn = get_building_3d_connection()

    # Buildings
    conn.execute(f"""
        INSERT INTO buildings_3d
        SELECT * FROM read_parquet('{parquet_dir}/buildings/*.parquet')
    """)

    # Roofs (mit tile_id ergänzt)
    conn.execute(f"""
        INSERT INTO building_roofs
        SELECT *, '{tile_id}' as tile_id
        FROM read_parquet('{parquet_dir}/roofs/*.parquet')
    """)

    # Walls
    conn.execute(f"""
        INSERT INTO building_walls
        SELECT *, '{tile_id}' as tile_id
        FROM read_parquet('{parquet_dir}/walls/*.parquet')
    """)

    return {"buildings": ..., "roofs": ..., "walls": ...}
```

### Dateien

| Datei | Funktion |
|-------|----------|
| `tile_prefetch.py` | Feature-Generatoren, Pipeline-Orchestrierung |
| `parquet_writer.py` | ParquetWriter-Klasse mit Buffering |
| `building_3d_service.py` | `bulk_load_from_parquet()` Integration |
| `building_3d_schema.py` | DuckDB/SQLite Schema-Definitionen |

### Konfiguration

```python
# tile_prefetch.py
PARQUET_BUFFER_SIZE = 1000    # Features pro Flush
MAX_PARALLEL_WRITERS = 3      # Buildings, Roofs, Walls parallel
```

### Test-Ergebnisse (14.01.2026 00:15)

```
Tile: 1322-21 (Bern Zentrum)
════════════════════════════
GDB-Parsing:     12.3s
Parquet-Write:   18.7s (parallel)
DuckDB-Load:     20.2s

Gesamt:          51.2s (vs. 147.2s Baseline)
Speedup:         2.88×

Ergebnis:
  buildings_3d:    4,827 Gebäude
  building_roofs: 30,443 Dächer (~6.3/Gebäude)
  building_walls: 29,927 Wände (~6.2/Gebäude)
  DB-Größe:       402 MB (DuckDB komprimiert)
```

### Nächste Schritte

| Task | Status | Beschreibung |
|------|--------|--------------|
| C.5: Parallel Download | ⏳ Pending | Mehrere Tiles gleichzeitig |
| C.6: Progress-Tracking | ⏳ Pending | Fortschrittsanzeige für User |
| C.7: Cleanup-Integration | ⏳ Pending | Temp-Dateien aufräumen |
| Multi-Tile-Test | ⏳ Pending | Stadt Bern (~20 Tiles) |

---

---

## Partielle Fassaden-Blockierung (NEU 23.01.2026)

### Problem

Bei Gebäuden mit teilweise blockierenden Nachbarn (z.B. Garage, Waschraum) wurde die **gesamte Fassade** als blockiert markiert, obwohl nur ein Teil tatsächlich blockiert war.

```
FASSADE:    |==============================|
GARAGE:                    |████████|

ALT:        |█████████████████████████████| (ganze Fassade grau)
                          ❌ FALSCH

NEU:        |=============|████████|=======|
             auswählbar    blockiert  auswählbar
                          ✅ RICHTIG
```

### Lösung: Segment-basierte Blockierung

Das Backend berechnet für jede Fassade **Segmente** mit ihrem Blockierungs-Status:

```python
# Backend: blocked_facades_service.py

@dataclass
class BlockedSegment:
    start_ratio: float  # 0.0-1.0 Position auf Fassade
    end_ratio: float    # 0.0-1.0 Position auf Fassade
    blocker_egid: str
    min_distance_m: float
```

### Datenfluss

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARTIELLE BLOCKIERUNG                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Backend: blocked_facades_service.py                        │
│     └─ _calculate_blocked_segments(facade, neighbor_polygon)   │
│         ├─ Sampelt Fassade alle 50cm                           │
│         ├─ Prüft Distanz zu Nachbar-Polygon                    │
│         └─ Gibt BlockedSegment[] zurück                        │
│                                                                 │
│  2. SSE: project_context_stream.py                             │
│     └─ blocked_facades Event enthält:                          │
│         {                                                       │
│           "blockers": [{                                       │
│             "facade_index": 2,                                 │
│             "fully_blocked": false,                            │
│             "blocked_segments": [                              │
│               { "start_ratio": 0.4, "end_ratio": 0.7, ... }   │
│             ]                                                  │
│           }]                                                   │
│         }                                                       │
│                                                                 │
│  3. Frontend: FacadePanel.tsx                                  │
│     ├─ allBlockedSegmentsByFacadeIndex (Map)                   │
│     ├─ getFacadeSegments(index) → FacadeSegment[]              │
│     ├─ isFacadeFullyBlocked(index) → boolean (>= 90%)          │
│     └─ SVG-Darstellung mit Segment-Aufteilung                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### UI-Darstellung

| Segment | Farbe | Interaktion |
|---------|-------|-------------|
| Freies Segment | Nach Himmelsrichtung | Klickbar |
| Blockiertes Segment | Grau (#e5e7eb) | Nicht klickbar |

| Fassaden-Status | Darstellung | Info-Text |
|-----------------|-------------|-----------|
| Frei | Grüner Rand | `{length} m` |
| Partiell blockiert | Gelber Rand | `{freeLength} m frei (X% blockiert)` |
| Vollständig blockiert (≥90%) | Grau, deaktiviert | - |

### Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `blocked_facades_service.py` | Segment-Berechnung |
| `project_context_stream.py` | SSE mit `blocked_segments` |
| `geruestbau.ts` | Interface `BlockedSegment` |
| `useProjectContextStream.ts` | Interface `BlockedSegment` |
| `FacadePanel.tsx` | Segment-basierte Visualisierung |

---

---

## Fassaden-exakte Gerüstberechnung (NEU 24.01.2026)

> **Status:** 🔴 ANALYSE - Bug erkannt, Konzept definiert
>
> **Problem:** Frontend berechnet Höhe aus Wall-Geometrie (falsch), statt API-Werte zu nutzen.
> **Ziel:** Gerüst exakt pro Fassade aus 3D-Geometrie berechnen, inkl. Giebel-Optimierung.

### Problem: Falsche Höhenberechnung im Frontend

**Symptom:** Frontend zeigt 11.23m Traufhöhe, API liefert 5.49m.

**Ursache in `ConfiguratorPage.tsx:308-310`:**

```typescript
// FALSCH - enthält Giebel-Spitze UND Terrain-Gefälle!
if (isFinite(geometryWallMinZ) && isFinite(geometryWallMaxZ)) {
  traufHeight = geometryWallMaxZ - geometryWallMinZ;
  // 565.71 (First) - 554.48 (tiefstes Terrain) = 11.23m
}
```

**Das Problem im Detail:**

```
WALL-GEOMETRIE Z-WERTE (Knospenweg 4-6):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                  /\  ← geometryWallMaxZ = 565.71m (First-Spitze)
                 /  \
                /    \     ← GIEBEL (gehört nicht zur Traufhöhe!)
               /      \
==============+========+== ← dach_min = 562.96m (ECHTE Traufe)
|              Gebäude   |
|                        |
|                        |
+========================+ ← wall z_min = 557.47m (Terrain-Attribut)
                         |
                         | ← Terrain fällt ab (Hanglage)
                         |
+========================+ ← geometryWallMinZ = 554.48m (tiefstes Vertex)

BERECHNUNGEN:
  Frontend (FALSCH): 565.71 - 554.48 = 11.23m
  API (RICHTIG):     562.96 - 557.47 = 5.49m
```

### Konzept: Fassaden-exakte Gerüstberechnung

#### Datenquellen-Zuverlässigkeit

| Datenquelle | Zuverlässigkeit | Verwendung |
|-------------|-----------------|------------|
| `dach_min` (building_roofs) | ✅ **Sehr zuverlässig** | Trauf-Niveau absolut |
| `dach_max` (building_roofs) | ✅ **Sehr zuverlässig** | First-Niveau absolut |
| `wall.z_min` (Attribut) | ⚠️ **Mäßig zuverlässig** | Terrain-Referenz (Gebäudemitte) |
| `wall geometry.z[]` | ✅ **Präzise pro Punkt** | Exakte Höhen pro Fassade |
| `terrain_z_min` (global) | ❌ **Unzuverlässig** | Nur Indiz für Hanglage |
| `traufhoehe_m` (API) | ✅ **Zuverlässig** | Berechnete Traufhöhe |

#### Ziel-Architektur: Fassaden-individuelle Höhen

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEUE ARCHITEKTUR: PRO-FASSADE HÖHEN                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DATENQUELLE: Wall-Geometrie (3D-Koordinaten)                              │
│  ─────────────────────────────────────────────                              │
│                                                                             │
│  1. Wall-Geometrie enthält alle Vertices mit [x, y, z]                     │
│  2. Pro Fassade: Vertices matchen basierend auf 2D-Position                │
│  3. Z-Werte pro Fassade:                                                   │
│     - facade_z_min = niedrigstes Z der gematchten Vertices                 │
│     - facade_z_max = OHNE Giebel-Spitze (median oder Trauf-Niveau)         │
│                                                                             │
│  BERECHNUNG PRO FASSADE:                                                   │
│  ─────────────────────────                                                  │
│  Trauf-Fassade (N, S):  height = dach_min - facade_z_min                   │
│  Giebel-Fassade (E, W): height = dach_min - facade_z_min (bis Traufe)      │
│                         + Giebel-Zone (optional, bis dach_max)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Giebel-Einrüstung (Trapez-Form)

**Praxis-Anforderung:** Das Gerüst "verjüngt" sich am Giebel - Material sparen!

```
GIEBEL-FASSADE (Ost oder West bei O-W-Dach):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                    ╱╲
                   ╱  ╲  ← Giebel-Spitze (First)
                  ╱    ╲
                 ╱      ╲
                ╱ GIEBEL ╲         ← Gerüst NUR hier bis First
               ╱  ZONE    ╲            (1-2 Felder breit, Mitte)
              ╱            ╲
             ╱              ╲
════════════╱════════════════╲════════════ ← Traufe (dach_min)
            ╲                ╱
             ╲   STANDARD   ╱
              ╲  GERÜST    ╱    ← Gerüst bis Traufe
               ╲          ╱        (links und rechts vom Giebel)
════════════════╲════════╱════════════════ ← Terrain

GERÜST-FORM (Trapez/Stufenpyramide):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

           ┌──┐           ← Oberste Lage: 1-2 Felder (Giebel-Spitze)
          ┌┴──┴┐          ← 2. Lage: 3-4 Felder
         ┌┴────┴┐         ← 3. Lage: 5-6 Felder
        ┌┴──────┴┐        ← Standard-Breite ab Trauf-Niveau
        │        │
        │        │
════════╧════════╧════════ ← Terrain

MATERIAL-ERSPARNIS:
  Standard (Rechteck):  10m breit × 8m hoch = 80 m² Gerüst
  Trapez (Giebel):      ~60 m² (ca. 25% weniger Material)
```

### Implementierungskonzept

#### 1. Höhenberechnung korrigieren (P1)

**Datei:** `ConfiguratorPage.tsx:308-355`

```typescript
// KORREKTUR: API-Werte priorisieren statt Geometrie-Berechnung
const apiTraufHeight = projectBuildings[0]?.traufhoehe_m;
const apiFirstHeight = projectBuildings[0]?.firsthoehe_m;

if (apiTraufHeight && apiTraufHeight > 0) {
  traufHeight = apiTraufHeight;  // ← API-Wert verwenden!
  console.log(`[convertGeodataResponse] Traufhöhe aus API: ${traufHeight.toFixed(2)}m`);
} else if (isFinite(geometryWallMinZ) && isFinite(geometryWallMaxZ)) {
  // Fallback NUR wenn keine API-Werte
  // Aber: dach_min statt geometryWallMaxZ verwenden!
  const roofDachMin = allRoofs[0]?.dach_min;
  if (roofDachMin && isFinite(roofDachMin)) {
    traufHeight = roofDachMin - geometryWallMinZ;
  }
}
```

#### 2. Fassaden-exakte Z-Werte aus Geometrie (P2)

**Neuer Algorithmus in `polygonSimplifier.ts`:**

```typescript
export function matchFacadeToWallGeometry(
  facade: { start_point: [number, number], end_point: [number, number] },
  wallGeometry: number[][][] | number[][][][],  // Polygon oder MultiPolygon
  dachMin: number  // Trauf-Niveau aus building_roofs
): { z_min: number; z_max: number; is_giebel: boolean } {

  // 1. Alle Vertices aus Wall-Geometrie extrahieren
  const vertices: {x: number, y: number, z: number}[] = extractVertices(wallGeometry);

  // 2. Vertices filtern die zur Fassade gehören (Distanz < 1m zur Fassaden-Linie)
  const facadeVertices = vertices.filter(v =>
    distanceToLine(v, facade.start_point, facade.end_point) < 1.0
  );

  // 3. Z-Werte analysieren
  const zValues = facadeVertices.map(v => v.z).sort((a, b) => a - b);
  const z_min = Math.min(...zValues);  // Terrain

  // 4. Giebel-Erkennung: Hat diese Fassade Punkte über dach_min?
  const pointsAboveDachMin = zValues.filter(z => z > dachMin + 0.5);
  const is_giebel = pointsAboveDachMin.length > 0;

  // 5. z_max bestimmen
  // - Trauf-Fassade: z_max = dach_min (keine Punkte darüber)
  // - Giebel-Fassade: z_max = max(zValues) (First-Spitze)
  const z_max = is_giebel ? Math.max(...zValues) : dachMin;

  return { z_min, z_max, is_giebel };
}
```

#### 3. Giebel-Zone als separate Konfiguration (P3) ✅ IMPLEMENTIERT

**NEU 25.01.2026:** Implementiert in `polygonSimplifier.ts` und `ConfiguratorPage.tsx`.

**Erweitertes Interface in `WallMatchResult`:**

```typescript
export interface WallMatchResult {
  wall: BuildingWall;
  polygon_z_min: number;
  polygon_z_max: number;
  wall_height: number;
  // NEU 24.01.2026 P3: Giebel-Erkennung
  is_giebel: boolean;           // true wenn Punkte über dach_min + 0.5m liegen
  giebel_height_m?: number;     // Höhe des Giebel-Dreiecks (z_max - dach_min)
}
```

**Erweitertes Interface in `SelectedFacade`:**

```typescript
interface SelectedFacade {
  // ... bestehende Felder ...

  // NEU 24.01.2026 P3: Giebel-Erkennung für NPK 114 Ausmass
  is_giebel?: boolean;        // true wenn Wandpunkte über dach_min liegen
  giebel_height_m?: number;   // Höhe des Giebel-Dreiecks (z_max - dach_min)
}
```

**UI-Konfiguration:**

```
┌─────────────────────────────────────────────────────┐
│ Fassade Ost (Giebel-Fassade)                        │
├─────────────────────────────────────────────────────┤
│ Länge: 12.5m                                        │
│ Höhe bis Traufe: 5.49m                              │
│ Giebel-Höhe: 2.75m                                  │
│                                                     │
│ ☑ Giebel einrüsten (Trapez-Form)                   │
│   Breite Giebel-Zone: [2] Felder                   │
│                                                     │
│ Geschätzte Fläche: 68.2 m² (vs. 89.4 m² Rechteck)  │
│ Material-Ersparnis: ~24%                            │
└─────────────────────────────────────────────────────┘
```

### Hanglage-Material (Stellspindeln)

**Wichtig:** `terrain_z_min` (global) ist **unzuverlässig**!

**Zuverlässige Alternative:** Pro-Fassade z_min aus Wall-Geometrie:

```typescript
// Pro Fassade die Terrain-Differenz berechnen
const facadeTechnet wurdee
rrainDiff = facades.map(f => ({
  Dies direction: f.direction,
  z_min: f.z_min,
  diff_to_lowest: f.z_min - Math.min(...facades.map(f => f.z_min))
}));

// Material basierend auf lokaler Differenz, nicht globalem Wert
if (facadeTerrainDiff.diff_to_lowest > 1.5) {
  // Ausgleichsrahmen nötig
}
```

### Data-Flow E2E (Korrigiert)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KORRIGIERTER DATA-FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. BACKEND: building_roofs + building_walls                               │
│     ├─ dach_min = 562.96 (Trauf-Niveau absolut, m ü.M.) ← ZUVERLÄSSIG     │
│     ├─ dach_max = 565.71 (First-Niveau absolut, m ü.M.) ← ZUVERLÄSSIG     │
│     └─ wall.geometry = [[[x,y,z], ...]]  ← PRO-VERTEX Z-WERTE             │
│                                                                             │
│  2. BACKEND: /geodata API                                                  │
│     ├─ traufhoehe_m = dach_min - wall.z_min = 5.49m ← API-BERECHNUNG      │
│     ├─ firsthoehe_m = dach_max - wall.z_min = 8.24m                       │
│     └─ walls[].geometry = volle 3D-Geometrie                              │
│                                                                             │
│  3. FRONTEND: convertGeodataResponse                                       │
│     └─ traufHeight = apiTraufHeight (5.49m)  ← NICHT aus Geometrie!       │
│                                                                             │
│  4. FRONTEND: polygonSimplifier.ts                                         │
│     └─ matchFacadeToWallGeometry() für jede Fassade:                      │
│         ├─ Trauf-Fassade: height = dach_min - facade_z_min                │
│         └─ Giebel-Fassade: height + giebel_zone                           │
│                                                                             │
│  5. FRONTEND: ScaffoldScene (3D)                                           │
│     ├─ Trauf-Fassade: Rechteck-Gerüst                                     │
│     └─ Giebel-Fassade: Trapez-Gerüst (wenn aktiviert)                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Next Steps

| Priorität | Task | Beschreibung |
|-----------|------|--------------|
| **P1** | Höhenberechnung-Bug fixen | `ConfiguratorPage.tsx`: API-Wert statt Geometrie |
| **P2** | Pro-Fassade Z-Matching | `polygonSimplifier.ts`: Geometrie → Fassade matchen |
| **P3** | Giebel-Erkennung | Fassaden mit `is_giebel` Flag markieren |
| **P4** | Trapez-Gerüst UI | Option für Giebel-Einrüstung im Konfigurator |
| **P5** | 3D-Visualisierung | Trapez-Form in ScaffoldScene rendern |

### Test-Gebäude
Noch ei
| Adresse | Typ | Erwartung |
|---------|-----|-----------|
| Knospenweg 4-6, Bern | Reihenhaus mit O-W Dach | E/W = Giebel, N/S = Trauf |
| Bundeshaus, Bern | Komplex | Keine Giebel (Walmdach) |
| Kirche St. Peter, Bern | Sakralbau | Giebel an Ost-Fassade |

---

## Bekanntes Problem: blocked_facades Index-Mismatch

### Problem

Der SSE-Stream liefert `blocked_facades` mit Indizes basierend auf dem **Original-Polygon** (z.B. 31 Punkte = 30 Segmente). Nach der Douglas-Peucker Vereinfachung hat das Frontend nur noch 5-8 Fassaden.

```
ORIGINAL-POLYGON: 30 Segmente (Index 0-29)
  blocked_indices: [0, 1, 2, 9, 10, 11]  ← Backend berechnet auf Original

VEREINFACHT:      8 Fassaden (Index 0-7)
  → Index 9, 10, 11 existieren nicht mehr!
  → Falsche Fassaden werden als blockiert markiert
```

### Aktuelle Situation

- Backend (`blocked_facades_service.py`) berechnet auf Union-Polygon
- Frontend vereinfacht das Polygon (Douglas-Peucker, epsilon variable)
- **Keine Zuordnung** zwischen Original-Index und vereinfachtem Index

### Mögliche Lösungen

| Lösung | Beschreibung | Aufwand |
|--------|--------------|---------|
| **A: Direction-basiert** | Blockierung per Himmelsrichtung statt Index | Mittel |
| **B: Backend vereinfacht** | Backend sendet bereits vereinfachte Indizes | Hoch |
| **C: Index-Mapping** | Frontend mappt Original→Vereinfacht bei Vereinfachung | Mittel |

**Empfehlung:** Lösung A (Direction-basiert) ist am robustesten, da Himmelsrichtungen stabil bleiben auch bei Vereinfachung.

```typescript
// Statt: blocked_indices: [0, 1, 2, 9, 10, 11]
// Besser: blocked_directions: ["N", "NE", "E"]

// Frontend kann dann:
facades.filter(f => !blockedDirections.includes(f.direction))
```

### Betroffene Dateien

| Datei | Änderung nötig |
|-------|----------------|
| `blocked_facades_service.py` | Direction statt Index liefern |
| `project_context_stream.py` | SSE-Format anpassen |
| `useProjectContextStream.ts` | Interface anpassen |
| `FacadePanel.tsx` | Direction-basierte Filterung |

---

## Changelog

| Version | Datum | Änderungen |
|---------|-------|------------|
| 8.0 | 24.01.2026 | Fassaden-exakte Gerüstberechnung, Giebel-Trapez, Bug-Analyse |
| 7.0 | 23.01.2026 | Partielle Fassaden-Blockierung (Segment-basiert) |
| 6.9 | 14.01.2026 00:20 | Parquet-Pipeline (C.1-C.4) dokumentiert, DB-Statistiken aktualisiert |
| 6.8 | 13.01.2026 23:45 | Materialliste mit Stellspindeln KOMPLETT |
| 6.7 | 13.01.2026 22:00 | Editor-Visualisierung implementiert |
| 6.6 | 14.01.2026 00:00 | Hanglage z_max Fix |
| 6.5 | 14.01.2026 22:30 | Implementation Status aktualisiert |
