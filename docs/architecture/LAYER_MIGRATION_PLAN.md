# Layer-Migration: 3D-Daten für Gebäude

> **Version:** 1.2 (11.01.2026)
> **Status:** Planung
> **Ziel:** Vollständige 3D-Daten für komplexe Gebäude

## Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.2 | 11.01.2026 | Floor-Tabelle wieder aufgenommen (Schema komplett, On-Demand für komplexe) |
| 1.1 | 11.01.2026 | Floor-Layer Analyse durchgeführt |
| 1.0 | 11.01.2026 | Initiales Design |

## Übersicht

### Problem

1. **Tiles sind zu gross** für dauerhaften Server-Speicher (~80GB für CH)
2. **Dachform wird geschätzt** statt aus echter 3D-Geometrie berechnet
3. **Keine echten 3D-Daten** für Fassaden

### Lösung: Hybrid-Ansatz

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATENSTRATEGIE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRE-IMPORT (lokal, einmal)                                     │
│  ══════════════════════════                                     │
│  ├─ Building_solid → buildings (alle Gebäude)                   │
│  │   └─ EGID, Polygon, Höhen, Koordinaten                      │
│  │   └─ NEU: objektart, name_komplett, gebaeudeeinheit         │
│  │                                                              │
│  └─ Roof_solid → building_roofs (alle Gebäude)                  │
│      └─ Dachform berechnet aus 3D-Geometrie                    │
│      └─ roof_form, roof_angle_deg, roof_orientation            │
│      └─ NEU: ECHTE 3D-Geometrie als WKB gespeichert!           │
│      └─ Für Frontend-Visualisierung (Bug-Fix 11.01.2026)       │
│                                                                 │
│  Ergebnis: building_3d.db (~50-100MB für Region Bern)           │
│  → Upload zu Railway                                            │
│                                                                 │
│  ON-DEMAND (Server, pro Projekt)                                │
│  ════════════════════════════════                               │
│  Für MODERATE/COMPLEX Gebäude im aktiven Projekt:               │
│  ├─ Wall → building_walls (3D-Fassadengeometrie)               │
│  └─ Roof_solid → building_roofs (vollständige 3D-Geometrie)    │
│                                                                 │
│  Tile wird nach Import GELÖSCHT (kein Disk-Verbrauch)           │
│                                                                 │
│  NICHT IMPORTIERT:                                              │
│  ├─ Floor → Building_solid Polygon reicht (Analyse 11.01.2026) │
│  └─ Roof → Nur Umriss auf Traufhöhe, wenig Mehrwert            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Layer-Nutzungsübersicht

| Layer | Schema | Pre-Import | On-Demand | Begründung |
|-------|--------|------------|-----------|------------|
| **Building_solid** | ✅ buildings | ✅ Ja | - | Polygon, Höhen, Attribute |
| **Roof_solid** | ✅ building_roofs | ✅ Ja + Geometrie! | - | Dachform + 3D-Visualisierung |
| **Wall** | ✅ building_walls | ❌ | ✅ Ja | 3D-Fassaden |
| **Floor** | ✅ building_floors | ❌ | ✅ Ja | Exakter Grundriss für komplexe Gebäude |
| **Roof** | ❌ | ❌ | ❌ | Nur Umriss auf Traufhöhe, kein Mehrwert |

> **Änderung 11.01.2026:** Roof_solid Geometrie wird IMMER gespeichert (nicht nur on-demand).
> Grund: Frontend benötigt echte Dach-Geometrie für korrekte Visualisierung.

> **Hinweis Floor:** Für EINFACHE Gebäude reicht Building_solid Polygon (Median +0.02% Unterschied).
> Für KOMPLEXE Gebäude wird Floor on-demand geladen für exakte Fassadenposition.

---

## Phase 1: DB-Schema

### 1.1 Erweiterte `buildings` Tabelle

