# Koordinatenbasierte Architektur (Spatial Index)

**Stand: 15.01.2026 20:15**

## Überblick

Dieses Dokument beschreibt die geplante Architektur für koordinatenbasierte Datenverarbeitung
mit Spatial Index. Ziel: **Exakte 3D-Daten** als Single-Source-of-Truth für alle Komponenten.

## Aktueller Datenfluss (nach BUG-024)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SINGLE-SOURCE-OF-TRUTH                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  swissBUILDINGS3D (GDB-Tiles)                                  │
│       │                                                         │
│       ▼                                                         │
│  Backend DB (DuckDB)                                           │
│  ├── buildings_3d      (Polygon, Höhen, Zentrum)               │
│  ├── building_walls    (3D-Geometrie, z_min/z_max)             │
│  └── building_roofs    (Dach-Geometrie, dach_min/dach_max)     │
│       │                                                         │
│       ▼                                                         │
│  SSE-Stream (geruestbau API)                                   │
│  └── building_walls[], selected_facades[], neighbors[], ...    │
│       │                                                         │
│       ▼                                                         │
│  Frontend (React)                                              │
│  └── Koordinaten-Matching, 3D-Visualisierung, Gerüst-Logik    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Prinzip:** Rohe 3D-Daten fliessen unverändert vom Backend ans Frontend.
Das Frontend übernimmt die Matching-Logik (koordinatenbasiert, nicht richtungsbasiert).

## Komponenten-Analyse (TODO)

Für jede Komponente muss analysiert werden:
- Wie werden Koordinaten aktuell verwendet?
- Wo sind Altlasten (richtungsbasierte Logik)?
- Was muss für exakte Daten geändert werden?

### 1. Building Walls (✅ Implementiert - BUG-024)

| Aspekt | Status | Details |
|--------|--------|---------|
| DB-Speicherung | ✅ | `building_walls` mit `geometry_wkb`, `z_min`, `z_max` |
| API-Response | ✅ | `building_walls[]` mit `coords_3d` (volle 3D-Geometrie) |
| Frontend-Matching | ✅ | `matchFacadeToWall()` - koordinatenbasiert |
| Altlasten | ⚠️ | `wall_facade_matcher.py` - DEPRECATED, noch vorhanden |

### 2. Neighbors (Nachbar-Gebäude)

| Aspekt | Status | Details |
|--------|--------|---------|
| DB-Speicherung | ⚠️ | Nur `center_e`, `center_n` - kein Polygon-Index |
| API-Response | ✅ | `/building/{egid}/neighbors` mit Polygonen |
| Frontend-Logik | ⚠️ | Radius-Slider, aber zentrumsbasiert |
| Für Blocking | ⚠️ | Verwendet `BLOCKING_THRESHOLD_M = 2.0m` |

**TODO:** Koordinatenbasierte Nachbar-Suche mit Polygon-Überlappung statt Zentrum-Distanz.

### 3. Blockierte Fassaden

| Aspekt | Status | Details |
|--------|--------|---------|
| Backend-Berechnung | ⚠️ | Richtungsbasiert (N, S, E, W) |
| Frontend-Anzeige | ✅ | Grau dargestellt, nicht auswählbar |
| Genauigkeit | ⚠️ | Himmelsrichtung reicht nicht für L-förmige Gebäude |

**TODO:** Koordinatenbasierte Blockierung - prüfe ob Fassaden-Segment durch Nachbar-Polygon überlappt wird.

### 4. Dach (3D-Geometrie)

| Aspekt | Status | Details |
|--------|--------|---------|
| DB-Speicherung | ✅ | `building_roofs` mit `geometry_wkb`, `dach_min`, `dach_max` |
| API-Response | ⚠️ | `roof_geometry_coords` nur teilweise genutzt |
| 3D-Visualisierung | ⚠️ | Fallback-Heuristik statt echte Geometrie |
| Dach-Orientierung | ⚠️ | Inkonsistent bei Reihenhäusern (BUG-016) |

**TODO:** Echte 3D-Dach-Geometrie aus `building_roofs` im 3D-Viewer verwenden.

### 5. Multi-Building (Mehrere Gebäude als Projekt)

| Aspekt | Status | Details |
|--------|--------|---------|
| Projekt-Speicherung | ✅ | `buildings[]` Array in `geruestbau.db` |
| API-Response | ✅ | `additionalBuildings[]` in SSE |
| 2D-Darstellung | ✅ | Alle Polygone in FacadePanel |
| 3D-Darstellung | ⚠️ | Nur Haupt-Gebäude hat volle Details |

