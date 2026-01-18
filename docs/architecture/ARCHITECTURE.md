# Architektur-Dokumentation

**Stand: 19.01.2026 14:30**

## Übersicht

Das System besteht aus zwei logisch getrennten Bereichen mit unterschiedlichen Verantwortlichkeiten:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GEODATEN-CH SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────┐│
│  │     GEODATEN-BACKEND            │    │     GERÜSTBAU-BACKEND           ││
│  │     (main.py)                   │    │     (geruestbau.py)             ││
│  │                                 │    │                                 ││
│  │  Verantwortlich für:            │    │  Verantwortlich für:            ││
│  │  • Gebäudedaten (Polygon, Höhe) │    │  • Projekte (CRUD)              ││
│  │  • Nachbar-Suche                │    │  • Gerüst-Konfiguration         ││
│  │  • 3D-Layer (Wall, Roof)        │    │  • Foto-Analyse                 ││
│  │  • Terrain-Daten                │    │  • PDF/IFC Export               ││
│  │  • Tile-Import & Prefetch       │    │  • Ausschreibungs-Import        ││
│  │  • SmartBuildingService         │    │                                 ││
│  │                                 │    │  KEIN direkter DB-Zugriff!      ││
│  │  ══════════════════════════     │    │  Nutzt Geodaten-API             ││
│  │  │ building_3d.duckdb     │     │    │                                 ││
│  │  │ tiles.db               │     │    │  ══════════════════════════     ││
│  │  │ building_contexts.db   │     │    │  │ geruestbau.db           │    ││
│  │  ══════════════════════════     │    │  ══════════════════════════     ││
│  └─────────────────────────────────┘    └─────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API-Dokumentation & Metriken

### Lokale Entwicklung

| Service | Swagger UI | ReDoc | Health |
|---------|------------|-------|--------|
| **Backend** | http://localhost:8000/docs | http://localhost:8000/redoc | http://localhost:8000/health |
| **Geodaten-API** | http://localhost:8000/docs#/Geodaten | - | - |
| **Gerüstbau-API** | http://localhost:8000/docs#/Gerüstbau | - | - |

### Production (Railway)

| Service | Swagger UI | ReDoc | Health |
|---------|------------|-------|--------|
| **Backend** | https://acceptable-trust-production.up.railway.app/docs | https://acceptable-trust-production.up.railway.app/redoc | https://acceptable-trust-production.up.railway.app/health |
| **Frontend** | https://cooperative-commitment-production.up.railway.app | - | - |

### Metriken-Endpunkte

| Endpunkt | Beschreibung |
|----------|--------------|
| `GET /api/v1/db/stats` | DuckDB Statistiken (Gebäude, Tiles, Grösse) |
| `GET /api/v1/heights/stats` | Höhendaten-Statistiken |
| `GET /api/v1/cache/stats` | API-Cache Statistiken |
| `GET /api/v1/smart-building/cache/stats` | SmartBuilding Bundle-Cache |

---

## Verantwortlichkeiten

### 1. Geodaten-Backend (main.py)

**Zuständig für:** Alle Schweizer Geodaten - Gebäude, Terrain, Adressen

| Bereich | Endpunkte | Datenquelle |
|---------|-----------|-------------|
| **Gebäude** | `/api/v1/building/*` | building_3d.duckdb |
| **SmartBuilding** | `/api/v1/smart-building/*` | Aggregiert alle Quellen |
| **Terrain** | `/api/v1/terrain/*` | swissALTI3D API |
| **Höhen** | `/api/v1/heights/*` | swissBUILDINGS3D |
| **Suche** | `/api/v1/search/*` | building_contexts.db |
| **Visualisierung** | `/api/v1/visualize/*` | SVG-Generierung |

**Datenbanken:**

| Datenbank | Inhalt | Zugriff |
|-----------|--------|---------|
| `building_3d.duckdb` | Gebäude-Grunddaten (Polygon, Höhen, 3D-Layer) | **NUR Geodaten-Backend** |
| `tiles.db` | Tile-Metadaten, Download-Status | **NUR Geodaten-Backend** |
| `building_contexts.db` | Zonen, Terrain-Profile, Research-Cache | **NUR Geodaten-Backend** |

### 2. Gerüstbau-Backend (geruestbau.py)

