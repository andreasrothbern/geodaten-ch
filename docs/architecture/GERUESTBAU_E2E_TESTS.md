# Gerüstbau-App E2E Tests

## Übersicht

Diese Dokumentation beschreibt die End-to-End Tests für die Gerüstbau-App.
Die Tests validieren den vollständigen Workflow von Projekt-Erstellung bis 3D-Visualisierung.

**Test-Datei:** `backend/tests/test_geruestbau_e2e.py`

---

## Test-Ergebnisse (Stand: 04.01.2026)

```
┌───────────────────────────────────────────────────────────────────┐
│                     TEST-ERGEBNISSE                               │
├───────────────────────────────────────────────────────────────────┤
│  TestPolygonSimplification          ✅ 6/6 bestanden              │
│  TestNeighborsAndFacadeBlocking     ✅ 6/6 bestanden              │
│  TestTerrainAndSlope                ✅ 3/3 bestanden              │
│  TestCacheConsistency               ✅ 3/3 bestanden              │
│  TestPerformance                    ⚠️ 2/3 (1 Performance-Issue)  │
├───────────────────────────────────────────────────────────────────┤
│  GESAMT: 20 bestanden, 1 fehlgeschlagen                           │
└───────────────────────────────────────────────────────────────────┘
```

### Bekannte Issues

| Test | Issue | Ursache | Workaround |
|------|-------|---------|------------|
| `test_facade_loading_under_5s` | 185s statt <5s | STAC-Tile Download beim ersten Aufruf | Cache vorher befüllen |

### Ausführung

```bash
# Alle E2E Tests
cd backend
python -m pytest tests/test_geruestbau_e2e.py -v

# Schnelle Tests (ohne API-abhängige)
python -m pytest tests/test_geruestbau_e2e.py::TestPolygonSimplification \
                 tests/test_geruestbau_e2e.py::TestNeighborsAndFacadeBlocking \
                 tests/test_geruestbau_e2e.py::TestTerrainAndSlope \
                 tests/test_geruestbau_e2e.py::TestCacheConsistency -v
```

---

## Test-Architektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GERÜSTBAU E2E TESTS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │ TestProject      │    │ TestMultiAddress │    │ TestPolygon      │      │
│  │ Creation         │    │ Resolution       │    │ Simplification   │      │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘      │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │ TestFacade       │    │ TestNeighbors    │    │ Test3DView       │      │
│  │ Selection        │    │ AndBlocking      │    │ DataFlow         │      │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘      │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │ TestTerrain      │    │ TestBuilding     │    │ TestScaffold     │      │
│  │ AndSlope         │    │ Zones            │    │ Configuration    │      │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘      │
│           │                       │                       │                 │
│           └───────────────────────┼───────────────────────┘                 │
│                                   ▼                                         │
│                      ┌──────────────────────────┐                           │
│                      │ TestCacheConsistency     │                           │
│                      │ TestAPIIntegration       │                           │
│                      │ TestPerformance          │                           │
│                      └──────────────────────────┘                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API-Endpunkte und Datenfluss

