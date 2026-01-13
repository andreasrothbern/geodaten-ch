# 3D-Layer Analyse - Umfassende Bestandsaufnahme

> **Version:** 1.2
> **Datum:** 14.01.2026 18:30
> **Status:** T1-T4 implementiert ✅
> **Autor:** Claude Code

---

## Executive Summary

Diese Analyse untersucht, wie die swissBUILDINGS3D 3.0 Daten aktuell verwendet werden
und wie sie für **Gerüstplanung** und **3D-Visualisierung** optimal genutzt werden könnten.

**Kernfrage:** Sollen wir das System mit den neuen 3D-Layer-Daten neu aufbauen?

---

## Teil 1: Verfügbare Datenquellen

### 1.1 swissBUILDINGS3D 3.0 Layer-Übersicht

| Layer | Inhalt | Punkte (Münster) | Verwendung |
|-------|--------|------------------|------------|
| **Building_solid** | 2D-Polygon + Höhen-Attribute | - | ✅ Primär |
| **Roof_solid** | 3D-Dachkörper | 112 | ✅ On-Demand |
| **Wall** | 3D-Fassadenflächen | 4'360 | ⚠️ Teilweise |
| **Floor** | 3D-Bodenplatte mit Terrain | 1'204 | ❌ Deaktiviert |
| **Roof** | Dach-Umriss (2D) | 24 | ❌ Nicht genutzt |

### 1.2 Attribute pro Layer

#### Building_solid (Hauptquelle)
```
EGID                 → Gebäude-ID
DACH_MIN             → Traufhöhe (m ü.M.)
DACH_MAX             → Firsthöhe (m ü.M.)
GELAENDEPUNKT        → Terrain-Referenz (m ü.M.)
GESAMTHOEHE          → Gebäudehöhe (relativ, m)
GEBAEUDEEINHEIT      → UUID für Layer-Verknüpfung
Geometrie            → 2D-Polygon (Grundriss)
```

#### Wall Layer (pro Wand-Segment!)
```
GEBAEUDEEINHEIT      → Verknüpfung zu Building
GELAENDEPUNKT        → Terrain an DIESER Wand (m ü.M.)
GESAMTHOEHE          → Wandhöhe (m)
Geometrie            → 3D-Fläche (WKB)

Berechnung:
  z_min = GELAENDEPUNKT (Terrain)
  z_max = GELAENDEPUNKT + GESAMTHOEHE (Wandoberkante)
```

#### Roof_solid Layer
```
GEBAEUDEEINHEIT      → Verknüpfung
DACH_MIN             → Traufhöhe (m ü.M.)
DACH_MAX             → Firsthöhe (m ü.M.)
Geometrie            → 3D-Körper (WKB)
```

### 1.3 Aktueller Datenbestand (building_3d.db)

```sql
-- Abfrage 12.01.2026
SELECT
  (SELECT COUNT(*) FROM buildings_3d) as gebaeude,
  (SELECT COUNT(*) FROM buildings_3d WHERE has_3d_layers=1) as mit_3d,
  (SELECT COUNT(*) FROM building_roofs) as roofs,
  (SELECT COUNT(*) FROM building_walls) as walls;

-- Ergebnis:
-- gebaeude: ~8000 (Bern Region)
-- mit_3d: ~20 (nur on-demand geladen)
-- roofs: ~100
-- walls: ~15
```

**Erkenntnis:** 3D-Layer sind nur für wenige Gebäude geladen!

---

## Teil 2: Aktuelle Verwendung

