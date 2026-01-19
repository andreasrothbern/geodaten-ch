# Bekannte Bugs

> **NEU 13.01.2026:** `building_3d.db` wurde auf DuckDB migriert → `building_3d.duckdb`
> Historische Bug-Referenzen auf `building_3d.db` beziehen sich auf die neue DuckDB-Datei.

## ⚠️ KRITISCH: Blockierte Fassaden - Schwellenwert

**WICHTIG für zukünftige Änderungen:**

Die Erkennung blockierter Fassaden verwendet einen **Schwellenwert von 2.0m** an zwei Stellen:

| Ort | Datei | Konstante | Wert |
|-----|-------|-----------|------|
| Backend | `geruestbau.py:537` | `BLOCKING_THRESHOLD_M` | 2.0m |
| Frontend | `FacadePanel.tsx:94` | `BLOCKING_THRESHOLD_M` | 2.0m |

**Diese Werte MÜSSEN identisch sein!**

Wenn ein Nachbargebäude innerhalb von 2.0m einer Fassade liegt, wird diese als "blockiert" markiert.

**Visuelle Darstellung blockierter Fassaden:**
- **Farbe:** Hell-grau (statt farbig/rot)
- **Optik:** Tritt in den Hintergrund, nicht auswählbar
- **Bedeutung:** Kann nicht direkt eingerüstet werden (Nachbargebäude im Weg)

**Typische Fehlerquelle:** Der Backend-Wert wird auf einen niedrigeren Wert geändert (z.B. 0.5m),
während der Frontend-Wert bei 2.0m bleibt. Das führt zu inkonsistenter Anzeige.

---

## Gefixte Bugs (Neu)

### BUG-022: Blockierte Fassaden werden nicht erkannt (GEFIXT)

**Status:** ✅ Gefixt am 14.01.2026 18:15

**Problem:**
Fassaden, die eigentlich durch Nachbargebäude blockiert sein sollten, wurden als "frei" (farbig)
angezeigt statt als "blockiert" (hell-grau, im Hintergrund). Das Problem trat bei Knospenweg 4, Bern auf.

```
VOR dem Fix:                         NACH dem Fix:
┌─────────────────┐                  ┌─────────────────┐
│   Nachbar       │                  │   Nachbar       │
│   (grau)        │                  │   (grau)        │
└────────┬────────┘                  └────────┬────────┘
         │ 1.5m                               │ 1.5m
    ═════╧═════  ← ROT (falsch!)         ----+----  ← GRAU (korrekt!)
    ║         ║                          ║         ║
    ║  Kno4   ║                          ║  Kno4   ║
    ║         ║                          ║         ║
    ═══════════                          ═══════════

Legende:
  ═══ / ║ = Farbige Fassade (auswählbar)
  -------  = Blockierte Fassade (hell-grau, nicht auswählbar)
```

**Ursache:**
Der Backend-Schwellenwert für blockierte Fassaden war **0.5m** (zu streng!).
Ein Nachbargebäude musste praktisch direkt angrenzen (< 50cm) um als "blockierend" erkannt zu werden.

```python
# VOR dem Fix (geruestbau.py:536)
if neighbor.distance_m < 0.5:  # Direkt angrenzend
```

Das Frontend verwendete hingegen korrekt **2.0m** als Schwellenwert.

**Fix:**
Backend-Schwellenwert auf 2.0m erhöht, übereinstimmend mit Frontend:
```python
# NACH dem Fix (geruestbau.py:537-540)
BLOCKING_THRESHOLD_M = 2.0
if neighbor.distance_m < BLOCKING_THRESHOLD_M:
```

**Betroffene Dateien:**
- `backend/app/routers/geruestbau.py:537-540`

**Prävention:**
Siehe Abschnitt "⚠️ KRITISCH: Blockierte Fassaden - Schwellenwert" oben.

---

### BUG-028: geometry_wkb NULL nach 3D-Layer-Import (GEFIXT)

**Status:** ✅ Gefixt am 19.01.2026 18:00

**Problem:**
Nach dem Import von 3D-Layern (via `/api/v1/building/{egid}/load-3d-layers`) wurde `geometry_wkb`
nicht in der DB gespeichert. Die API meldete `walls_count: 2`, aber die Geometrie war NULL.

**Beispiel Kirche St. Peter und Paul:**
```
VOR dem Fix:
  POST /load-3d-layers → {"success": true, "walls_count": 2}
  SELECT geometry_wkb FROM building_walls WHERE egid=191821074 → NULL

NACH dem Fix:
  POST /load-3d-layers → {"success": true, "walls_count": 2}
  SELECT geometry_wkb FROM building_walls WHERE egid=191821074 → <WKB Binary>
  GET /3d-layers → walls[0].has_geometry_wkt = True
```

**Ursache:**
Zwei Probleme in `layer_fetcher.py`:

1. **`executemany` statt `execute`**: DuckDB hatte Probleme mit BLOB-Feldern bei `executemany`.
   Die Geometrie wurde nicht korrekt gespeichert.

2. **EGID als String statt Integer**: Das DB-Schema erwartet `egid INTEGER`, aber der Code
   speicherte EGID als String. Beim Laden (mit Integer) wurden keine Rows gefunden.