### Vollständiger Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATENFLUSS: Projekt erstellen                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Adresse eingeben                                                        │
│     │                                                                       │
│     ▼                                                                       │
│  GET /api/v1/geruestbau/address/resolve?address=Knospenweg 2-10            │
│     │                                                                       │
│     ├─► parsed: {street, city, numbers: ["2","4","6","8","10"]}            │
│     └─► buildings: [{egid, address, polygon?, heights?}, ...]              │
│                                                                             │
│  2. Fassaden laden                                                          │
│     │                                                                       │
│     ▼                                                                       │
│  GET /api/v1/geruestbau/configurator/facades?address=...&simplify_epsilon= │
│     │                                                                       │
│     ├─► building: {egid, polygon, trauf_height_m, first_height_m}          │
│     ├─► selected_facades: [{direction, length_m, height_m}, ...]           │
│     └─► metadata: {facade_count, perimeter_m, area_m2}                     │
│                                                                             │
│  3. Nachbarn laden (für blockierte Fassaden)                               │
│     │                                                                       │
│     ▼                                                                       │
│  GET /api/v1/geruestbau/building/{egid}/neighbors?radius_m=10              │
│     │                                                                       │
│     ├─► neighbors: [{egid, distance_m, direction, polygon?}, ...]          │
│     └─► blocked_sides: ["E", "W"]  (bei Reihenhaus)                        │
│                                                                             │
│  4. Projekt erstellen                                                       │
│     │                                                                       │
│     ▼                                                                       │
│  POST /api/v1/geruestbau/projects                                          │
│     │                                                                       │
│     └─► {id, name, address, status: "draft", egid}                         │
│                                                                             │
│  5. Terrain-Daten enrichen                                                  │
│     │                                                                       │
│     ▼                                                                       │
│  POST /api/v1/geruestbau/projects/{id}/enrich                              │
│     │                                                                       │
│     └─► terrain: {height_m, slope_m, slope_class}                          │
│                                                                             │
│  6. 3D-Ansicht                                                              │
│     │                                                                       │
│     ▼                                                                       │
│  GET /api/v1/geruestbau/projects/{id}                                      │
│  GET /api/v1/geruestbau/building/{egid}/neighbors?include_polygons=true    │
│     │                                                                       │
│     └─► Three.js rendert Gebäude + Nachbarn + Gerüst                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Test-Kategorien

### 1. Projekt-Erstellung (`TestProjectCreation`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_create_project_single_address` | Projekt mit Einzeladresse | `POST /projects` | Projekt wird erstellt mit Status "draft" |
| `test_get_project_with_geodata` | Projekt mit Geodaten laden | `GET /projects/{id}` | Geodata (Polygon, Höhen) enthalten |
| `test_list_projects_with_filter` | Projekte filtern | `GET /projects?status=` | Nur passende Status zurückgeben |
| `test_update_project` | Projekt aktualisieren | `PUT /projects/{id}` | Name/Status geändert |
| `test_delete_project` | Projekt löschen | `DELETE /projects/{id}` | Nicht mehr abrufbar |

**Validierte Daten:**
- `id` - UUID generiert
- `name`, `address` - wie übergeben
- `status` - "draft" initial
- `created_at`, `updated_at` - Timestamps gesetzt

---

### 2. Multi-Adresse (`TestMultiAddressResolution`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_parse_address_range` | Adressbereich parsen | `GET /address/resolve` | Parsed enthält numbers Array |
| `test_address_range_contains_all_buildings` | Alle Gebäude gefunden | `GET /address/resolve` | building_count >= 1 |
| `test_single_address_resolution` | Einzeladresse | `GET /address/resolve` | building_count == 1 |

**Test-Adressen:**

| Adresse | Typ | Erwartete Gebäude |
|---------|-----|-------------------|
| "Knospenweg 2-10, 3006 Bern" | Range | 5 (2, 4, 6, 8, 10) |
| "Kramgasse 27/29, 3011 Bern" | Explicit | 2 |
| "Kramgasse 49, 3011 Bern" | Single | 1 |

**Response-Struktur:**
```json
{
  "parsed": {
    "street": "Knospenweg",
    "city": "Bern",
    "numbers": ["2", "4", "6", "8", "10"],
    "range_type": "range"
  },
  "buildings": [
    {"egid": "1243788", "address": "Knospenweg 2, 3006 Bern", ...},
    {"egid": "1243790", "address": "Knospenweg 4, 3006 Bern", ...},
    ...
  ],
  "building_count": 5
}
```

---

### 3. Polygon-Vereinfachung (`TestPolygonSimplification`)

| Test | Beschreibung | Parameter | Erwartetes Verhalten |
|------|--------------|-----------|---------------------|
| `test_simplify_with_default_epsilon` | Dynamisches Epsilon | `epsilon=None` | Epsilon automatisch gewählt |
| `test_simplify_with_small_epsilon` | Feine Vereinfachung | `epsilon=0.3` | Viele Punkte erhalten |
| `test_simplify_with_large_epsilon` | Grobe Vereinfachung | `epsilon=2.0` | Wenig Punkte, Details entfernt |
| `test_simplification_preserves_area` | Fläche bleibt | - | Abweichung < 10% |
| `test_simplification_calculates_sides` | Fassaden berechnet | - | Seiten mit Richtung |
| `test_dynamic_epsilon_scales_with_size` | Epsilon nach Grösse | - | Gross → grösseres Epsilon |