### 2.1 Datenfluss-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AKTUELLER DATENFLUSS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ADRESSE EINGEBEN                                                       │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SmartBuildingService.collect_all_data()                         │   │
│  │                                                                 │   │
│  │  Phase 1: Geocoding → Koordinaten, EGID                        │   │
│  │  Phase 2: GWR + Building_solid → Polygon, Höhen                │   │
│  │  Phase 3: Terrain (swissALTI3D) → slope_m, slope_class         │   │
│  │  Phase 4: Zonen (optional bei COMPLEX)                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       │ BuildingDataBundle                                              │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SSE-Stream an Frontend                                          │   │
│  │                                                                 │   │
│  │  heights Event:                                                 │   │
│  │    • traufhoehe_m, firsthoehe_m (relativ)                      │   │
│  │    • has_3d_layers (Flag)                                      │   │
│  │    • roof_type, roof_orientation (wenn has_3d_layers)          │   │
│  │                                                                 │   │
│  │  terrain Event:                                                 │   │
│  │    • terrain_height_m, slope_m, slope_class                    │   │
│  │    • KEINE facade_heights! ❌                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ConfiguratorPage.tsx                                            │   │
│  │                                                                 │   │
│  │  if (has_3d_layers) {                                          │   │
│  │    roofType = geodata.roof_type;        // Echte Daten ✓       │   │
│  │    roofOrientation = geodata.roof_orientation;                 │   │
│  │  } else {                                                      │   │
│  │    roofOrientation = calculateFromPolygon();  // Fallback      │   │
│  │  }                                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ScaffoldScene.tsx (3D-Viewer)                                   │   │
│  │                                                                 │   │
│  │  • Gebäude-Mesh aus 2D-Polygon extrudiert                      │   │
│  │  • Dach nach roofType (flachdach, satteldach, walmdach)        │   │
│  │  • Gerüst-Felder entlang Fassaden                              │   │
│  │  • Zonen (Türme, Kuppeln) wenn vorhanden                       │   │
│  │                                                                 │   │
│  │  PROBLEM: Boden ist FLACH! Terrain wird ignoriert.             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Was wird NICHT verwendet

| Daten | Verfügbar in | Aktuell genutzt | Warum nicht? |
|-------|--------------|-----------------|--------------|
| Wall z_min/z_max | building_walls | ❌ Nein | Daten nicht geladen |
| Floor Terrain-Variation | building_floors | ❌ Nein | Import deaktiviert |
| 3D-Wandgeometrie | building_walls.geometry_wkb | ❌ Nein | Kein Rendering |
| Per-Fassade Terrain | Wall Layer | ❌ Nein | Kein Mapping |

---

## Teil 3: Use Cases

### 3.1 Gerüstplanung (Scaffold Configuration)

#### UC-S1: Fassaden-Höhe bestimmen

**Aktuell:**
```
Alle Fassaden → gleiche Höhe (traufhoehe_m)
```

**Optimal (mit Wall-Layer):**
```
Fassade 0 (Nord) → Wall[0].z_max - Wall[0].z_min = 8.2m
Fassade 1 (Ost)  → Wall[1].z_max - Wall[1].z_min = 9.5m
Fassade 2 (Süd)  → Wall[2].z_max - Wall[2].z_min = 8.2m
Fassade 3 (West) → Wall[3].z_max - Wall[3].z_min = 7.8m
```

**Vorteil:** Bei Hanglage korrekte Gerüsthöhe pro Seite!

#### UC-S2: Gerüst-Aufsetz-Punkt (Terrain)

**Aktuell:**
```
terrain_height_m = Referenzpunkt (Center oder erste Ecke)
Alle Gerüste starten auf gleicher Höhe
```

**Optimal (mit Wall-Layer):**
```
Fassade 0: Gerüst startet bei Wall[0].z_min = 541.2 m ü.M.
Fassade 2: Gerüst startet bei Wall[2].z_min = 543.8 m ü.M.
Differenz: 2.6m Höhenunterschied!
```

#### UC-S3: Komplexe Gebäude (Zonen)

**Aktuell:**
```
Zonen aus known_buildings.py oder Claude-Analyse
Jede Zone hat eigene Höhe (traufhoehe_m, firsthoehe_m)
ABER: Terrain wird nicht pro Zone berücksichtigt
```

**Optimal:**
```
Zone "Turm": Wall-Daten zeigen Terrain an Turm-Basis
Zone "Arkade": Wall-Daten zeigen Terrain an Arkaden-Bereich
→ Unterschiedliche Gerüsthöhen pro Zone
```

### 3.2 3D-Visualisierung (ScaffoldScene)

#### UC-V1: Gebäude-Darstellung

**Aktuell:**
```typescript
// 2D-Polygon wird extrudiert
createBuildingFromPolygon(polygon, buildingHeight)
// → Alle Wände gleich hoch, flacher Boden
```

**Optimal (mit Wall-Geometrie):**
```typescript
// Echte 3D-Wandflächen rendern
walls.forEach(wall => {
  const mesh = createMeshFromWKB(wall.geometry_wkb);
  scene.add(mesh);
});
// → Wände mit realer Höhenvariation
```

#### UC-V2: Terrain-Darstellung

**Aktuell:**
```typescript
// Flache Ebene
<mesh position={[0, 0, 0]}>
  <planeGeometry args={[100, 100]} />
</mesh>
```