```sql
-- Neue Spalten für alle Gebäude
ALTER TABLE buildings ADD COLUMN objektart TEXT;
ALTER TABLE buildings ADD COLUMN name_komplett TEXT;
ALTER TABLE buildings ADD COLUMN gebaeude_nutzung TEXT;
ALTER TABLE buildings ADD COLUMN gebaeudeeinheit TEXT;

-- Dach-Attribute (Variante A: berechnet)
ALTER TABLE buildings ADD COLUMN roof_form TEXT;
-- Werte: 'flachdach', 'satteldach', 'pultdach', 'walmdach', 'zeltdach', 'mansarddach', 'komplex'
ALTER TABLE buildings ADD COLUMN roof_form_confidence REAL;
-- 0.0 - 1.0 (wie sicher ist die Erkennung?)
ALTER TABLE buildings ADD COLUMN roof_orientation TEXT;
-- 'N-S', 'O-W', 'NO-SW', 'NW-SO' (First-Verlauf)

-- Flag: Hat dieses Gebäude erweiterte 3D-Daten?
ALTER TABLE buildings ADD COLUMN has_3d_layers INTEGER DEFAULT 0;
```

### 1.2 Neue Tabelle `building_roofs`

```sql
-- Variante B: Dach-Geometrie für ausgewählte Gebäude
CREATE TABLE building_roofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gebaeudeeinheit TEXT NOT NULL,
    egid TEXT,

    -- Berechnete Werte (aus 3D-Geometrie)
    dach_min REAL,              -- Traufhöhe (m ü.M.)
    dach_max REAL,              -- Firsthöhe (m ü.M.)
    roof_form TEXT,             -- Erkannte Dachform
    roof_angle_deg REAL,        -- Berechnete Neigung
    roof_orientation TEXT,      -- First-Verlauf
    z_levels TEXT,              -- JSON: [546.9, 551.0, 552.7, ...] für Analyse

    -- 3D-Geometrie (nur für komplexe Gebäude, on-demand)
    geometry_wkb BLOB,          -- 3D MultiPolygon als WKB (NULL bei Pre-Import)
    has_full_geometry INTEGER DEFAULT 0,

    -- Metadaten
    calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    calculation_method TEXT     -- 'z_level_analysis', 'manual', 'estimated'
);

CREATE INDEX idx_roofs_gebaeudeeinheit ON building_roofs(gebaeudeeinheit);
CREATE INDEX idx_roofs_egid ON building_roofs(egid);
```

### 1.3 Neue Tabelle `building_walls` (nur on-demand)

```sql
-- Nur für komplexe Gebäude befüllt (on-demand)
CREATE TABLE building_walls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gebaeudeeinheit TEXT NOT NULL,
    egid TEXT,

    -- Höhen
    z_min REAL,                 -- Geländepunkt
    z_max REAL,                 -- Traufhöhe

    -- 3D-Geometrie
    geometry_wkb BLOB,          -- 3D MultiPolygon als WKB

    -- Metadaten
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_walls_gebaeudeeinheit ON building_walls(gebaeudeeinheit);
CREATE INDEX idx_walls_egid ON building_walls(egid);
```

### 1.4 Neue Tabelle `building_floors` (nur on-demand)

> **Analyse (11.01.2026):** Floor ≈ Building_solid (Median +0.02% Unterschied).
> Für EINFACHE Gebäude reicht Building_solid Polygon.
> Für KOMPLEXE Gebäude wird Floor on-demand geladen (exakte Fassadenposition).

```sql
-- Nur für komplexe Gebäude befüllt (on-demand)
CREATE TABLE building_floors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gebaeudeeinheit TEXT NOT NULL,
    egid TEXT,

    -- Höhe
    gelaendepunkt REAL,         -- Terrainhöhe

    -- 3D-Geometrie (2.5D - alle Z gleich)
    geometry_wkb BLOB,          -- MultiPolygon als WKB

    -- Metadaten
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_floors_gebaeudeeinheit ON building_floors(gebaeudeeinheit);
CREATE INDEX idx_floors_egid ON building_floors(egid);
```

---

## Phase 2: Batch-Import (Building_solid + Roof_solid)

### 2.1 Erweitertes Parsing