**Epsilon-Auswirkung:**

| Epsilon (m) | Toleranz (°) | Effekt |
|-------------|-------------|--------|
| 0.3 | 5.0° | Minimal - Details bleiben |
| 0.5 | 8.0° | Standard |
| 1.0 | 12.0° | Moderat |
| 2.0 | 20.0° | Stark |
| 3.0 | 30.0° | Aggressiv |

**Dynamisches Epsilon:**

| Umfang | Epsilon |
|--------|---------|
| < 50m (EFH) | 0.3m |
| 50-200m (MFH) | 0.8m |
| > 200m (Gross) | 1.5m |

---

### 4. Fassaden-Selektion (`TestFacadeSelection`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_get_facades_for_address` | Fassaden laden | `GET /configurator/facades` | Gebäude + Fassaden + Metadata |
| `test_facades_have_compass_directions` | Richtungen korrekt | - | N, NE, E, SE, S, SW, W, NW |
| `test_facades_with_simplify_epsilon` | Epsilon-Auswirkung | `simplify_epsilon=` | Mehr/weniger Fassaden |
| `test_facade_heights_match_building` | Höhen plausibel | - | 2-100m |

**Fassaden-Response:**
```json
{
  "building": {
    "egid": "1234567",
    "polygon": [[e, n], ...],
    "trauf_height_m": 8.5,
    "first_height_m": 12.0
  },
  "selected_facades": [
    {
      "id": "facade_0",
      "direction": "N",
      "length_m": 10.5,
      "height_m": 8.5,
      "start_point": [e, n],
      "end_point": [e, n]
    },
    ...
  ],
  "metadata": {
    "facade_count": 4,
    "perimeter_m": 42.0,
    "area_m2": 105.0
  }
}
```

**Richtungsberechnung:**
```
Azimut = atan2(dx, dy) → Grad
Normal = (Azimut + 90°) % 360°
Direction = azimuth_to_direction(Normal)
```

---

### 5. Nachbar-Berechnung und Fassaden-Blockierung (`TestNeighborsAndFacadeBlocking`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_get_neighbors_for_rowhouse` | Nachbarn finden | `GET /building/{egid}/neighbors` | Nachbarn mit Distanz |
| `test_blocked_sides_for_adjacent_buildings` | Blockierte Seiten | - | blocked_sides Array |
| `test_neighbors_with_different_radii` | Radius-Auswirkung | `radius_m=0,5,10` | Mehr Nachbarn bei grösserem Radius |
| `test_neighbor_direction_calculation` | Richtung korrekt | - | Gültige Kompass-Richtung |
| `test_neighbor_distance_calculation` | Distanz korrekt | - | >= 0, <= radius_m |
| `test_neighbor_polygons_included` | Polygone enthalten | `include_polygons=true` | Min. 3 Punkte pro Polygon |

**Blockierungs-Logik:**
```python
for neighbor in neighbors:
    if distance_m < 0.5:  # Direkt angrenzend
        blocked_sides.append(neighbor.direction)
```

**Test-Daten (Knospenweg):**

| EGID | Adresse | Position | Erwartete Blockierung |
|------|---------|----------|----------------------|
| 1243788 | Knospenweg 2 | Endhaus links | E blockiert |
| 1243790 | Knospenweg 4 | Mitte | E + W blockiert |
| 1243791 | Knospenweg 6 | Mitte | E + W blockiert |
| 1243792 | Knospenweg 8 | Mitte | E + W blockiert |
| 1243793 | Knospenweg 10 | Endhaus rechts | W blockiert |

---

### 6. 3D-View Datenfluss (`TestThreeDViewDataFlow`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_smart_building_data_for_3d` | 3D-Daten vorhanden | SmartBuildingService | Polygon + Höhen |
| `test_3d_data_contains_heights` | Höhen enthalten | `GET /smart-building/data` | trauf/first/gesamt |
| `test_neighbors_for_3d_scene` | Nachbarn für Szene | `GET /building/{egid}/neighbors` | Polygone für Rendering |