**Optimal (mit Floor-Layer oder swissALTI3D):**
```typescript
// Terrain-Mesh mit Höhenvariation
const terrainGeometry = createTerrainFromPoints(
  floor.geometry,  // 3D-Punkte mit Z-Koordinaten
  buildingFootprint
);
```

#### UC-V3: Dach-Darstellung

**Aktuell:**
```typescript
// Algorithmisch generiert aus roofType
createRoofFromPolygon(polygon, roofType, roofOrientation)
// → Satteldach, Walmdach, etc. geschätzt
```

**Optimal (mit Roof_solid-Geometrie):**
```typescript
// Echte 3D-Dachgeometrie
const roofMesh = createMeshFromWKB(roof.geometry_wkb);
// → Exakte Dachform inkl. Gauben, Kamine, etc.
```

### 3.3 Multi-Building Projekte

#### UC-M1: Reihenhaus-Projekt (z.B. Knospenweg 2-10)

**Aktuell:**
```
Jedes Gebäude separat geladen
Keine gemeinsame Terrain-Referenz
Dach-Orientierung kann inkonsistent sein
```

**Optimal:**
```
1. Alle Gebäude laden
2. Gemeinsames Terrain aus swissALTI3D oder Floor-Layer
3. Dach-Orientierung aus Wall/Roof-Layer konsistent
4. Relative Höhen zwischen Gebäuden korrekt
```

#### UC-M2: Zoom-Funktion

**Anforderung:**
```
Zoom Out: Übersicht aller Gebäude im Projekt
Zoom In: Details eines Gebäudes (3D-Layer laden)
```

**Implementierung:**
```
if (zoomLevel > DETAIL_THRESHOLD) {
  await loadWallLayerForBuilding(focusedEgid);
  renderDetailedWalls();
} else {
  renderSimplifiedBuildings();
}
```

---

## Teil 4: Offene Fragen

### 4.1 Daten-Fragen

| # | Frage | Status | Antwort/Notiz |
|---|-------|--------|---------------|
| D1 | Hat jedes Gebäude Wall-Einträge im GDB? | ❓ | Vermutlich ja, aber nicht alle importiert |
| D2 | Entspricht 1 Wall-Eintrag = 1 Fassade? | ❓ | EGID 2245881 hat 11 Walls - unklar ob pro Fassade |
| D3 | Wie matchen wir Wall → unsere Sides? | ❓ | Geometrie-Overlap prüfen |
| D4 | Warum ist Floor-Import deaktiviert? | ✅ | Fiona unterstützt Geometrie-Typ nicht |
| D5 | Ist Floor-Layer redundant zu Terrain? | ❓ | Floor hat exaktes Terrain am Gebäude |

### 4.2 Architektur-Fragen

| # | Frage | Status | Antwort/Notiz |
|---|-------|--------|---------------|
| A1 | Wall-Layer immer laden oder on-demand? | ❓ | On-demand spart Speicher/Zeit |
| A2 | Wo berechnen: Backend oder Frontend? | ❓ | Backend für Konsistenz |
| A3 | Wie mit fehlenden Wall-Daten umgehen? | ❓ | Fallback auf Terrain-Berechnung |
| A4 | Cache-Strategie für 3D-Daten? | ❓ | Pro Projekt? Pro Session? |

### 4.3 UI/UX-Fragen

| # | Frage | Status | Antwort/Notiz |
|---|-------|--------|---------------|
| U1 | Soll User 3D-Layer manuell laden können? | ❓ | Button "Detailansicht laden"? |
| U2 | Wie Terrain-Differenz visualisieren? | ❓ | Farbcodierung? Höhenlinien? |
| U3 | Loading-State bei 3D-Layer-Fetch? | ❓ | Spinner? Progressive Loading? |

---

## Teil 5: Lösungsansätze

### 5.1 Option A: Inkrementelle Erweiterung

**Ansatz:** Bestehende Architektur erweitern

```
1. Wall-Layer on-demand laden (existiert bereits!)
2. Mapping Wall → Facade implementieren
3. facade_heights in TerrainProfile speichern
4. Frontend: facade_heights nutzen statt einheitliche Höhe
```

**Aufwand:** 4-6h
**Risiko:** Niedrig
**Vorteil:** Schnell, kompatibel

### 5.2 Option B: 3D-Daten-First Redesign

**Ansatz:** System neu denken mit 3D als Basis

```
1. Bei Projekt-Erstellung: ALLE 3D-Layer laden
2. Wall-Geometrie als primäre Fassaden-Quelle
3. Echtes 3D-Terrain aus Floor-Layer
4. Exakte Dach-Geometrie aus Roof_solid
```