```python
# VOR dem Fix (layer_fetcher.py:290-297)
cursor.executemany("""
    INSERT OR REPLACE INTO building_walls ... VALUES (?, ?, ?, ?, ?)
""", [(w['gebaeudeeinheit'], w['egid'], ...)])  # egid war STRING!
```

**Fix:**
1. `executemany` durch einzelne `execute`-Aufrufe ersetzt (wie in `roof_3d_service.py`)
2. EGID zu Integer konvertiert vor dem Speichern

```python
# NACH dem Fix (layer_fetcher.py:294-314)
for w in walls:
    egid_int = int(w['egid']) if w['egid'] else None  # FIX!
    cursor.execute("""
        INSERT OR REPLACE INTO building_walls ... VALUES (?, ?, ?, ?, ?, ...)
    """, (w['gebaeudeeinheit'], egid_int, ...))  # execute statt executemany
```

**Betroffene Dateien:**
- `backend/app/services/layer_fetcher.py:280-320` - `_save_walls()`
- `backend/app/services/layer_fetcher.py:330-370` - `_save_floors()`

**Verifiziert mit:**
- Kirche St. Peter und Paul (EGID: 191821074): geometry_type=MultiPolygon, 547 Polygone
- Bundeshaus (EGID: 2242547): geometry_type=MultiPolygon

---

### BUG-026: Gerüst zu hoch bei 'Fassadenarbeit' - wall_height statt Traufhöhe (GEFIXT)

**Status:** ✅ Gefixt am 18.01.2026 04:35

**Problem:**
Bei Auswahl von "Fassadenarbeit" (facade work type) ragte das Gerüst über das Dach hinaus,
obwohl es nur bis zur Traufe (Dachansatz) gehen sollte.

**Beispiel Knospenweg 4-6:**
```
VOR dem Fix:                         NACH dem Fix:
┌─────────────────┐                  ┌─────────────────┐
│    /\   Dach    │                  │    /\   Dach    │
│   /  \          │                  │   /  \          │
│══/════\═════════│ ← Gerüst        │  /    \         │
│ /      \        │    zu hoch!     │══════════════════│ ← Gerüst
│/        \       │                  │ /      \        │    korrekt!
│══════════════════│                 │/        \       │
│   Gebäude       │                  │══════════════════│
│                 │                  │   Gebäude       │
└─────────────────┘                  └─────────────────┘
```

**Ursache:**
Die `matchFacadeToWall()` Funktion in `polygonSimplifier.ts` berechnete `wall_height = z_max - z_min`
aus dem gematchten 3D-Wand-Polygon. Bei Giebel-Fassaden (E, W bei O-W Dach) enthält dies das
Giebel-Dreieck bis zum First!

```typescript
// ConfiguratorPage.tsx:990-992 (VOR dem Fix)
if (matchResult) {
  heightM = matchResult.wall_height;  // FALSCH!
  // Giebel-Fassade: wall_height ≈ 10.7m (bis First)
  // Trauf-Fassade: wall_height ≈ 9m (bis Traufe)
}
```

Bei "Fassadenarbeit" sollte das Gerüst aber NUR bis zur TRAUFE gehen, nicht bis zum Giebel-First.

**Fix:**
`wall_height` wird NICHT mehr als Fassaden-Höhe verwendet. Stattdessen wird die Gebäude-Traufhöhe
(`facade.height_m` aus der API) beibehalten:

```typescript
// ConfiguratorPage.tsx:990-996 (NACH dem Fix)
if (matchResult) {
  facadeZMin = matchResult.polygon_z_min;
  facadeZMax = matchResult.polygon_z_max;
  // FIX 18.01.2026: NICHT wall_height verwenden!
  // Die Gerüsthöhe basiert auf facade.height_m (= Traufhöhe aus API)
  // ENTFERNT: heightM = matchResult.wall_height;
  heightSource = 'building_walls';
}
```

**Betroffene Dateien:**
- `geruestbau-app/src/pages/ConfiguratorPage.tsx:978-999`
- `geruestbau-app/src/features/scaffold-configurator/utils/polygonSimplifier.ts:651-665`

**Wichtig:** Das Wall-Matching liefert weiterhin `z_min` und `z_max` für Terrain-Höhen
(Stellspindel-Berechnung), aber NICHT mehr die Gerüsthöhe.

---

### BUG-023: TerrainProfile - Fassaden-Höhen falsch berechnet (GEFIXT)

**Status:** ✅ Gefixt am 15.01.2026 09:45

**Problem:**
Bei Gebäuden am Hang wurden die Fassaden-Höhen unterschiedlich berechnet. Das Gerüst
ragte auf der tieferen Terrain-Seite über das Dach hinaus.

**Ursache:**
```typescript
// polygonSimplifier.ts:362-363 (VOR dem Fix)
height = dirZMax - dirZMin;  // FALSCH!
// N: 555.0 - 543.0 = 12.0m
// S: 555.0 - 540.0 = 15.0m ← 3m höheres Gerüst auf Südseite!
```

Die Terrain-Differenz wurde zur Gerüsthöhe addiert statt am Boden durch Stellspindeln
ausgeglichen zu werden.