**Zuständig für:** Projektmanagement und Gerüstplanung

| Bereich | Endpunkte | Datenquelle |
|---------|-----------|-------------|
| **Projekte** | `/api/v1/geruestbau/projects/*` | geruestbau.db |
| **Konfiguration** | `/api/v1/geruestbau/configurator/*` | geruestbau.db + Geodaten-API |
| **Adressen** | `/api/v1/geruestbau/address/*` | **Geodaten-API** (nicht direkt!) |
| **Parzellen** | `/api/v1/geruestbau/parzelle/*` | swisstopo API |
| **Import** | `/api/v1/geruestbau/extract`, `/import/url` | Claude Vision |

**Datenbank:**

| Datenbank | Inhalt | Zugriff |
|-----------|--------|---------|
| `geruestbau.db` | Projekte, Scaffold-Config, Fotos | **NUR Gerüstbau-Backend** |

### 3. Batch-Import (batch_import.py)

**Zuständig für:** Massen-Import von Gebäudedaten

| Endpunkt | Beschreibung |
|----------|--------------|
| `POST /api/v1/batch/import/tiles` | Tiles importieren |
| `GET /api/v1/batch/import/status` | Import-Status |
| `POST /api/v1/batch/import/region` | Region importieren (z.B. Kt. Bern) |

---

## Architektur-Bruch: Aktueller Zustand

### Problem: Direkter DuckDB-Zugriff von Gerüstbau

**Verstoss in `geruestbau.py`:**

```python
# geruestbau.py:795-808 - ARCHITEKTUR-BRUCH!
@router.get("/neighbors/by-coordinates")
async def get_neighbors_by_coordinates(...):
    from app.config import get_building_3d_connection  # ← FALSCH!
    conn = get_building_3d_connection(read_only=True)
    cursor.execute("SELECT ... FROM buildings_3d ...")  # ← DIREKT auf DuckDB!
```

**Services mit DuckDB-Zugriff (importiert von geruestbau.py):**

| Service | Zeile | DuckDB-Zugriff |
|---------|-------|----------------|
| `neighbors_service` | 23 | Direkt |
| `address_parser` | 21 | Direkt |
| `blocked_facades_service` | 1188 | Direkt |
| `layer_fetcher` | 437 | Direkt |

### Warum das ein Problem ist

1. **Doppelte Datenhaltung:** Projekte speichern `buildings_data` als JSON - dieselben Daten die in `building_3d.duckdb` liegen
2. **Architektur-Verletzung:** Gerüstbau greift direkt auf Geodaten-DB zu statt API zu nutzen
3. **Wartbarkeit:** Bei Änderungen muss man beide Stellen anpassen
4. **Claude-Halluzinationen:** Claude erstellt oft doppelte Implementierungen weil die Trennung unklar ist

### Lösung: API-Trennung

```
SOLL-ZUSTAND:
─────────────

geruestbau.py                     main.py (Geodaten-API)
     │                                   │
     │  HTTP GET                         │
     ├──────────────────────────────────▶│
     │  /api/v1/building/neighbors       │
     │                                   │
     │  JSON Response                    │
     │◀──────────────────────────────────┤
     │                                   │
     │                                   ▼
     │                          building_3d.duckdb
     │
     ▼
geruestbau.db (NUR Projekte!)
```

---

## Performance-Messungen

### Aktuelle Messwerte (18.01.2026)

| Operation | Zeit | Methode |
|-----------|------|---------|
| **Nachbar-Suche (5m Radius)** | ~0.8ms | DuckDB BBox-Query |
| **Nachbar-Suche (100m Radius)** | ~1.0ms | DuckDB BBox-Query |
| **Gebäude per EGID** | ~0.5ms | DuckDB Index-Lookup |
| **Gebäude per Koordinaten** | ~1.2ms | BBox + Point-in-Polygon |
| **Tile-Prefetch (7000 Gebäude)** | ~70s | Fiona Direct |
| **SmartBuilding collect_all_data** | ~200-500ms | Aggregiert (gecacht: ~5ms) |

### Datenbank-Grössen

| Datenbank | Grösse | Gebäude | Pro Gebäude |
|-----------|--------|---------|-------------|
| `building_3d.duckdb` | ~54 MB | ~6400 | ~8.5 KB |
| `tiles.db` | ~12 KB | - | - |
| `building_contexts.db` | ~188 KB | - | - |
| `geruestbau.db` | ~20 KB | - | - |