**3D-Rendering Anforderungen:**

| Daten | Verwendung | Pflicht |
|-------|-----------|---------|
| `polygon` | Grundriss-Mesh | Ja |
| `traufhoehe_m` | Wand-Höhe | Ja |
| `firsthoehe_m` | Dach-Spitze | Nein |
| `roof_type` | Dachform | Nein |
| `neighbors[].polygon` | Nachbar-Gebäude | Nein |

---

### 7. Terrain und Hanglage (`TestTerrainAndSlope`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_terrain_data_loaded` | Terrain geladen | SmartBuildingService | height_m vorhanden |
| `test_project_enrichment_adds_terrain` | Enrichment funktioniert | `POST /projects/{id}/enrich` | terrain in geodata |
| `test_slope_classification` | Hanglage-Klassen | - | Korrekte Klassifikation |

**Hanglage-Klassifikation:**

| Klasse | Höhendifferenz | Auswirkung |
|--------|----------------|------------|
| `eben` | < 0.5m | Kein Ausgleich nötig |
| `leicht` | 0.5-1.5m | Stellspindeln |
| `mittel` | 1.5-3.0m | Ausgleichsrahmen |
| `stark` | > 3.0m | Spezial-Fundamentierung |

**Terrain-Daten:**
```json
{
  "terrain": {
    "height_m": 533.5,
    "min_terrain_m": 531.2,
    "max_terrain_m": 537.1,
    "slope_m": 5.9,
    "slope_class": "stark",
    "requires_level_compensation": true
  }
}
```

---

### 8. Gebäude mit Zonen (`TestBuildingZones`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_complex_building_has_zones` | Komplexes Gebäude | SmartBuildingService | Mehrere Zonen |
| `test_church_has_tower_zone` | Kirche mit Turm | - | "turm" Zone vorhanden |
| `test_simple_building_single_zone` | Einfaches Gebäude | - | 1-2 Zonen |

**Zonen-Typen:**

| Typ | Beschreibung | Beispiel |
|-----|--------------|---------|
| `hauptgebaeude` | Hauptbaukörper | EFH, MFH |
| `anbau` | Seitenflügel | Garage |
| `turm` | Türme | Kirchturm |
| `kuppel` | Kuppeln | Bundeshaus |
| `arkade` | Laubengänge | Bundeshaus |

**Test-Gebäude:**

| Adresse | Erwartete Zonen |
|---------|----------------|
| Bundesplatz 3 | Arkaden, Hauptgebäude, Kuppel |
| Münsterplatz 1 | Kirchenschiff, Turm |
| Kramgasse 49 | Hauptgebäude (1 Zone) |

---

### 9. Scaffold Configuration (`TestScaffoldConfiguration`)

| Test | Beschreibung | API | Erwartetes Verhalten |
|------|--------------|-----|---------------------|
| `test_save_and_load_scaffold_config` | Config speichern | `PUT/GET /scaffold` | Werte gespeichert |
| `test_config_persists_across_loads` | Persistenz | - | Nach Reload identisch |

**ScaffoldConfig:**
```json
{
  "simplify_epsilon": 0.5,
  "field_length_ratio": 75.0,
  "system": "layher_blitz_70",
  "breitenklasse": "W09"
}
```

---

### 10. Cache-Konsistenz (`TestCacheConsistency`)

| Test | Beschreibung | Validierung |
|------|--------------|-------------|
| `test_smart_building_cache_populated` | Cache befüllt | get_bundle_by_egid != None |
| `test_neighbors_use_smart_building_cache` | Service-Hierarchie | _get_smart_service vorhanden |
| `test_project_uses_cached_data` | Projekt nutzt Cache | Daten konsistent |

**Service-Hierarchie:**
```
ProjectService  ───┬──►  SmartBuildingService
NeighborsService ──┘          │
                              ▼
                     smart_building_cache
                     (building_contexts.db)
```

---

### 11. API Integration (`TestAPIIntegration`)

| Test | Beschreibung | Schritte |
|------|--------------|----------|
| `test_full_workflow_single_building` | Kompletter Workflow | 6 API-Calls |
| `test_api_error_handling` | Fehlerbehandlung | 404 bei ungültigen IDs |