**Fix:**
Zeile `height = dirZMax - dirZMin` entfernt. Die Variable `height` bleibt jetzt
bei `defaultHeight` (Traufhöhe), konstant für alle Fassaden.

```typescript
// polygonSimplifier.ts:362-370 (NACH dem Fix)
if (dirZMin !== undefined && dirZMax !== undefined && dirZMax > dirZMin) {
  // FIX 15.01.2026 BUG-023: height bleibt defaultHeight (Traufhöhe)!
  // ENTFERNT: height = dirZMax - dirZMin;
  zMin = dirZMin;
  zMax = dirZMax;
  heightSource = 'terrain_sampled';
}
```

**Betroffene Datei:**
- `geruestbau-app/src/features/scaffold-configurator/utils/polygonSimplifier.ts:362-370`

**Verifiziert mit:**
- Knospenweg 4, Bern: Alle Fassaden haben jetzt gleiche Gerüsthöhe (5.54m)
- Terrain-Differenz (1.8m) wird weiterhin für Stellspindeln-Visualisierung verwendet

---

### BUG-025: traufhoehe_m aus GELAENDEPUNKT falsch bei Hanglagen (GEFIXT)

**Status:** ✅ Gefixt am 16.01.2026 16:00

**Problem:**
Die Traufhöhe (`traufhoehe_m`) wurde im Backend falsch berechnet. Bei Hanglagen war das
Gebäude in der 3D-Ansicht zu niedrig, und das Dach "schwebte" über dem Gebäude.

**Beispiel Knospenweg 9:**
```
GELAENDEPUNKT (swissBUILDINGS3D): 557.45 m ü.M. (Gebäudezentrum)
min(facade_z_min) (swissALTI3D):  555.80 m ü.M. (niedrigstes Terrain)
dach_min (building_roofs):        562.94 m ü.M. (Traufhöhe absolut)

ALT (FALSCH): traufhoehe = 562.94 - 557.45 = 5.49m
NEU (KORREKT): traufhoehe = 562.94 - 555.80 = 7.14m
```

**Ursache:**
`swissbuildings3d_fetcher.py` berechnete `traufhoehe = DACH_MIN - GELAENDEPUNKT`.
GELAENDEPUNKT ist aber ein **einzelner** Terrain-Punkt (meist Gebäudezentrum), der bei
Hanglagen **nicht** das niedrigste Terrain ist.

**Fix (3 Teile):**

1. **Backend API (geruestbau.py:558-589):**
   - Korrekte Berechnung: `traufhoehe = dach_min - min(facade_z_min)`
   - Überschreibt alte Werte im Response
   - Liefert `terrain_z_min` im roof-Objekt

2. **Fetcher (swissbuildings3d_fetcher.py):**
   - Legacy-Berechnung entfernt (3 Stellen)
   - `traufhoehe_m` wird jetzt als `None` gespeichert
   - Nur noch `gebaeudehoehe` (GESAMTHOEHE) wird gespeichert

3. **Datenfluss vereinfacht:**
   - Rohdaten: `dach_min`, `dach_max` in `building_roofs` (m ü.M.)
   - Terrain: `facade_z_min` aus swissALTI3D Sampling
   - Berechnung: Zentral in `geruestbau.py`

**Betroffene Dateien:**
- `backend/app/routers/geruestbau.py:558-618` - Korrekte Berechnung + Response
- `backend/app/services/swissbuildings3d_fetcher.py:388-435, 1065-1068, 1486-1497` - Legacy entfernt

**Verifiziert mit:**
- Knospenweg 9: traufhoehe_m = 7.14m (vorher 5.49m)
- 3D-Ansicht: Gebäude und Dach sind jetzt korrekt ausgerichtet

---

## Offene Bugs

### BUG-027: Multi-Building-Projekte: Gerüst nur auf Hauptgebäude (NEU)

**Status:** 🔴 Offen (erkannt 18.01.2026 05:00)

**Problem:**
Bei Multi-Building-Projekten (z.B. "Knospenweg 4-6") zeigt die 3D-Ansicht das Gerüst
**NUR** auf dem Hauptgebäude. Die zusätzlichen Gebäude werden zwar mit Gebäude + Dach
gerendert, aber **ohne Gerüst**.

**Beispiel Knospenweg 4-6:**
```
VOR dem Fix (aktuell):
┌──────────────────────────────────────────────────┐
│                                                  │
│  ┌─────────┐          ┌─────────┐               │
│  │░░░░░░░░░│          │         │               │
│  │░░Kno 4░░│          │  Kno 6  │  ← KEIN      │
│  │░░(Gerüst)│         │ (nur    │    GERÜST!   │
│  │░░░░░░░░░│          │ Gebäude)│               │
│  └─────────┘          └─────────┘               │
│                                                  │
│  Legende: ░ = Gerüst vorhanden                  │
└──────────────────────────────────────────────────┘
```

**Ursache:**
- `ScaffoldScene.tsx:1219-1221`: Gerüst wird nur für `enabledFacades` erstellt
- `enabledFacades` kommt nur vom **Hauptgebäude** (über `configuration.elements`)
- `additionalBuildings` werden in Zeilen 1276-1337 nur als **Gebäude + Dach** gerendert