**TODO:** Alle Projekt-Gebäude mit vollständigen 3D-Daten (Walls, Roofs) laden.

### 6. Umgebung (Terrain, Strassen)

| Aspekt | Status | Details |
|--------|--------|---------|
| Terrain-Höhen | ✅ | swissALTI3D via API |
| Terrain-Profil | ✅ | Polygon-Ecken-Sampling |
| Strassen | ❌ | Nicht implementiert |
| 2D-Darstellung | ⚠️ | Nur Gebäude-Polygone |
| 3D-Darstellung | ⚠️ | Terrain als flache Ebene |

**TODO:** Strassen-Layer für Zugangs-Planung. Terrain mit echtem Relief im 3D-Viewer.

### 7. Gerüst-Aspekte (Scaffolding)

| Aspekt | Status | Details |
|--------|--------|---------|
| Fassaden-Länge | ✅ | Exakt aus Polygon-Koordinaten |
| Fassaden-Höhe | ✅ | Aus `building_walls.z_min/z_max` (BUG-024) |
| Terrain-Ausgleich | ✅ | `terrain_diff_m` für Stellspindeln |
| Feld-Aufteilung | ✅ | Layher Blitz 2.57m / 3.07m |
| Ständer-Positionen | ✅ | Koordinatenbasiert entlang Fassade |
| Verankerungen | ⚠️ | Alle 4m, aber ohne Hindernis-Check |

**TODO:** Hindernis-Erkennung für Verankerungen (Fenster, Balkone aus Photo-Analyse).

## Spatial Index Strategie

### Option A: DuckDB Spatial Extension (empfohlen)

```sql
-- Spatial Extension laden
INSTALL spatial; LOAD spatial;

-- Geometrie-Spalte hinzufügen
ALTER TABLE building_walls ADD COLUMN geom GEOMETRY;
UPDATE building_walls SET geom = ST_GeomFromWKB(geometry_wkb);

-- R-Tree Index erstellen
CREATE INDEX idx_walls_geom ON building_walls USING RTREE(geom);

-- Nachbar-Suche mit Spatial Query
SELECT * FROM buildings_3d
WHERE ST_DWithin(polygon_geom, ST_Point(E, N), radius_m);
```

### Option B: SpatiaLite (SQLite + Spatial)

Ähnlich wie Option A, aber für SQLite-basierte DBs (building_contexts.db).

### Vorteile von Spatial Index

| Feature | Ohne Index | Mit R-Tree Index |
|---------|------------|------------------|
| Nachbar-Suche | O(n) - alle prüfen | O(log n) |
| Polygon-Überlappung | Manuell berechnen | ST_Intersects() |
| Distanz-Berechnung | Zentrum-zu-Zentrum | Polygon-zu-Polygon |

## Implementierungs-Reihenfolge

1. **Phase 1: Altlasten entfernen** (aktuell)
   - [x] BUG-024: building_walls koordinatenbasiert
   - [ ] `wall_facade_matcher.py` entfernen
   - [ ] Alte `facadeZMin/facadeZMax` Props entfernen

2. **Phase 2: Neighbors koordinatenbasiert**
   - [ ] Polygon-basierte Nachbar-Suche
   - [ ] Blockierte Fassaden per Koordinaten-Überlappung
   - [ ] `blockedSides[]` (richtungsbasiert) durch `blockedSegments[]` ersetzen

3. **Phase 3: 3D-Dach-Geometrie**
   - [ ] Echte Dach-Polygone aus `building_roofs` laden
   - [ ] 3D-Viewer: Dach aus Koordinaten rendern
   - [ ] BUG-016 (Dach-Orientierung) durch echte Geometrie lösen

4. **Phase 4: Spatial Index** (optional)
   - [ ] DuckDB Spatial Extension evaluieren
   - [ ] Performance-Tests mit grossen Tile-Mengen
   - [ ] Migration bestehender Daten

## Referenzen

- BUG-024: Wall-Layer koordinatenbasiert (implementiert)
- BUG-016: Dach-Orientierung inkonsistent (offen)
- BUG-022: Blockierte Fassaden-Schwellenwert (gefixt)
- BUG-023: TerrainProfile Höhenberechnung (gefixt)