### Projektion: Ganze Schweiz

| Metrik | Kt. Bern (aktuell) | Ganze Schweiz |
|--------|-------------------|---------------|
| Gebäude | ~6'400 | ~2'500'000 |
| DuckDB Grösse | ~54 MB | **~21 GB** |
| Tiles | ~2 | ~800 |
| Tile-Download | ~10 min | ~66 Stunden |

---

## Bereits Implementiert: Session-based Prefetch

**Status:** ✅ Implementiert in `tile_prefetch.py:1261-1325`

```
schedule_prefetch_with_neighbors(tile_id, gdb_path, center_e, center_n, main_egid)
│
├── SOFORT (in Thread): load_neighbors_and_save()
│   └─ Lädt Nachbarn im 5m Radius synchron
│
└── ASYNC (Background): prefetch_tile_buildings_async()
    └─ Parquet-Pipeline für restliche Gebäude im Tile
```

**Ablauf beim Projekt-Laden:**
1. User gibt Adresse ein → SSE-Stream startet
2. `collect_all_data()` → Gebäude + 5m Nachbarn sofort
3. Background: Komplettes Tile wird geprefetched
4. Nach ~5s: Alle Gebäude bis 100m verfügbar

---

## Optimierungsmöglichkeiten

### 1. Spatial Index (R-Tree) - NUR PRODUKTION

**Problem:** Aktuelle BBox-Queries sind linear O(n).

**Lösung:** R-Tree Index für koordinatenbasierte Suchen.

```sql
-- DuckDB unterstützt Spatial Extension
INSTALL spatial;
LOAD spatial;

-- R-Tree Index erstellen
CREATE INDEX buildings_rtree ON buildings_3d
USING RTREE (center_e, center_n);

-- Optimierte Nachbar-Suche
SELECT * FROM buildings_3d
WHERE ST_DWithin(
    ST_Point(center_e, center_n),
    ST_Point(2596299.9, 1199805.0),
    100  -- Radius in Metern
);
```

**Wann sinnvoll?**

| Umgebung | Gebäude | Query ohne R-Tree | R-Tree nötig? |
|----------|---------|-------------------|---------------|
| **Entwicklung** | ~6'400 | ~1ms | ❌ Nein |
| **Produktion (Kt. Bern)** | ~100'000 | ~15ms | ⚠️ Optional |
| **Produktion (CH)** | ~2'500'000 | ~400ms | ✅ Ja |

**Konfiguration:**
```python
# config.py
USE_RTREE_INDEX = os.getenv("USE_RTREE_INDEX", "false").lower() == "true"

# Nur auf Produktion aktivieren:
# Railway: USE_RTREE_INDEX=true
```

### 2. Koordinaten-basierte API (NEU - ANALYSE)

**Kernidee:** Ein einziger API-Call liefert ALLE Daten für ein Projekt.