**Relevante Stellen:**
```typescript
// ScaffoldScene.tsx:1219-1221 - NUR Hauptgebäude-Gerüst
enabledFacades.forEach((facade) => {
  parent.add(createScaffoldFacadeAlongEdge(facade, fieldWidth, levelHeight, bboxCenter));
});

// ScaffoldScene.tsx:1276-1337 - Zusatzgebäude OHNE Gerüst
multiBuildingData.forEach((building, index) => {
  // ... nur buildingMesh und roof werden erstellt
  // FEHLT: createScaffoldFacadeAlongEdge für dieses Gebäude
});
```

**Erforderliche Änderungen:**
1. **Frontend Interface:** `MultiBuildingData` um `facades[]` erweitern
2. **Frontend Laden:** Fassaden für alle Gebäude im Projekt berechnen
3. **3D-Renderer:** Für jedes Gebäude in `additionalBuildings` Gerüste erstellen

---

#### Schema-Änderungen (18.01.2026)

**1. MultiBuildingData erweitern** (`geruestbau.ts:49-59`):
```typescript
export interface MultiBuildingData {
  egid: string
  address: string
  polygon: [number, number][]
  center: [number, number]
  roof_dach_min_m?: number
  roof_dach_max_m?: number
  terrain_z_min?: number
  gebaeudehoehe_m?: number

  // NEU 18.01.2026 BUG-027: Fassaden für Gerüst
  facades?: Array<{
    id: string
    direction: string
    length_m: number
    height_m: number
    start_point: [number, number]
    end_point: [number, number]
  }>
}
```

**Keine DB-Änderungen nötig!** Fassaden werden aus Polygon berechnet (wie beim Hauptgebäude).

---

#### Data-Flow E2E (18.01.2026)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     NEUER DATA-FLOW                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Projekt laden (ConfiguratorPage.tsx)                               │
│     ├─ Hauptgebäude: buildingData mit selected_facades                 │
│     └─ Zusatzgebäude: buildings_data[egid] aus Projekt                 │
│                                                                         │
│  2. Fassaden berechnen (NEU - für jedes Zusatzgebäude)                 │
│     ├─ polygon → polygonToSides() → sides[]                            │
│     └─ sides[] + traufhoehe → facades[]                                │
│                                                                         │
│  3. MultiBuildingData befüllen                                         │
│     ├─ egid, address, polygon, center                                  │
│     ├─ roof_dach_min_m, roof_dach_max_m, terrain_z_min                │
│     └─ facades[] ← NEU!                                                │
│                                                                         │
│  4. ScaffoldScene.tsx rendern                                          │
│     └─ multiBuildingData.forEach((building) => {                       │
│          // Gebäude + Dach (existiert)                                 │
│          createBuildingFromPolygon(...)                                │
│          createRoofFromPolygon(...)                                    │
│                                                                         │
│          // Gerüst (NEU!)                                              │
│          building.facades?.forEach((facade) => {                       │
│            createScaffoldForAdditionalBuilding(facade, building, ...)  │
│          })                                                            │
│        })                                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

#### Implementierungsplan (18.01.2026)

| Schritt | Datei | Änderung |
|---------|-------|----------|
| 1 | `geruestbau.ts` | `MultiBuildingData.facades` Interface hinzufügen |
| 2 | `ConfiguratorPage.tsx` | Fassaden aus Polygon berechnen beim Laden |
| 3 | `ScaffoldScene.tsx` | Gerüste für `additionalBuildings` rendern |

**Betroffene Dateien:**
- `geruestbau-app/src/api/geruestbau.ts:49-59` - Interface erweitern
- `geruestbau-app/src/pages/ConfiguratorPage.tsx:762-788` - Fassaden berechnen
- `geruestbau-app/src/features/scaffold-configurator/components/threeDView/ScaffoldScene.tsx:1276-1337` - Gerüste rendern

**Workaround (bis Fix):**
Jedes Gebäude einzeln als separates Projekt anlegen.

---

### BUG-024: Wall-Layer Daten werden nicht korrekt ans Frontend gesendet

**Status:** 🟡 In Bearbeitung (erkannt 15.01.2026 10:00)

**Problem:**
Die P1-Implementation "Wall-Layer Fassaden-Höhen" ist fehlerhaft. Der `wall_facade_matcher.py`
findet nur ~20% der Fassaden (z.B. nur "E" von 5 Richtungen bei Knospenweg 4).

**Symptome:**
- `facade_z_min` enthält nur 1 von 5 Fassaden
- `service.py:1115` kehrt nach ANY Match zurück (Bug!)
- `slope_m` kommt aus Terrain-Sampling, nicht aus Wall-Layer

**Lösung implementiert (15.01.2026):**
- ✅ `building_walls[]` in API-Response `/configurator/facades` hinzugefügt
  - Naming exakt wie DB-Tabelle (`building_walls`)
  - Volle 3D-Geometrie (`coords_3d`) - ALLE Polygone bei MultiPolygon!
  - Felder: `gebaeudeeinheit`, `egid`, `z_min`, `z_max`, `geometry_type`, `coords_3d`