```python
# tile_prefetch.py - Erweiterung

def _parse_all_buildings_from_gdb(gdb_path: str, tile_id: str) -> tuple[list, list]:
    """
    Parse Building_solid UND Roof_solid aus GDB.

    Returns:
        (buildings, roofs) - Zwei Listen für Bulk-Insert
    """

    buildings = []
    roofs = []

    # 1. Building_solid parsen (wie bisher + neue Attribute)
    with fiona.open(gdb_path, layer='Building_solid') as src:
        for feature in src:
            props = feature['properties']
            geom = shape(feature['geometry'])

            buildings.append({
                'egid': props.get('EGID'),
                'polygon': list(geom.exterior.coords),
                'traufhoehe_m': ...,
                'firsthoehe_m': ...,
                # NEU:
                'objektart': props.get('OBJEKTART'),
                'name_komplett': props.get('NAME_KOMPLETT'),
                'gebaeude_nutzung': props.get('GEBAEUDE_NUTZUNG'),
                'gebaeudeeinheit': props.get('GEBAEUDEEINHEIT'),
            })

    # 2. Roof_solid parsen (für Dachform-Berechnung)
    with fiona.open(gdb_path, layer='Roof_solid') as src:
        for feature in src:
            props = feature['properties']
            geom = shape(feature['geometry'])

            # Z-Levels extrahieren
            z_values = extract_z_from_geometry(geom)

            # Dachform berechnen
            roof_form, confidence, angle, orientation = calculate_roof_form(z_values, geom)

            roofs.append({
                'gebaeudeeinheit': props.get('GEBAEUDEEINHEIT'),
                'egid': props.get('EGID'),
                'dach_min': props.get('DACH_MIN'),
                'dach_max': props.get('DACH_MAX'),
                'roof_form': roof_form,
                'roof_form_confidence': confidence,
                'roof_angle_deg': angle,
                'roof_orientation': orientation,
                'z_levels': json.dumps(sorted(set(z_values))),
                # KEINE Geometrie speichern (zu gross)
                'geometry_wkb': None,
                'has_full_geometry': 0,
            })

    return buildings, roofs
```

### 2.2 Dachform-Erkennung aus Z-Levels

```python
# roof_form_detector.py - NEU

import math
from typing import Tuple, List
from collections import Counter

def calculate_roof_form(z_values: List[float], geometry) -> Tuple[str, float, float, str]:
    """
    Erkennt Dachform aus 3D-Geometrie.

    Returns:
        (roof_form, confidence, angle_deg, orientation)
    """

    if not z_values or len(z_values) < 3:
        return 'unbekannt', 0.0, 0.0, None

    z_min = min(z_values)
    z_max = max(z_values)
    z_range = z_max - z_min

    # 1. Flachdach: Alle Z-Werte nahezu gleich
    if z_range < 0.5:
        return 'flachdach', 0.95, 0.0, None

    # 2. Z-Level-Verteilung analysieren
    z_rounded = [round(z, 1) for z in z_values]
    z_distribution = Counter(z_rounded)
    unique_levels = len(z_distribution)

    # Punkte bei Min und Max Z
    min_z_points = [p for p in get_points(geometry) if p[2] < z_min + 0.5]
    max_z_points = [p for p in get_points(geometry) if p[2] > z_max - 0.5]

    # Zentren berechnen
    min_center = centroid_2d(min_z_points)
    max_center = centroid_2d(max_z_points)

    # Horizontale Distanz
    horiz_dist = math.sqrt(
        (max_center[0] - min_center[0])**2 +
        (max_center[1] - min_center[1])**2
    )

    # Dachneigung berechnen
    if horiz_dist > 0.1:
        angle_deg = math.degrees(math.atan(z_range / horiz_dist))
    else:
        angle_deg = 90.0  # Spitzer Turm

    # First-Orientierung
    orientation = calculate_orientation(min_center, max_center)

    # 3. Dachform erkennen
    # Satteldach: 2-4 Z-Levels, lineare Verteilung
    if 2 <= unique_levels <= 4 and 15 < angle_deg < 50:
        # Prüfen ob First linear ist
        if is_linear_ridge(max_z_points):
            return 'satteldach', 0.85, angle_deg, orientation

    # Pultdach: Asymmetrische Verteilung
    if unique_levels == 2 and 5 < angle_deg < 30:
        return 'pultdach', 0.80, angle_deg, orientation

    # Walmdach: First kürzer als Traufe, 4 geneigte Flächen
    if 3 <= unique_levels <= 5 and 15 < angle_deg < 45:
        if is_hipped_roof(min_z_points, max_z_points):
            return 'walmdach', 0.75, angle_deg, orientation

    # Zeltdach: Zentrale Spitze
    if unique_levels >= 3 and len(max_z_points) <= 4:
        if is_pyramid_roof(geometry, max_z_points):
            return 'zeltdach', 0.70, angle_deg, None

    # Mansarddach: Gebrochene Neigung (2 Winkel)
    if unique_levels >= 4:
        angles = detect_multiple_angles(z_values, geometry)
        if len(angles) >= 2 and angles[0] > angles[1] + 15:
            return 'mansarddach', 0.65, angles[0], orientation

    # Fallback: Komplex
    return 'komplex', 0.50, angle_deg, orientation


def calculate_orientation(p1: Tuple[float, float], p2: Tuple[float, float]) -> str:
    """Berechnet First-Orientierung als Himmelsrichtung."""

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    # Azimut in Grad (0° = Nord, 90° = Ost)
    azimuth = math.degrees(math.atan2(dx, dy)) % 360

    # In Himmelsrichtung konvertieren
    if 337.5 <= azimuth or azimuth < 22.5:
        return 'N-S'
    elif 22.5 <= azimuth < 67.5:
        return 'NO-SW'
    elif 67.5 <= azimuth < 112.5:
        return 'O-W'
    elif 112.5 <= azimuth < 157.5:
        return 'SO-NW'
    elif 157.5 <= azimuth < 202.5:
        return 'N-S'
    elif 202.5 <= azimuth < 247.5:
        return 'SW-NO'
    elif 247.5 <= azimuth < 292.5:
        return 'O-W'
    else:
        return 'NW-SO'
```