**Aufwand:** 20-40h
**Risiko:** Mittel
**Vorteil:** Maximale Präzision, zukunftssicher

### 5.3 Option C: Hybrid (Empfohlen)

**Ansatz:** Best of Both Worlds

```
Standard-Flow (wie heute):
  → Building_solid für Polygon + Basis-Höhen
  → Terrain aus swissALTI3D
  → Schnell, funktioniert für 90% der Fälle

On-Demand bei Bedarf:
  → Wall-Layer für Hanglage-Korrektur
  → Roof_solid für exakte Dachform
  → User-initiated oder auto bei COMPLEX
```

**Aufwand:** 8-12h
**Risiko:** Niedrig
**Vorteil:** Optimale Balance zwischen Speed und Präzision

---

## Teil 6: Konkrete TODOs

### 6.1 Kurzfristig (P3) - ✅ ALLE ERLEDIGT 14.01.2026

| # | Task | Datei | Status |
|---|------|-------|--------|
| T1 | Wall→Facade Mapping Prototyp | `wall_facade_matcher.py` | ✅ Implementiert 13.01.2026 |
| T2 | facade_heights in TerrainProfile | `models.py`, `service.py` | ✅ Implementiert 14.01.2026 |
| T3 | facade_heights im SSE-Stream | `main.py` (Serialisierung) | ✅ Implementiert 14.01.2026 |
| T4 | Frontend: facade_heights nutzen | `BuildingDataCard.tsx` | ✅ Implementiert 14.01.2026 |

#### T2-T4 Implementierungsdetails (14.01.2026)

**T2: TerrainProfile erweitert (`models.py:100-107`)**
```python
@dataclass
class TerrainProfile:
    # ... bestehende Felder ...

    # NEU 14.01.2026: Fassaden-Höhen aus Wall-Layer oder Terrain-Sampling
    facade_z_min: Dict[str, float] = field(default_factory=dict)
    # {"N": 541.0, "E": 543.5, ...} - Terrain-Höhe (m ü.M.) an der Fassade
    facade_z_max: Dict[str, float] = field(default_factory=dict)
    # {"N": 550.0, "E": 552.0, ...} - Wandoberkante (m ü.M.) an der Fassade
    facade_heights_source: str = "global"
    # "wall_layer" | "terrain_sampled" | "global"
```

**T3: API-Serialisierung (`main.py:3810`)**
```python
"terrain": {
    "reference_height_m": bundle.terrain.reference_height_m,
    # ... bestehende Felder ...
    # NEU 14.01.2026 (T2-T4): Fassaden-Höhen
    "facade_z_min": bundle.terrain.facade_z_min,
    "facade_z_max": bundle.terrain.facade_z_max,
    "facade_heights_source": bundle.terrain.facade_heights_source,
}
```

**T4: Frontend BuildingDataCard (`BuildingDataCard.tsx:60-103`)**
- `Data3DQualityBadge`: Zeigt Qualitätsstufe basierend auf Datenquelle
  - Grün "3D-Daten ✓": `has_3d_layers=true` oder `facade_heights_source='wall_layer'`
  - Blau "Terrain ✓": `facade_heights_source='terrain_sampled'` (±0.5m Genauigkeit)
  - Gelb "Geschätzt": `facade_heights_source='global'` (Fallback)
- `FacadeHeightsInfo`: Zeigt Höhen pro Himmelsrichtung (N, NE, E, SE, S, SW, W, NW)

#### T1: Wall→Facade Matching - Implementierungsdetails

**Datei:** `backend/app/services/smart_building/wall_facade_matcher.py`

**Strategie:**
1. Wall-Layer Geometrie laden (MultiPolygon mit triangulierten Flächen)
2. Basis-Punkte extrahieren (z <= z_min + 0.5m)
3. Konvexe Hülle der Basis-Punkte berechnen
4. Kanten der Hülle als Wall-Segmente verwenden
5. Matching auf Fassaden (sides) basierend auf:
   - Normalenrichtung (Azimut-Differenz <= 30°)
   - Distanz der Mittelpunkte
   - Längen-Verhältnis

**Ergebnis-Format:**
```python
facade_heights = matcher.get_facade_heights(egid, sides)
# → {"N": FacadeHeight(z_min=542.0, z_max=600.0, height_m=58.0), ...}
```