- ✅ `BuildingWall` Interface im Frontend erstellt (DB-Naming!)
- ✅ Alte Endpunkte als deprecated markiert
- ✅ `wall_facade_matcher.py` als deprecated markiert

**Noch offen:**
- [ ] Frontend: Geometrisches Matching für BuildingWall implementieren
- [ ] Frontend: z_min/z_max aus gematchten Wänden berechnen

**Betroffene Dateien:**
- `backend/app/routers/geruestbau.py` - `building_walls` hinzugefügt
- `backend/app/services/smart_building/wall_facade_matcher.py` - DEPRECATED
- `geruestbau-app/src/types/project.ts` - `BuildingWall` Interface

**Details:** Siehe `docs/architecture/3D_LAYER_USAGE_3D_VIEW.md` → BUG-024

---

### BUG-017: Fassaden bei Knospenweg 1 falsch dargestellt

**Status:** 🔴 Offen (erkannt 11.01.2026)

**Problem:**
Bei Knospenweg 1, Bern werden die Fassaden falsch dargestellt:
1. **Halbe Fassade:** Eine Fassade erscheint nur halb/abgeschnitten
2. **Falsche Blockierung:** Fassaden werden als blockiert angezeigt, obwohl sie frei sind
3. **Traufhöhe 0.0m:** Die Traufhöhe wird als 0.0m angezeigt (sollte ~5.5m sein)

**Screenshot:** `2026-01-11 19_11_47-Task-Manager.png`

**Betroffene Adresse:**
- Knospenweg 1, Bern (EGID 1243787)

**Vermutete Ursache:**
- Polygon-Vereinfachung (Douglas-Peucker) schneidet Fassade falsch ab
- blocked_facades Berechnung verwendet falsches EGID (siehe BUG-015)
- Höhendaten werden nicht korrekt zugeordnet

**Betroffene Dateien:**
- `backend/app/services/facade_service.py`
- `backend/app/routers/geruestbau.py` - blocked_facades Endpunkt

---

### BUG-020: Bekannte Gebäude bekommen falsche Zonen (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026

**Problem:**
Das Bundeshaus bekam Kirchen-Zonen ("Seitenschiffe", "Kirchenschiff", "Turm") statt
der korrekten Zonen ("Arkaden", "Hauptgebäude", "Kuppel") aus known_buildings.py.

**Ursache:**
Zwei Fehler:
1. **EGID-Typ:** `get_known_building()` erwartete String-EGID, aber bekam Integer
2. **Reihenfolge:** `_create_default_zone()` wurde VOR `_collect_research_data()` aufgerufen

Die Zonen wurden erstellt BEVOR `_known_zones` aus `known_buildings.py` geladen wurde.

**Fixes:**
1. `known_buildings.py:601-604` - EGID zu String konvertieren vor Lookup
2. `service.py:488-493` - Research VOR Zonen-Erstellung aufrufen

**Betroffene Dateien:**
- `backend/app/services/smart_building/known_buildings.py`
- `backend/app/services/smart_building/service.py`

**Test:**
```bash
curl "http://localhost:8000/api/v1/smart-building/data?address=Bundesplatz%203,%20Bern&include_zones=true"
# → Zonen: Arkaden, Hauptgebäude, Kuppel
```

---

### BUG-021: 3D-Layer Attribute werden nicht gespeichert (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026

**Problem:**
Bei 3D-Layer Import (on-demand für komplexe Gebäude) wurden wichtige Attribute nicht gespeichert:

| Tabelle | Felder | Status vor Fix |
|---------|--------|----------------|
| building_walls | z_min, z_max | NULL |
| building_roofs | dach_min, dach_max | NULL |
| buildings_3d | has_3d_layers | 0 (nicht gesetzt) |

**Beispiel Bundeshaus (vor Fix):**
```sql
SELECT z_min, z_max FROM building_walls WHERE egid='2242547';
-- z_min=NULL, z_max=NULL

SELECT dach_min, dach_max FROM building_roofs WHERE egid='2242547';
-- dach_min=NULL, dach_max=NULL

SELECT has_3d_layers FROM buildings_3d WHERE egid=2242547;
-- has_3d_layers=0
```

**Ursache:**
Mehrere Fehler in `roof_3d_service.py` und `layer_fetcher.py`:

1. **Wall-Layer**: INSERT ohne z_min/z_max, und falsches Attribut (`DACH_MIN` statt `GESAMTHOEHE`)
2. **Roof-Layer**: INSERT ohne dach_min/dach_max (nur Geometrie gespeichert)
3. **Flag**: `has_3d_layers` wurde nach dem Import nicht auf 1 gesetzt

**Layer-Attribute in swissBUILDINGS3D:**
- **Wall-Layer**: `GELAENDEPUNKT` (Terrain), `GESAMTHOEHE` (Höhe) → z_max = GELAENDEPUNKT + GESAMTHOEHE
- **Roof_solid-Layer**: `DACH_MIN` (Traufe ü.M.), `DACH_MAX` (First ü.M.)