### 2.3 Erweiterter Import-Befehl

```bash
# Region Bern importieren mit Roof-Daten
python scripts/import_tiles.py --region bern --include-roofs

# Optionen:
#   --include-roofs     Roof_solid parsen und Dachform berechnen
#   --skip-existing     Nur neue Tiles importieren
#   --workers 4         Anzahl parallele Worker
```

---

## Phase 3: On-Demand Layer-Fetch

### 3.1 Trigger: Komplexes Gebäude im Projekt

```python
# layer_fetcher.py - NEU

async def fetch_3d_layers_for_building(egid: str, gebaeudeeinheit: str) -> bool:
    """
    Lädt Floor, Wall und Roof_solid für ein spezifisches Gebäude.

    Wird aufgerufen wenn:
    1. Gebäude zu Projekt hinzugefügt wird
    2. Gebäude als MODERATE/COMPLEX klassifiziert ist
    3. User explizit "3D-Daten laden" klickt
    """

    # 1. Prüfen ob bereits geladen
    if has_3d_layers(egid):
        return True

    # 2. Koordinaten aus buildings holen
    building = get_building_by_egid(egid)
    if not building:
        return False

    # 3. Tile downloaden (temporär)
    tile_path = await download_tile_for_coordinates(
        building['center_e'],
        building['center_n']
    )

    try:
        # 4. Layer parsen mit GEBAEUDEEINHEIT-Filter
        # ALLE 3 Layer für komplexe Gebäude
        await parse_layers_for_building(
            tile_path,
            gebaeudeeinheit,
            layers=['Floor', 'Wall', 'Roof_solid']
        )

        # 5. Flag setzen
        update_building(egid, has_3d_layers=1)

        return True

    finally:
        # 6. Tile LÖSCHEN (Speicher sparen)
        delete_tile(tile_path)
```

### 3.2 Selektives Layer-Parsing