**Workflow-Sequenz:**
1. Fassaden laden
2. Projekt erstellen
3. Nachbarn laden
4. Config speichern
5. Projekt laden
6. Projekt löschen

---

### 12. Performance (`TestPerformance`)

| Test | Beschreibung | SLA |
|------|--------------|-----|
| `test_facade_loading_under_5s` | Fassaden laden | < 5s |
| `test_neighbors_lookup_under_1s` | Nachbar-Lookup | < 1s |
| `test_address_resolution_under_2s` | Adress-Auflösung | < 2s |

---

## Test-Adressen

| ID | Adresse | Typ | EGID |
|----|---------|-----|------|
| `single_efh` | Kramgasse 49, 3011 Bern | Einzelhaus | - |
| `rowhouse_range` | Knospenweg 2-10, 3006 Bern | Reihenhaus | 1243788-1243793 |
| `complex_building` | Bundesplatz 3, 3011 Bern | Komplex | 2242547 |
| `church` | Münsterplatz 1, 3011 Bern | Kirche | 1230337 |
| `mfh_slope` | Knospenweg 4, 3006 Bern | Hanglage | 1243790 |

---

## Ausführung

### Alle Tests
```bash
cd backend
python -m pytest tests/test_geruestbau_e2e.py -v
```

### Einzelne Kategorie
```bash
python -m pytest tests/test_geruestbau_e2e.py::TestProjectCreation -v
python -m pytest tests/test_geruestbau_e2e.py::TestNeighborsAndFacadeBlocking -v
```

### Mit Coverage
```bash
python -m pytest tests/test_geruestbau_e2e.py --cov=app.services.geruestbau --cov-report=html
```

### Nur schnelle Tests
```bash
python -m pytest tests/test_geruestbau_e2e.py -v -m "not slow"
```

---

## Datenbank-Abhängigkeiten

| Datenbank | Tabellen | Getestet |
|-----------|----------|----------|
| `geruestbau.db` | `projects`, `photos` | ProjectService |
| `building_contexts.db` | `smart_building_cache`, `building_environment` | SmartBuildingService |
| `tiles.db` | `tiles` (Metadaten) | TileCacheService |
| `building_3d.db` | `buildings_3d` | NeighborsService, tile_prefetch |

---

## Bekannte Einschränkungen

1. **API-abhängig:** Tests benötigen laufenden Backend-Server oder TestClient
2. **Cache-abhängig:** Nachbar-Tests benötigen Daten im smart_building_cache
3. **Netzwerk:** Einige Tests rufen externe APIs auf (swisstopo)

---

## Checkliste

```
✅ Projekt-Erstellung
   ☐ Einzeladresse
   ☐ Multi-Adresse
   ☐ Update/Delete

✅ Polygon-Vereinfachung
   ☐ Dynamisches Epsilon
   ☐ Manuelles Epsilon
   ☐ Flächen-Erhaltung

✅ Fassaden
   ☐ Selektion
   ☐ Richtungen (N,E,S,W,NE,SE,SW,NW)
   ☐ Blockierung durch Nachbarn

✅ 3D-View
   ☐ Polygon-Daten
   ☐ Höhen-Daten
   ☐ Nachbar-Polygone

✅ Terrain
   ☐ Hanglage-Berechnung
   ☐ Klassifikation (eben/leicht/mittel/stark)

✅ Zonen
   ☐ Komplexe Gebäude (Bundeshaus)
   ☐ Kirchen (Turm)
   ☐ Einfache Gebäude

✅ Cache
   ☐ SmartBuildingService Cache
   ☐ Service-Hierarchie
   ☐ Konsistenz

✅ Performance
   ☐ Fassaden < 5s
   ☐ Nachbarn < 1s
   ☐ Adress-Auflösung < 2s
```

---

## Nächste Schritte

1. **Frontend-Tests:** Cypress/Playwright für UI-Tests
2. **Load-Tests:** Performance bei vielen gleichzeitigen Anfragen
3. **Regressionstests:** Automatisierte Tests bei jedem Deploy