**Fixes in `roof_3d_service.py`:**
1. Zeile 470-478: Wall-Attribute als `wall_props` extrahieren
2. Zeile 480-487: Roof-Attribute als `roof_props` extrahieren
3. Zeile 502-514: Roof INSERT mit dach_min/dach_max erweitert
4. Zeile 510-522: Wall INSERT mit z_min/z_max erweitert
5. Zeile 524-526: `has_3d_layers = 1` UPDATE hinzugefügt

**Fix in `layer_fetcher.py`:**
- Zeile 214-224: z_max aus `GELAENDEPUNKT + GESAMTHOEHE` berechnen

**Ergebnis nach Fix (Bundeshaus):**

| Tabelle | Feld | Wert |
|---------|------|------|
| building_walls | z_min | 541.29m |
| building_walls | z_max | 603.86m |
| building_roofs | dach_min | 569.75m |
| building_roofs | dach_max | 571.05m |
| buildings_3d | has_3d_layers | 1 |

**Test:**
```bash
cd backend
python -c "
from app.services.roof_3d_service import get_roof_3d_service
result = get_roof_3d_service().fetch_all_layers_on_demand('2242547')
print('Layers:', result['loaded_layers'])
print('Wall:', result.get('wall_props'))
print('Roof:', result.get('roof_props'))
"
# → Layers: ['Roof_solid', 'Roof', 'Wall']
# → Wall: {'z_min': 541.29, 'z_max': 603.86}
# → Roof: {'dach_min': 569.75, 'dach_max': 571.05, ...}
```

**Hinweis Floor-Layer:**
Der Floor-Layer Import ist deaktiviert wegen `fiona.errors.UnsupportedGeometryTypeError: 2147483648`.
Der Floor-Layer verwendet einen 3D-Geometrie-Typ, den Fiona nicht unterstützt.
Die Daten sind redundant zum Building_solid Layer.

**Deaktiviert in:** `layer_fetcher.py:225-247`

---

### BUG-019: NaN-EGID verursacht Parsing-Fehler (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026

**Problem:**
Bei manchen Gebäuden im GDB ist EGID als `float('nan')` gespeichert statt als Integer.
Der Code versuchte `int(nan)` aufzurufen, was fehlschlug:
```
[BUG-015] Kein Polygon-Match für (2600683.0, 1199480.0). Fallback auf nächstes Zentrum: EGID nan (dist=30.0m)
ERROR:root:Error parsing GDB for polygon: cannot convert float NaN to integer
```

**Ursache:**
- GDB speichert EGID als `float` (nicht `int`)
- Gebäude ohne EGID haben den Wert `nan`
- `if egid` ist `True` für NaN (NaN ist truthy in Python!)
- `int(nan)` wirft ValueError

**Fix:**
```python
# Vor der int-Konvertierung NaN prüfen
import math
if egid is not None and isinstance(egid, float) and math.isnan(egid):
    egid = None
```

**Betroffene Datei:**
- `backend/app/services/swissbuildings3d_fetcher.py:1015-1019` - `parse_gdb_for_building_polygon()`

---

### BUG-018: Multi-Adress-Auflösung gibt falsche EGIDs (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026 03:15

**Problem:**
Bei Multi-Adress-Auflösung (z.B. "Knospenweg 1-9, Bern") bekamen alle Adressen
die gleiche EGID statt unterschiedliche EGIDs für jedes Gebäude.

**Beispiel (vor Fix):**
```
Knospenweg 1: EGID 1243787
Knospenweg 3: EGID 1243787 (FALSCH - sollte 1243789 sein)
Knospenweg 5: EGID 1243787 (FALSCH - sollte 1243791 sein)
Knospenweg 7: EGID 1243787 (FALSCH - sollte 1243793 sein)
Knospenweg 9: EGID 1243787 (FALSCH - sollte 1243795 sein)
```

**Ursache:**
`building_3d_service.get_by_coordinates()` verwendete `ORDER BY dist_sq LIMIT 1`
und gab einfach das **nächste Gebäude nach Zentrum-Distanz** zurück - OHNE
Point-in-Polygon Check! Bei teilweise gefüllter DB (nur 1 Gebäude) wurde
dieses für alle Koordinaten zurückgegeben.

**Fix:**
`get_by_coordinates()` in `building_3d_service.py` angepasst:
1. Alle Kandidaten im Radius laden (nicht nur LIMIT 1)
2. Point-in-Polygon Check für jeden Kandidaten
3. Bei Match → Gebäude zurückgeben
4. Bei keinem Match → None (damit Stufe 2/3 das GDB parst)

**Betroffene Datei:**
- `backend/app/services/building_3d_service.py:321-420` - `get_by_coordinates()`

**Test:**
```bash
curl "http://localhost:8000/api/v1/geruestbau/address/resolve?address=Knospenweg%201-9,%20Bern"
# → 5 verschiedene EGIDs: 1243787, 1243789, 1243791, 1243793, 1243795
```

---

### BUG-016: Dach-Orientierung bei Reihenhäusern inkonsistent

**Status:** 🟡 Wartet auf 3D-Layer-Migration (erkannt 11.01.2026)

**Problem:**
Bei Reihenhäusern (z.B. Knospenweg 2-10, Bern) wechselt die Dach-Orientierung
zwischen benachbarten Gebäuden, obwohl alle Dächer gleich ausgerichtet sein sollten.