```python
# layer_fetcher.py

async def parse_layers_for_building(
    gdb_path: str,
    target_gebaeudeeinheit: str,
    layers: List[str]
) -> dict:
    """
    Parsed nur die Features mit passender GEBAEUDEEINHEIT.

    Viel schneller als komplettes Tile zu parsen!
    """

    result = {'floors': [], 'walls': [], 'roofs': []}

    for layer_name in layers:
        with fiona.open(gdb_path, layer=layer_name) as src:
            for feature in src:
                props = feature['properties']

                # Nur Features für DIESES Gebäude
                if props.get('GEBAEUDEEINHEIT') != target_gebaeudeeinheit:
                    continue

                geom = shape(feature['geometry'])

                if layer_name == 'Floor':
                    result['floors'].append({
                        'gebaeudeeinheit': target_gebaeudeeinheit,
                        'egid': props.get('EGID'),
                        'gelaendepunkt': props.get('GELAENDEPUNKT'),
                        'geometry_wkb': geom.wkb,
                    })

                elif layer_name == 'Wall':
                    result['walls'].append({
                        'gebaeudeeinheit': target_gebaeudeeinheit,
                        'egid': props.get('EGID'),
                        'z_min': props.get('GELAENDEPUNKT'),
                        'z_max': props.get('DACH_MIN'),
                        'geometry_wkb': geom.wkb,
                    })

                elif layer_name == 'Roof_solid':
                    # Geometrie speichern (für 3D-Visualisierung)
                    result['roofs'].append({
                        'gebaeudeeinheit': target_gebaeudeeinheit,
                        'egid': props.get('EGID'),
                        'geometry_wkb': geom.wkb,
                        'has_full_geometry': 1,
                    })

    # In DB speichern
    save_floors(result['floors'])
    save_walls(result['walls'])
    update_roofs_with_geometry(result['roofs'])

    return result
```

---

## Phase 4: API-Endpunkte

### 4.1 3D-Layer Abrufen

```python
# Neue Endpunkte in main.py

@app.get("/api/v1/building/{egid}/3d-layers")
async def get_building_3d_layers(egid: str):
    """
    Gibt alle 3D-Layer für ein Gebäude zurück.

    Für EINFACHE Gebäude: polygon aus buildings Tabelle
    Für KOMPLEXE Gebäude: floor, walls, roof mit 3D-Geometrie

    Response:
    {
        "egid": "1230337",
        "has_3d_layers": true,
        "polygon": [[2600951.6, 1199554.9], ...],  // Aus buildings Tabelle (immer)
        "floor": { "gelaendepunkt": 533.5, "geometry_wkt": "..." },  // Nur wenn on-demand geladen
        "walls": [{ "z_min": 533.5, "z_max": 561.5, "geometry_wkt": "..." }],
        "roof": {
            "dach_min": 561.5,
            "dach_max": 633.8,
            "roof_form": "satteldach",
            "roof_angle_deg": 30.7,
            "geometry_wkt": "MULTIPOLYGON..."
        }
    }
    """
    pass


@app.post("/api/v1/building/{egid}/load-3d-layers")
async def load_building_3d_layers(egid: str):
    """
    Lädt 3D-Layer on-demand für komplexes Gebäude.

    Triggert: Tile-Download → Parse → Save → Delete Tile
    """
    pass
```

### 4.2 Dachform-Statistiken

```python
@app.get("/api/v1/stats/roof-forms")
async def get_roof_form_stats():
    """
    Statistik über erkannte Dachformen.

    Response:
    {
        "total": 7197,
        "forms": {
            "satteldach": 4521,
            "flachdach": 1823,
            "walmdach": 412,
            ...
        },
        "avg_confidence": 0.78
    }
    """
    pass
```

---

## Phase 5: Datenfluss im Projekt