```
┌────────────────────────────────────────────────────────────────────────┐
│                 KOORDINATEN-BASIERTE API STRATEGIE                     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  AKTUELL (viele Calls):                                               │
│  ══════════════════════                                                │
│  1. GET /building/egid/1243788         → Gebäude 1                    │
│  2. GET /building/egid/1243790         → Gebäude 2                    │
│  3. GET /building/1243788/neighbors    → Nachbarn Gebäude 1           │
│  4. GET /building/1243790/neighbors    → Nachbarn Gebäude 2           │
│  5. GET /building/1243788/blocked      → Blockierte Fassaden 1        │
│  6. GET /building/1243790/blocked      → Blockierte Fassaden 2        │
│     ────────────────────────────────────────────────────────          │
│     = 6 API-Calls, viel Overhead                                      │
│                                                                        │
│  NEU (ein Call):                                                       │
│  ═══════════════                                                       │
│  GET /api/v1/building/area?e=2596300&n=1199805&radius_m=100           │
│                                                                        │
│  Response: {                                                           │
│    "center": {"e": 2596300, "n": 1199805},                            │
│    "radius_m": 100,                                                    │
│    "buildings": [                                                      │
│      {"egid": "1243788", "polygon": [...], "center_e": ..., ...},     │
│      {"egid": "1243790", "polygon": [...], "center_e": ..., ...},     │
│      {"egid": "1243792", "polygon": [...], "center_e": ..., ...},     │
│      // ... alle Gebäude im 100m Radius                               │
│    ],                                                                  │
│    "query_time_ms": 1.2                                               │
│  }                                                                     │
│                                                                        │
│  Client-seitige Kategorisierung:                                       │
│  ════════════════════════════════                                      │
│  const projectEgids = ["1243788", "1243790"];  // Aus Projekt         │
│                                                                        │
│  buildings.forEach(b => {                                             │
│    if (projectEgids.includes(b.egid)) {                               │
│      // → Projekt-Gebäude                                             │
│    } else {                                                            │
│      // → Nachbar                                                      │
│      if (b.distance_m < 2.0) {                                        │
│        // → Blockiert Fassade                                         │
│      }                                                                 │
│    }                                                                   │
│  });                                                                   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- **1 API-Call statt 6+**
- **R-Tree macht es blitzschnell** (~0.2ms auf Produktion)
- **Keine Daten-Duplikation** im Projekt
- **Client-seitige Logik** für Kategorisierung (einfacher!)

---

## Daten-Analyse: Was speichern wir im Projekt?

### IST-Zustand (REDUNDANT!)

```
┌────────────────────────────────────────────────────────────────────────┐
│                    AKTUELLE PROJEKT-STRUKTUR                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  geruestbau.db → projects Tabelle                                     │
│  ══════════════════════════════════                                    │
│                                                                        │
│  {                                                                     │
│    "id": "abc123",                                                     │
│    "name": "Knospenweg 4-6",                                          │
│    "address": "Knospenweg 4, 3006 Bern",                              │
│    "egid": "1243790",                                                  │
│    "buildings": [                                                      │
│      {"egid": "1243790", "address": "...", "coordinates": {...}},     │
│      {"egid": "1243792", "address": "...", "coordinates": {...}}      │
│    ],                                                                  │
│                                                                        │
│    "buildings_data": {  ← REDUNDANT! (50-200 KB pro Projekt)          │
│      "1243790": {                                                      │
│        "building": {"egid": "...", "polygon": [...], ...},            │
│        "heights": {...},                                               │
│        "walls": [...],      ← Bereits in building_3d.duckdb!          │
│        "roofs": [...],      ← Bereits in building_3d.duckdb!          │
│        "terrain": {...},    ← Bereits in building_contexts.db!        │
│        "zones": [...]       ← Bereits in building_contexts.db!        │
│      },                                                                │
│      "1243792": { ... }                                                │
│    }                                                                   │
│  }                                                                     │
│                                                                        │
│  PROBLEM: Daten werden DOPPELT gespeichert!                           │
│  - Einmal in building_3d.duckdb (Geodaten-Backend)                    │
│  - Nochmal in geruestbau.db → buildings_data                          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### SOLL-Zustand (MINIMAL)

```
┌────────────────────────────────────────────────────────────────────────┐
│                    NEUE PROJEKT-STRUKTUR (Vorschlag)                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  geruestbau.db → projects Tabelle                                     │
│  ══════════════════════════════════                                    │
│                                                                        │
│  {                                                                     │
│    "id": "abc123",                                                     │
│    "name": "Knospenweg 4-6",                                          │
│    "address": "Knospenweg 4, 3006 Bern",                              │
│                                                                        │
│    // NEU: Koordinaten-Referenz statt volle Daten                     │
│    "center_e": 2596300.0,     ← Projekt-Zentrum                       │
│    "center_n": 1199810.0,     ← Projekt-Zentrum                       │
│    "project_egids": ["1243790", "1243792"],  ← Welche EGIDs gehören   │
│                                                  zum Projekt?          │
│                                                                        │
│    // Projekt-spezifische Einstellungen (NICHT Geodaten!)             │
│    "config": {                                                         │
│      "settings": {"system": "layher_blitz", "work_type": "facade"},   │
│      "facades": [{"index": 0, "selected": true, ...}],                │
│      "access_points": [...]                                            │
│    },                                                                  │
│                                                                        │
│    // Metadaten                                                        │
│    "client_name": "...",                                               │
│    "deadline": "..."                                                   │
│  }                                                                     │
│                                                                        │
│  KEIN buildings_data mehr!                                            │
│  Geodaten werden LIVE aus Geodaten-API geladen.                       │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Vergleich

| Aspekt | IST (buildings_data) | SOLL (Koordinaten-Referenz) |
|--------|---------------------|----------------------------|
| **Projekt-Grösse** | 50-200 KB | ~1 KB |
| **API-Calls beim Laden** | 0 (alles lokal) | 1 (area query) |
| **Daten-Aktualität** | Snapshot vom Speichern | Immer aktuell |
| **Duplikation** | ✅ Ja (redundant!) | ❌ Nein |
| **Skalierung 1000 Projekte** | 50-200 MB | ~1 MB |

---

## Mapping-Analyse: Kann der Client kategorisieren?

### Was liefert der Area-Query?

```typescript
// Response von GET /api/v1/building/area?e=...&n=...&radius_m=100