**Beispiel Knospenweg:**
```
EGID 1243788: Azimut=173° → N-S (First Ost-West)
EGID 1243790: Azimut=265° → O-W (First Nord-Süd)
EGID 1243792: Azimut=355° → N-S (First Ost-West)
EGID 1243794: Azimut=265° → O-W (First Nord-Süd)
```

**Ursache:**
Aktuell wird eine **Fallback-Heuristik** verwendet (längste Polygon-Seite),
weil die echten 3D-Layer-Daten (`has_3d_layers=0`) noch nicht extrahiert sind.

**Lösung:**
Die korrekte Dach-Orientierung sollte aus den **swissBUILDINGS3D 3D-Layern** kommen:
- `building_roofs.roof_orientation` - aus DACH-Layer Geometrie berechnet
- `building_roofs.roof_form` - Satteldach, Walmdach, etc.

**Aktueller Stand:**
```sql
SELECT has_3d_layers, roof_orientation FROM buildings_3d WHERE egid=1243790;
-- has_3d_layers=0, roof_orientation=NULL → 3D-Layer noch nicht extrahiert
```

**Nächste Schritte:**
1. 3D-Layer-Migration für Knospenweg-Tile durchführen
2. `roof_orientation` aus DACH-Layer Geometrie extrahieren
3. Frontend: `roof_orientation` aus API verwenden statt Heuristik

**Betroffene Dateien:**
- `geruestbau-app/src/features/scaffold-configurator/components/threeDView/ScaffoldScene.tsx:17-47`
  - `calculatePolygonRoofOrientation()` - NUR als Fallback wenn keine DB-Daten
- `backend/app/services/roof.py` - Sollte DB-Wert priorisieren
- `backend/app/services/layer_extractor.py` - 3D-Layer Extraktion

---

### BUG-015: EGID-Zuordnung bei Koordinaten-Lookup fehlerhaft

**Status:** ✅ Gefixt am 11.01.2026 19:45

**Problem:**
Bei der Koordinaten-basierten Gebäudesuche wurde das Gebäude mit dem
**nächsten Zentrum** zur Geocoding-Koordinate gesucht. Aber die Geocoding-Koordinate
zeigt auf den **Hauseingang**, nicht aufs Gebäudezentrum. Bei Reihenhäusern liegt
der Hauseingang oft näher am Nachbar-Zentrum!

**Beispiel Knospenweg, Bern (vor Fix):**
```
Geocoding "Knospenweg 4": E=2596299.06, N=1199805.22 (Hauseingang)

Gebäude-Zentren in building_3d.db:
  EGID 1243790: E=2596300.3, N=1199805.4  ← Knospenweg 4 (1.3m entfernt)
  EGID 1243792: E=2596299.7, N=1199812.8  ← Knospenweg 6 (7.6m entfernt)
  EGID 1243794: E=2596299.0, N=1199820.1  ← Knospenweg 8 (14.9m entfernt)

ALT: Nächstes Zentrum → EGID 1243790 (zufällig korrekt für Nr. 4)
ABER: Bei Nr. 6 war Zentrum von Nr. 8 näher als von Nr. 6 selbst!
```

**Fix:**
Statt nur nach nächstem Zentrum zu suchen, wird jetzt **Point-in-Polygon** geprüft:

1. Alle Kandidaten im Suchradius laden (mit Polygon)
2. Für jeden: Liegt die Geocoding-Koordinate **im Gebäudepolygon**?
3. Falls Match: Diese EGID zurückgeben (korrekt!)
4. Falls kein Match: Fallback auf nächstes Zentrum (mit Warnung)

**Geänderte Datei:**
- `backend/app/services/address_parser.py:26-128` - `_lookup_egid_by_coordinates()`
  - Neue Hilfsfunktion `_point_in_polygon()` (Ray-Casting, keine Dependencies)
  - Point-in-Polygon Check vor Zentrum-Fallback

**Test:**
```bash
# Multi-Adresse auflösen
curl "http://localhost:8000/api/v1/geruestbau/address/resolve?address=Knospenweg%204-8,%20Bern"
# → Jetzt sollten 3 verschiedene EGIDs zurückkommen
```

---

---

## Optimierungen

### OPT-001: egid_tile_index entfernt (07.01.2026)

**Status:** ✅ Implementiert

**Problem:**
`tile_prefetch.py` rief für jedes Gebäude `register_egid()` auf, was 7197 einzelne
DB-Transaktionen in `tiles.db/egid_tile_index` verursachte (~58s Overhead pro Tile!).

**Lösung:**
- `egid_tile_index` ist redundant seit `building_3d.db` existiert
- `building_3d.db` hat bereits `center_e`, `center_n` für Koordinaten-Lookups
- `address_parser.py` nutzt jetzt `building_3d.db` statt `tiles.db`

**Performance:**
```
VORHER:  158.9s (22ms/Gebäude)
NACHHER:  82.5s (11.5ms/Gebäude)
SPEEDUP:  1.9x (48% schneller!)
```

**Geänderte Dateien:**
- `tile_prefetch.py` - `register_egid()` Aufruf entfernt
- `address_parser.py` - Nutzt `building_3d.db` statt `tiles.db`
- `tile_cache.py` - Funktionen deprecated/umgeleitet
- `swissbuildings3d_fetcher.py` - `_register_egids_from_tile()` Aufrufe entfernt