```
┌─────────────────────────────────────────────────────────────────┐
│              DATENFLUSS: GEBÄUDE IM PROJEKT                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User sucht Adresse                                          │
│     └─ SmartBuildingService.collect_all_data()                 │
│         ├─ buildings Tabelle (Pre-Import)                      │
│         │   └─ Polygon + Höhen + objektart + roof_form         │
│         │                                                       │
│         └─ building_roofs Tabelle (Pre-Import)                 │
│             └─ Berechnete Dachform + Neigung                   │
│                                                                 │
│  2. User fügt Gebäude zu Projekt hinzu                          │
│     └─ Komplexität prüfen (objektart, roof_form)               │
│         │                                                       │
│         ├─ SIMPLE: Fertig (Building_solid Polygon reicht)      │
│         │                                                       │
│         └─ MODERATE/COMPLEX:                                    │
│             └─ fetch_3d_layers_for_building()                  │
│                 ├─ Tile downloaden (temporär)                  │
│                 ├─ Floor, Wall, Roof_solid parsen              │
│                 ├─ In DB speichern                             │
│                 ├─ has_3d_layers = 1 setzen                    │
│                 └─ Tile LÖSCHEN                                │
│                                                                 │
│  3. 3D-Viewer zeigt Gebäude                                     │
│     └─ GET /api/v1/building/{egid}/3d-layers                   │
│         ├─ Polygon aus buildings (immer)                       │
│         ├─ Floor-Geometrie (nur komplexe)                      │
│         ├─ Wall-Geometrie (nur komplexe)                       │
│         └─ Roof-Geometrie (nur komplexe)                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Speicher-Schätzung

### Pre-Import (Region Bern, ~20 Tiles)

| Tabelle | Datenmenge | Speicher |
|---------|------------|----------|
| buildings | ~7000 Gebäude × 0.5KB | ~3.5 MB |
| building_roofs (ohne Geometrie) | ~7000 × 0.2KB | ~1.4 MB |
| **Total** | | **~5 MB pro Tile** |
| **20 Tiles** | | **~100 MB** |

### On-Demand (pro komplexes Gebäude)

| Tabelle | Datenmenge | Speicher |
|---------|------------|----------|
| building_floors (1 Gebäude) | ~10KB | ~10 KB |
| building_walls (1 Gebäude) | ~50KB | ~50 KB |
| building_roofs + Geometrie | ~30KB | ~30 KB |
| **Total pro Gebäude** | | **~90 KB** |

> **Hinweis Floor:** Für EINFACHE Gebäude reicht Building_solid Polygon (Median +0.02% Unterschied).
> Für KOMPLEXE Gebäude wird Floor zusätzlich geladen für exakte Fassadenposition.

### Vergleich: Alt vs. Neu

| Szenario | Alt (Tiles behalten) | Neu (Hybrid) |
|----------|---------------------|--------------|
| 20 Tiles Region Bern | ~2 GB (GDB-Dateien) | ~100 MB (DB) |
| 100 komplexe Gebäude | - | ~9 MB zusätzlich |
| **Railway Volume** | Zu gross! | **Passt** |

---

## Implementierungs-Reihenfolge

### Schritt 1: DB-Schema (30 min)
- [ ] Migration-Script für neue Spalten
- [ ] Neue Tabellen erstellen
- [ ] Indizes anlegen

### Schritt 2: Batch-Import erweitern (2h)
- [ ] Building_solid: Neue Attribute extrahieren
- [ ] Roof_solid: Z-Levels extrahieren
- [ ] Dachform-Erkennung implementieren
- [ ] Bulk-Insert für beide Tabellen

### Schritt 3: Test-Import (1h)
- [ ] 1 Tile importieren (Bern Zentrum)
- [ ] Dachform-Statistiken prüfen
- [ ] Bekannte Gebäude validieren (Münster, Bundeshaus)

### Schritt 4: On-Demand Fetch (2h)
- [ ] layer_fetcher.py erstellen
- [ ] Selektives Parsing mit GEBAEUDEEINHEIT
- [ ] Tile-Cleanup nach Import

### Schritt 5: API + Frontend (2h)
- [ ] Endpunkte für 3D-Layer
- [ ] 3D-Viewer Integration
- [ ] Test mit Pilotgebäuden

---

## Pilotgebäude für Tests

| Gebäude | EGID | Erwartete Dachform | Komplexität |
|---------|------|-------------------|-------------|
| Berner Münster | 1230337 | Satteldach (~30°) | COMPLEX (Turm!) |
| Bundeshaus | 2242547 | Komplex (Kuppel) | COMPLEX |
| St. Peter & Paul | 191821074 | Satteldach + Türme | COMPLEX |
| Knospenweg 4 | 1243790 | Satteldach (~25°) | SIMPLE |
| Zytglogge | 1017961 | Walmdach + Turm | COMPLEX |

---

## Offene Fragen

1. **Wie viele komplexe Gebäude erwarten wir pro Projekt?**
   - Wenn viele: On-Demand könnte langsam sein
   - Alternative: Batch-Load für ganze Projekte

2. **Sollen wir Roof_solid-Geometrie IMMER speichern?**
   - Pro: 3D-Visualisierung für alle
   - Contra: ~30x mehr Speicher

3. **DuckDB statt SQLite?**
   - Für Batch-Import: Ja, ~5x schneller
   - Für Queries: SQLite reicht
   - Entscheidung: Später bei Bedarf

---

## Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 11.01.2026 | 1.0 | Initiales Design |
