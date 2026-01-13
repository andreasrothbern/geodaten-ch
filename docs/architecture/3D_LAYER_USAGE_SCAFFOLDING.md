# 3D-Layer Verwendung: Gerüst-Kalkulation

> **Stand 14.01.2026 00:20**
> **Status:** ✅ KOMPLETT IMPLEMENTIERT (inkl. Materialliste mit Stellspindeln)
>
> **Aktuelle DB-Statistiken (14.01.2026 00:15):**
> | Tabelle | Anzahl | Bemerkung |
> |---------|--------|-----------|
> | buildings_3d | 4,832 | Tile 1322-21 = 4,827 |
> | building_roofs | 30,443 | ~6.3 Dächer/Gebäude |
> | building_walls | 29,927 | ~6.2 Wände/Gebäude |
> | **DB-Größe** | **402 MB** | DuckDB komprimiert |

## Übersicht

Dieses Dokument beschreibt, wie die 3D-Layer-Daten (swissBUILDINGS3D) in der Gerüst-Kalkulation verwendet werden.

**Kernkonzept:** Bei Gebäuden am Hang haben verschiedene Fassaden unterschiedliche Höhen. Die 3D-Layer-Daten liefern präzise Fassaden-Höhen für jede Himmelsrichtung.

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
│                          │   N: z_min=543.0, z_max=555.0 → 12m  │          │
│                          │   S: z_min=540.0, z_max=555.0 → 15m  │          │
│                          └──────────────────┬───────────────────┘          │
│                                             │                              │
│                                             ▼                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      BuildingDataBundle                              │  │
│  │                      (SmartBuildingService)                          │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │  terrain:                                                            │  │
│  │    facade_z_min: { "N": 543.0, "NE": 542.5, "E": 541.0, ... }       │  │
│  │    facade_z_max: { "N": 555.0, "NE": 555.0, "E": 555.0, ... }       │  │
│  │    facade_heights_source: "wall_layer" | "terrain_sampled"          │  │
│  └──────────────────────────────────────────┬───────────────────────────┘  │
│                                             │                              │
│              ┌──────────────────────────────┴───────────────┐              │
│              │                                              │              │
│              ▼                                              ▼              │
│  ┌─────────────────────────┐              ┌─────────────────────────────┐  │
│  │ Frontend: Geodata       │              │ Backend: NPK114 Kalkulation │  │
│  │ (geruestbau-app)        │              │ (npk114_calculator.py)      │  │
│  ├─────────────────────────┤              ├─────────────────────────────┤  │
│  │ Geodata Interface:      │              │ Ausmass pro Fassade:        │  │
│  │   facade_z_min          │              │   height_m = z_max - z_min  │  │
│  │   facade_z_max          │              │   LA = length + 2×LS        │  │
│  │   facade_heights_source │              │   HA = height + Zuschlag    │  │
│  └───────────┬─────────────┘              │   Fläche = LA × HA          │  │
│              │                            └─────────────────────────────┘  │
│              ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         sidesToFacades()                            │   │
│  │                     (polygonSimplifier.ts)                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  IST:                                                               │   │
│  │    height_m = defaultHeight  ← GLEICH für alle Fassaden!            │   │
│  │                                                                     │   │
│  │  SOLL:                                                              │   │
│  │    height_m = facadeZMax[direction] - facadeZMin[direction]         │   │
│  │             = Fassaden-spezifische Höhe                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
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

**Stand 14.01.2026 22:30 - ✅ IMPLEMENTIERT**

### Problem

Bei Gebäuden am Hang haben verschiedene Fassaden unterschiedliche Höhen:
- Nordseite: Terrain auf 543m → Traufe auf 555m → **12m Gerüst**
- Südseite: Terrain auf 540m → Traufe auf 555m → **15m Gerüst**

Aktuell wird eine globale `traufhoehe_m` für ALLE Fassaden verwendet.

### Lösung

Die vorhandenen `facade_z_min` und `facade_z_max` Daten nutzen um pro Fassade die korrekte Gerüsthöhe zu berechnen.

### Datenfluss (IST → SOLL)

```
IST:
  Geodata.traufhoehe_m (global: 12.5m)
       ↓
  ScaffoldFacade.target_height_m = 12.5m (für ALLE Fassaden gleich)

SOLL:
  Geodata.facade_z_min["N"] = 543.0    Geodata.facade_z_max["N"] = 555.0
  Geodata.facade_z_min["S"] = 540.0    Geodata.facade_z_max["S"] = 555.0
       ↓
  ScaffoldFacade["N"].target_height_m = 555.0 - 543.0 = 12.0m
  ScaffoldFacade["S"].target_height_m = 555.0 - 540.0 = 15.0m
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

## Changelog

| Version | Datum | Änderungen |
|---------|-------|------------|
| 6.9 | 14.01.2026 00:20 | Parquet-Pipeline (C.1-C.4) dokumentiert, DB-Statistiken aktualisiert |
| 6.8 | 13.01.2026 23:45 | Materialliste mit Stellspindeln KOMPLETT |
| 6.7 | 13.01.2026 22:00 | Editor-Visualisierung implementiert |
| 6.6 | 14.01.2026 00:00 | Hanglage z_max Fix |
| 6.5 | 14.01.2026 22:30 | Implementation Status aktualisiert |