interface AreaResponse {
  center: { e: number; n: number };
  radius_m: number;
  buildings: Array<{
    egid: string;
    polygon: [number, number][];
    center_e: number;
    center_n: number;
    traufhoehe_m: number;
    firsthoehe_m: number;
    gebaeudehoehe_m: number;
    // Optional: 3D-Layer wenn angefordert
    walls?: BuildingWall[];
    roofs?: BuildingRoof[];
  }>;
  query_time_ms: number;
}
```

### Client-seitige Kategorisierung

```typescript
// Im Frontend (ConfiguratorPage.tsx)

function categorizeBuildings(
  areaResponse: AreaResponse,
  projectEgids: string[],
  projectCenter: { e: number; n: number }
): CategorizedBuildings {

  const projektGebaeude: Building[] = [];
  const nachbarn: Building[] = [];
  const blockierteFassaden: Map<string, string[]> = new Map();  // EGID → blockierte Richtungen

  for (const building of areaResponse.buildings) {
    // 1. Ist es ein Projekt-Gebäude?
    if (projectEgids.includes(building.egid)) {
      projektGebaeude.push(building);
    } else {
      // 2. Es ist ein Nachbar
      const distance = calculateDistance(projectCenter, building);
      nachbarn.push({ ...building, distance_m: distance });

      // 3. Blockiert es eine Fassade? (< 2m Abstand)
      if (distance < 2.0) {
        // Berechne welche Fassade blockiert ist
        for (const projektGeb of projektGebaeude) {
          const blockedDir = calculateBlockedDirection(projektGeb, building);
          if (blockedDir) {
            const existing = blockierteFassaden.get(projektGeb.egid) || [];
            existing.push(blockedDir);
            blockierteFassaden.set(projektGeb.egid, existing);
          }
        }
      }
    }
  }

  return { projektGebaeude, nachbarn, blockierteFassaden };
}
```

### Was brauchen wir im Projekt?

| Feld | Typ | Beschreibung | Woher? |
|------|-----|--------------|--------|
| `center_e` | float | Projekt-Zentrum E | Berechnet aus Projekt-Gebäuden |
| `center_n` | float | Projekt-Zentrum N | Berechnet aus Projekt-Gebäuden |
| `project_egids` | string[] | EGIDs der Projekt-Gebäude | Vom User ausgewählt |
| `config` | JSON | Gerüst-Einstellungen | User-Konfiguration |

### Können wir alles mappen?

| Anforderung | Machbar? | Methode |
|-------------|----------|---------|
| **Projekt-Gebäude** | ✅ Ja | `egid in project_egids` |
| **Nachbarn** | ✅ Ja | `egid NOT in project_egids` |
| **Blockierte Fassaden** | ✅ Ja | Distanz < 2m + Richtungsberechnung |
| **Polygon** | ✅ Ja | Aus Area-Response |
| **Höhen** | ✅ Ja | Aus Area-Response |
| **3D-Walls** | ✅ Ja | Optional in Area-Response (oder separater Call) |
| **3D-Roofs** | ✅ Ja | Optional in Area-Response (oder separater Call) |
| **Terrain** | ✅ Ja | Separates Terrain-API für Umkreis (geplant) |
| **Zonen** | ✅ Ja | Bei komplexen Gebäuden im Objekt enthalten |

---

## Neuer API-Endpunkt: `/api/v1/building/area`

```
GET /api/v1/building/area
  ?e=2596300            # Zentrum E (LV95)
  &n=1199805            # Zentrum N (LV95)
  &radius_m=100         # Suchradius
  &include_walls=true   # Optional: 3D-Walls
  &include_roofs=true   # Optional: 3D-Roofs
  &include_terrain=true # Optional: Terrain-Daten

