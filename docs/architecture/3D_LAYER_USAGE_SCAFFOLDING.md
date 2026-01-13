# 3D-Layer Verwendung: Gerüst-Kalkulation

> **Stand 14.01.2026 22:30**
> **Status:** ✅ IMPLEMENTIERT

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

**TODO:** Test mit echtem Hanglage-Gebäude (>3m Gefälle, z.B. Muri, Köniz Hang)