---

### OPT-002: Direktes Fiona-Reading (08.01.2026)

**Status:** ✅ Implementiert

**Problem:**
GDB-Parsing mit geopandas war langsam (82.5s für 7197 Gebäude = 11.5ms/Gebäude).
geopandas lädt das gesamte GDB in einen GeoDataFrame, bevor iteriert wird.

**Lösung:**
Direktes Fiona-Reading ohne geopandas:
```python
# Vorher (langsam):
gdf = gpd.read_file(gdb_path, layer=layer)
for _, row in gdf.iterrows():
    geom = row['geometry']

# Nachher (schneller):
with fiona.open(gdb_path, layer=layer) as src:
    for feature in src:
        geom = shape(feature['geometry'])
```

**Vorteile:**
- Kein Memory-Overhead durch GeoDataFrame
- Streaming-Iteration statt vollständiges Laden
- Nur shapely + fiona benötigt, kein geopandas

**Performance:** ✅ Gemessen am 08.01.2026
```
VORHER:  82.5s (11.5ms/Gebäude) - geopandas
NACHHER: 70.0s (9.8ms/Gebäude)  - fiona_direct
SPEEDUP: 1.17x (15% schneller)
```

**Gesamt-Performance nach OPT-001 + OPT-002:**
```
ORIGINAL:     158.9s (22.0ms/Gebäude)
NACH OPT-001:  82.5s (11.5ms/Gebäude)  1.9x
NACH OPT-002:  70.0s (9.8ms/Gebäude)   2.2x (gesamt)
```

**Geänderte Datei:**
- `tile_prefetch.py` - `_parse_all_buildings_from_gdb()` neu implementiert

**Performance-Logging:**
Die neue Implementierung loggt automatisch:
```
[PREFETCH] GDB-Parsing: 7197 Gebäude | 45000ms (6.3ms/Gebäude) | Methode: fiona_direct
```

---

## Geplante Optimierungen

### TODO: Weitere GDB Parsing Optimierungen

**Status:** 📋 Geplant (nach OPT-002 Messung)

| Option | Beschreibung | Status | Anwendung |
|--------|--------------|--------|-----------|
| **A) Parallel-Parsing** | multiprocessing.Pool | 📋 Geplant | Batch-Import |
| **B) Direktes Fiona** | Ohne geopandas | ✅ OPT-002 | Alle |
| **C) Vorberechnung** | Alle Gebäude beim Download | 📋 Geplant | Nur Batch-Import |

**Option A - Details:**
Parallelisierung mit multiprocessing für Batch-Imports.
⚠️ Achtung: Fiona-Features sind nicht picklable, müsste Koordinaten serialisieren.
→ Svoll kombiniert mit Option C bei Massenimport.

**Option C - Analyse (08.01.2026):**

Bei User-Requests ist Vorberechnung NICHT sinnvoll:
```
MIT Vorberechnung:  5-10s (Download) + 70s (Parsing) = ~80s Wartezeit
OHNE (aktuell):     5-10s (Download) + 0.5s (1 Geb.) = ~10s Wartezeit
```
→ User Experience würde sich verschlechtern!

**Sinnvoll NUR bei Batch-Import** (z.B. `scripts/import_tiles.py`):
- Kein User wartet → Zeit spielt keine Rolle
- Alle Tiles auf einmal importieren
- Kombinierbar mit Option A (Parallel-Parsing)

**Kleine Optimierungen (optional):**
- **C1:** Paralleles Parsing während ZIP-Entpackung (~1-2s Gewinn)
- **C2:** Prefetch mit höherer Priorität (schnellere Cache-Füllung)

> Siehe `docs/architecture/BATCH_IMPORT.md` für vollständige Dokumentation des Import-Prozesses.

---

## Gefixte Bugs

### BUG-014: Neighbors-API liest aus falscher DB (GEFIXT)

**Status:** ✅ Gefixt am 07.01.2026

**Problem:**
Die Neighbors-API suchte nur in `smart_building_cache`, aber via `tile_prefetch`
werden ALLE Gebäude eines Tiles in `building_3d.db` gespeichert.

**Fix:**
- **Nachbarn:** Direkt aus `building_3d.db` mit koordinaten-basierter Suche
- **Zielgebäude:** building_3d.db zuerst, dann smart_building_cache als Fallback
  (für den Fall dass das Bundle existiert bevor prefetch läuft)

**Geänderte Datei:**
`backend/app/services/neighbors_service.py`

### BUG-013: Zonen nicht an 3D-Viewer übertragen (GEFIXT)

**Status:** ✅ Gefixt am 05.01.2026

**Problem:**
`convertGeodataToConfiguratorFormat()` in `ConfiguratorPage.tsx` übertrug keine
Zonen-Daten an den 3D-Viewer.

**Fix:**
Zonen, building_name, complexity und research_source werden jetzt korrekt
in das `BuildingConfig` Objekt kopiert.

**Betroffene Datei:**
`geruestbau-app/src/pages/ConfiguratorPage.tsx:340-380`