Response: {
  "center": {"e": 2596300, "n": 1199805},
  "radius_m": 100,
  "buildings_count": 15,
  "buildings": [
    {
      "egid": "1243788",
      "polygon": [[2596290, 1199800], ...],
      "center_e": 2596295.5,
      "center_n": 1199802.3,
      "distance_from_center_m": 5.2,  // Distanz zum Anfrage-Zentrum
      "traufhoehe_m": 5.54,
      "firsthoehe_m": 8.12,
      "gebaeudehoehe_m": 8.12,
      "walls": [...],   // wenn include_walls=true
      "roofs": [...]    // wenn include_roofs=true
    },
    // ... weitere Gebäude
  ],
  "query_time_ms": 1.2
}
```

**Mit R-Tree auf Produktion:** ~0.2ms für 15 Gebäude aus 2.5 Mio

---

## Umstellungsplan

### Phase 1: Neue API-Endpunkte in main.py

| # | Endpunkt | Beschreibung | Priorität |
|---|----------|--------------|-----------|
| 1 | `GET /api/v1/building/neighbors` | Nachbarn per Koordinaten | P1 |
| 2 | `GET /api/v1/building/{egid}/neighbors` | Nachbarn per EGID | P1 |
| 3 | `POST /api/v1/building/batch` | Mehrere Gebäude auf einmal | P2 |

### Phase 2: geruestbau.py umstellen

| # | Änderung | Beschreibung |
|---|----------|--------------|
| 1 | Import entfernen | `get_building_3d_connection` entfernen |
| 2 | API-Client erstellen | httpx-basierter Client für Geodaten-API |
| 3 | Endpunkte umstellen | `/neighbors/by-coordinates` → API-Call |

### Phase 3: Deprecated Endpunkte bereinigen

| Endpunkt | Aktion |
|----------|--------|
| `GET /api/v1/geruestbau/neighbors/by-coordinates` | → Verschieben nach main.py |
| `GET /api/v1/geruestbau/building/{egid}/neighbors` | → Verschieben nach main.py |
| `GET /api/v1/geruestbau/building/{egid}/blocked-facades` | → Deprecated, Frontend-Berechnung |

---

## Datenfluss-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATENFLUSS                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   EXTERNE QUELLEN                      GEODATEN-BACKEND                     │
│   ════════════════                     ════════════════                     │
│                                                                             │
│   swissBUILDINGS3D ──────┐                                                  │
│   (STAC API)             │         ┌──────────────────────┐                │
│                          ├────────▶│  tile_prefetch.py    │                │
│   swissALTI3D ───────────┤         │  layer_fetcher.py    │                │
│   (Terrain API)          │         └──────────┬───────────┘                │
│                          │                    │                             │
│   swisstopo ─────────────┘                    ▼                             │
│   (Geocoding, GWR)               ┌──────────────────────┐                  │
│                                  │  building_3d.duckdb  │                  │
│                                  │  ────────────────────│                  │
│                                  │  • buildings_3d      │                  │
│                                  │  • building_walls    │                  │
│                                  │  • building_roofs    │                  │
│                                  └──────────┬───────────┘                  │
│                                             │                               │
│                                             ▼                               │
│                                  ┌──────────────────────┐                  │
│                                  │  Geodaten-API        │                  │
│                                  │  (main.py)           │                  │
│                                  │  ────────────────────│                  │
│                                  │  /api/v1/building/*  │                  │
│                                  │  /api/v1/smart-*     │                  │
│                                  └──────────┬───────────┘                  │
│                                             │                               │
│   ══════════════════════════════════════════│═══════════════════════════   │
│                                             │                               │
│   GERÜSTBAU-BACKEND                         │   FRONTEND                    │
│   ═════════════════                         │   ════════                    │
│                                             │                               │
│   ┌──────────────────────┐                  │   ┌──────────────────────┐   │
│   │  geruestbau.py       │◀─────────────────┘   │  geruestbau-app      │   │
│   │  ────────────────────│                      │  (React)             │   │
│   │  /api/v1/geruestbau/*│◀─────────────────────│                      │   │
│   └──────────┬───────────┘                      └──────────────────────┘   │
│              │                                                              │
│              ▼                                                              │
│   ┌──────────────────────┐                                                 │
│   │  geruestbau.db       │                                                 │
│   │  ────────────────────│                                                 │
│   │  • projects          │   ← NUR Projekt-Metadaten!                      │
│   │  • photos            │   ← KEINE Gebäudedaten!                         │
│   │  • scaffold_config   │                                                 │
│   └──────────────────────┘                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Checkliste für Entwickler

### Bei neuen Geodaten-Features

- [ ] Gehört das Feature zu Geodaten oder Gerüstbau?
- [ ] Endpunkt in der richtigen Datei (`main.py` vs `geruestbau.py`)?
- [ ] Kein direkter DuckDB-Zugriff in `geruestbau.py`!
- [ ] API-Endpunkt dokumentiert in Swagger?

### Bei Änderungen an bestehenden Features

- [ ] Wird `get_building_3d_connection` in geruestbau.py importiert? → FALSCH!
- [ ] Werden Gebäudedaten in `geruestbau.db` gespeichert? → Prüfen ob nötig!
- [ ] Gibt es bereits einen Geodaten-API Endpunkt dafür?

---

## Umsetzungsplanung

### Phase 1: Analyse und Planung ✅

| # | Aufgabe | Status |
|---|---------|--------|
| 1.1 | Architektur-Bruch dokumentiert | ✅ Erledigt |
| 1.2 | Koordinaten-basierte API analysiert | ✅ Erledigt |
| 1.3 | Daten-Redundanz identifiziert | ✅ Erledigt |
| 1.4 | R-Tree Strategie definiert | ✅ Erledigt |
| 1.5 | Mapping-Analyse abgeschlossen | ✅ Erledigt |

### Phase 2: Genehmigung ✅

| # | Aufgabe | Status |
|---|---------|--------|
| 2.1 | Review durch Benutzer | ✅ Erledigt (19.01.2026) |
| 2.2 | Entscheidung: Koordinaten-API ja/nein | ✅ JA |
| 2.3 | Entscheidung: buildings_data entfernen ja/nein | ✅ JA |
| 2.4 | Prioritäten festlegen | ✅ Erledigt |

### Phase 3: Implementierung (aktuell)

| # | Aufgabe | Priorität | Status |
|---|---------|-----------|--------|
| 3.1 | `GET /api/v1/building/area` Endpunkt erstellen | P1 | ✅ Erledigt (19.01.2026) |
| 3.2 | `GET /api/v1/building/neighbors/{egid}` Endpunkt erstellen | P1 | ✅ Erledigt (19.01.2026) |
| 3.3 | `GeodatenClient` Service erstellen | P1 | ✅ Erledigt (19.01.2026) |
| 3.4 | geruestbau.py: Direkten DuckDB-Zugriff entfernen | P1 | ✅ Erledigt (19.01.2026) |
| 3.5 | Projekt-Schema: `center_e`, `center_n`, `project_egids` | P2 | ✅ Erledigt (19.01.2026) |
| 3.6 | Frontend: API-Funktion `getProjectGeodata` | P2 | ✅ Erledigt (19.01.2026) |
| 3.7 | Frontend: ConfiguratorPage Migration | P2 | ⏳ Ausstehend |
| 3.8 | `buildings_data` aus Projekten entfernen | P2 | ⏳ Ausstehend (deprecated) |
| 3.9 | R-Tree Index auf Produktion aktivieren | P3 | ⏳ Ausstehend |

**Implementierte Dateien (19.01.2026):**
- `main.py:659-869` - Neue Endpunkte `/api/v1/building/area` und `/api/v1/building/neighbors/{egid}`
- `services/geodaten_client.py` - Client für Geodaten-API Aufrufe
- `routers/geruestbau.py` - DuckDB-Zugriff durch GeodatenClient ersetzt
- `routers/geruestbau.py:148-232` - NEU: `/projects/{id}/geodata` Endpunkt
- `services/geruestbau/project_service.py` - Schema-Migration für `center_e`, `center_n`, `project_egids`
- `models/geruestbau.py` - `Project` Model mit neuen Feldern
- `geruestbau-app/src/api/geruestbau.ts` - NEU: `getProjectGeodata()` API-Funktion

**Migrations-Strategie (Frontend):**
1. Neue Projekte: `getProjectGeodata()` nutzen
2. Bestehende Projekte: `buildings_data` als Fallback (wenn vorhanden)
3. Nach vollständiger Migration: `buildings_data` Spalte entfernen

### Phase 4: Dokumentation aktualisieren

| # | Dokument | Änderungen |
|---|----------|------------|
| 4.1 | ARCHITECTURE.md | Status auf "Implementiert" |
| 4.2 | 3D_LAYER_USAGE.md | Area-API dokumentieren |
| 4.3 | STREAMING_ARCHITECTURE.md | Koordinaten-Flow ergänzen |
| 4.4 | STREAMING_DATAFLOW.md | Neue Endpunkte |
| 4.5 | data-flow.md (Rule) | Architektur-Trennung |

### Phase 5: Rules und CLAUDE.md bereinigen

| # | Aufgabe | Status |
|---|---------|--------|
| 5.1 | ARCHITECTURE.md als Rule hinterlegen | ⏳ Ausstehend |
| 5.2 | Obsolete Rules identifizieren | ⏳ Ausstehend |
| 5.3 | CLAUDE.md aktualisieren | ⏳ Ausstehend |
| 5.4 | Veraltete Dokument-Referenzen entfernen | ⏳ Ausstehend |

---

## Verwandte Dokumentation

### Architektur-Dokumente

| Dokument | Beschreibung |
|----------|--------------|
| [3D_LAYER_ANALYSIS.md](./3D_LAYER_ANALYSIS.md) | Analyse der swissBUILDINGS3D Layer-Struktur |
| [3D_LAYER_USAGE.md](./3D_LAYER_USAGE.md) | Verwendung der 3D-Layer im System |
| [3D_LAYER_USAGE_3D_VIEW.md](./3D_LAYER_USAGE_3D_VIEW.md) | 3D-Visualisierung im Frontend |
| [3D_LAYER_USAGE_SCAFFOLDING.md](./3D_LAYER_USAGE_SCAFFOLDING.md) | 3D-Layer für Gerüstplanung |
| [BATCH_IMPORT.md](./BATCH_IMPORT.md) | Tile-Import und Reset-Prozedur |
| [STREAMING_ARCHITECTURE.md](./STREAMING_ARCHITECTURE.md) | SSE-Streaming Architektur |
| [STREAMING_DATAFLOW.md](./STREAMING_DATAFLOW.md) | Datenfluss bei Streaming |

### Weitere Architektur-Dokumente

| Dokument | Beschreibung |
|----------|--------------|
| [BUILDING_3D_SCHEMA.md](./BUILDING_3D_SCHEMA.md) | DuckDB Schema-Definition |
| [POLYGON_DATENFLUSS.md](./POLYGON_DATENFLUSS.md) | Polygon-Vereinfachung (Douglas-Peucker) |
| [PERFORMANCE_ANALYSIS.md](./PERFORMANCE_ANALYSIS.md) | Performance-Messungen |
| [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) | Railway Deployment-Konfiguration |
| [KOORDINATENBASIERTE_ARCHITEKTUR.md](./KOORDINATENBASIERTE_ARCHITEKTUR.md) | Koordinaten-basierte Suche |

### Claude Rules

| Rule | Beschreibung |
|------|--------------|
| [.claude/rules/smart-building.md](../../.claude/rules/smart-building.md) | SmartBuildingService Pipeline |
| [.claude/rules/data-flow.md](../../.claude/rules/data-flow.md) | Datenfluss-Übersicht |
| [.claude/rules/duckdb-rules.md](../../.claude/rules/duckdb-rules.md) | DuckDB Syntax und Connection-Factory |
| [.claude/rules/api-standards.md](../../.claude/rules/api-standards.md) | API-Endpunkte |

---

## Referenzen

- **DuckDB Spatial Extension:** https://duckdb.org/docs/extensions/spatial
- **R-Tree Index:** https://en.wikipedia.org/wiki/R-tree
- **swissBUILDINGS3D:** https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0
- **SmartBuildingService:** `.claude/rules/smart-building.md`
- **Datenfluss:** `.claude/rules/data-flow.md`