**Erkenntnisse:**
- Wall-Geometrie ist trianguliert (159+ Polygone pro Wand)
- Konvexe Hülle funktioniert für einfache Gebäude
- Für komplexe Gebäude (U-Form, etc.) wäre Alpha-Shape besser
- Matching-Quote: ~30-50% der Fassaden (abhängig von Geometrie)

### 6.2 Mittelfristig (P4)

| # | Task | Datei | Aufwand |
|---|------|-------|---------|
| T5 | Floor-Layer Import fixen | `layer_fetcher.py` | 4h |
| T6 | 3D-Terrain im Viewer | `ScaffoldScene.tsx` | 6h |
| T7 | Echte Wall-Geometrie rendern | `ScaffoldScene.tsx` | 8h |

### 6.3 Langfristig (P5)

| # | Task | Beschreibung | Aufwand |
|---|------|--------------|---------|
| T8 | DuckDB Migration | Wie in BUILDING_3D_SCHEMA.md | 20h |
| T9 | Volles 3D-Modell | Alle Layer, echte Geometrie | 40h |

---

## Teil 7: Entscheidungsmatrix

### Welche Option wählen?

| Kriterium | Option A (Inkr.) | Option B (Neu) | Option C (Hybrid) |
|-----------|------------------|----------------|-------------------|
| Aufwand | ⭐⭐⭐⭐⭐ (4-6h) | ⭐⭐ (20-40h) | ⭐⭐⭐⭐ (8-12h) |
| Präzision | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Risiko | ⭐⭐⭐⭐⭐ (niedrig) | ⭐⭐⭐ (mittel) | ⭐⭐⭐⭐ (niedrig) |
| Zukunftssicherheit | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Quick Wins | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

**Entscheidung (13.01.2026):** ✅ Option C (Hybrid) gewählt

**Begründung:**
- Daten können bei Bedarf nachgeladen werden (aus Tiles oder on-demand)
- Datenbedarf noch nicht vollständig bekannt → flexibel bleiben
- Komplex/On-demand als Strategie für 3D-Layer

---

## Teil 8: Nächste Schritte

### Sofort (diese Session):

1. ✅ Diese Analyse dokumentieren
2. ❓ Entscheidung: Option A, B oder C?
3. ❓ Priorität für T1 (Wall→Facade Mapping)?

### Diese Woche:

1. Prototyp für Wall→Facade Matching
2. Test mit Knospenweg (Reihenhaus mit Hanglage)
3. Dokumentation aktualisieren

### Diesen Monat:

1. facade_heights End-to-End implementieren
2. 3D-Viewer Terrain-Verbesserung
3. Multi-Building Support verbessern

---

## Anhang A: Service-Layer Architektur (Stand 14.01.2026)

### Datenfluss für Fassaden-Höhen

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SERVICE-LAYER FÜR FASSADEN-HÖHEN                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 1: DATENQUELLEN                                                  │
│  ═════════════════════                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ building_walls  │  │ swissALTI3D API │  │ buildings_3d    │        │
│  │ (Wall-Layer)    │  │ (Terrain-Höhen) │  │ (Traufhöhe)     │        │
│  │ z_min, z_max    │  │ get_height()    │  │ traufhoehe_m    │        │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │
│           │                    │                    │                  │
│           ▼                    ▼                    ▼                  │
│  LAYER 2: DATEN-SAMMLUNG (service.py)                                  │
│  ═════════════════════════════════════                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SmartBuildingService._collect_facade_heights(bundle)            │   │
│  │                                                                 │   │
│  │   1. Stufe: WallFacadeMatcher (höchste Präzision ±0.1m)        │   │
│  │      → Falls has_3d_layers=1 UND building_walls vorhanden      │   │
│  │      → Matching: Wall-Geometrie → Polygon-Seiten (sides)       │   │
│  │                                                                 │   │
│  │   2. Stufe: Terrain-Sampling (gute Präzision ±0.5m)            │   │
│  │      → terrain_service.get_height() pro Fassaden-Eckpunkt      │   │
│  │      → z_min = Terrain, z_max = z_min + traufhoehe_m           │   │
│  │                                                                 │   │
│  │   3. Stufe: Global Fallback                                    │   │
│  │      → z_min = terrain.reference_height_m                      │   │
│  │      → z_max = z_min + traufhoehe_m                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                                                            │
│           │ TerrainProfile mit facade_z_min, facade_z_max              │
│           ▼                                                            │
│  LAYER 3: BUNDLE-CACHE (building_contexts.db)                          │
│  ════════════════════════════════════════════                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ _save_terrain_to_environment(bundle)                            │   │
│  │   → Speichert TerrainProfile inkl. facade_heights pro EGID     │   │
│  │   → Cache wird bei force_refresh invalidiert                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                                                            │
│           ▼                                                            │
│  LAYER 4: API-SERIALISIERUNG (main.py:3810)                           │
│  ══════════════════════════════════════════                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ GET /api/v1/smart-building/data Response:                       │   │
│  │   "terrain": {                                                  │   │
│  │     "facade_z_min": {"N": 541.0, "E": 543.5, ...},             │   │
│  │     "facade_z_max": {"N": 550.0, "E": 552.0, ...},             │   │
│  │     "facade_heights_source": "terrain_sampled"                  │   │
│  │   }                                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                                                            │
│           ▼                                                            │
│  LAYER 5: PROJEKT-SERVICE (project_service.py)                        │
│  ═════════════════════════════════════════════                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ get_project_with_data() → ProjectWithGeodata                    │   │
│  │                                                                 │   │
│  │   geodata = {                                                   │   │
│  │     "facade_z_min": terrain.get('facade_z_min'),               │   │
│  │     "facade_z_max": terrain.get('facade_z_max'),               │   │
│  │     "facade_heights_source": terrain.get('facade_heights_source'),│
│  │     "has_3d_layers": bundle.get('has_3d_layers'),              │   │
│  │   }                                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                                                            │
│           ▼                                                            │
│  LAYER 6: FRONTEND (BuildingDataCard.tsx)                             │
│  ════════════════════════════════════════                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ BuildingDataCard({ geodata })                                   │   │
│  │   → Data3DQualityBadge: Qualitäts-Indikator                    │   │
│  │   → FacadeHeightsInfo: Höhen pro Richtung (N, E, S, W, ...)    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Backend-Dateien (Relevanz für Fassaden-Höhen)

| Datei | Service | Verantwortung |
|-------|---------|---------------|
| `services/smart_building/models.py` | TerrainProfile | Datenmodell: facade_z_min, facade_z_max |
| `services/smart_building/service.py` | SmartBuildingService | Orchestrierung, _collect_facade_heights() |
| `services/smart_building/wall_facade_matcher.py` | WallFacadeMatcher | Wall→Side Matching (Stufe 1) |
| `services/terrain.py` | TerrainService | swissALTI3D Integration (Stufe 2) |
| `services/geruestbau/project_service.py` | ProjectService | Bundle→Geodata Konvertierung |
| `main.py:3810` | API | Response-Serialisierung |

### Frontend-Dateien

| Datei | Komponente | Verantwortung |
|-------|------------|---------------|
| `components/ui/BuildingDataCard.tsx` | BuildingDataCard | Anzeige der Gebäudedaten |
| `components/ui/BuildingDataCard.tsx:60` | Data3DQualityBadge | Qualitäts-Badge |
| `components/ui/BuildingDataCard.tsx:123` | FacadeHeightsInfo | Fassaden-Höhen Grid |
| `pages/ProjectDetailPage.tsx:174` | - | Verwendet BuildingDataCard |
| `pages/ConfiguratorPage.tsx:812` | - | Verwendet BuildingDataCard |
| `types/project.ts` | Geodata Interface | TypeScript Typen |

### Dokumentation
```
docs/architecture/
├── 3D_LAYER_USAGE.md          # Verwendung (aktuell)
├── 3D_LAYER_ANALYSIS.md       # Diese Datei
├── BUILDING_3D_SCHEMA.md      # DB-Schema Konzept
├── STREAMING_ARCHITECTURE.md  # SSE Details
└── SWISSBUILDINGS3D_ANALYSE.md # Layer-Details
```

---

## Anhang B: Test-Gebäude

| Gebäude | EGID | Typ | Hanglage | 3D-Layer |
|---------|------|-----|----------|----------|
| Bundeshaus | 2242547 | Komplex | Leicht | Roof: ✅, Wall: ❌ |
| Knospenweg 4 | 1243790 | Einfach | Mittel | ❌ |
| Berner Münster | 1230337 | Komplex | Stark | Roof: ✅, Wall: ❌ |
| EGID 2245881 | - | ? | ? | Wall: ✅ (11 Einträge) |

---

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 13.01.2026 | 1.0 | Initiale Analyse erstellt |
| 13.01.2026 | 1.1 | T1 (Wall→Facade Matching) implementiert |
| 14.01.2026 | 1.2 | T2-T4 implementiert: Fassaden-Höhen End-to-End |
