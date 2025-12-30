# CLAUDE.md - Projekt-Kontext für Claude Code

## Modulare Dokumentation

Detaillierte Regeln sind in `.claude/rules/` aufgeteilt:
@.claude/rules/api-standards.md
@.claude/rules/data-sources.md
@.claude/rules/smart-building.md
@.claude/rules/svg-generation.md

### Test-Dokumentation
@docs/tests/README.md - Building Comparison Teststrategie

### Roadmap
@docs/roadmap/CURRENT_BUGS.md - Aktuelle Bugs und Fixes
@docs/roadmap/ML_LEARNING_SYSTEM.md - ML Learning System (geplant)

## Claude Rules

### Sprache & Formatierung
- **Umlaute:** äöü verwenden (NICHT ae/oe/ue)
- **Sonderzeichen:** ±, →, ✅ sind OK
- **Encoding:** UTF-8 für alle Dateien
- **Zeilenenden:** LF (Unix-Style)

### Dokumentation
- **Sprache:** Deutsch
- **Markdown:** Standard GitHub-Flavored
- **Diagramme:** ASCII-Art oder Mermaid

### Code
- **Python:** PEP 8, Type Hints, Docstrings
- **TypeScript:** ESLint + Prettier Konfiguration
- **Kommentare:** Englisch (für internationale Lesbarkeit)
- **Variablen:** snake_case (Python), camelCase (TypeScript)

### Commits
- Format: `type(scope): description`
- Types: feat, fix, chore, docs, refactor, test
- Beispiel: `feat(smart-building): add height validation`

## Projekt: Geodaten Schweiz

Dieses Projekt bietet eine API und Web-App für Schweizer Geodaten (Gebäude, Adressen, Grundstücke).

**Deployment auf Railway.app:**
- Frontend: https://cooperative-commitment-production.up.railway.app/
- Backend: https://acceptable-trust-production.up.railway.app/
- Mit Adresse: `?address=Bundesplatz%203,%203011%20Bern`

## Development Workflow

### Branching-Strategie

**WICHTIG:** Neue Features IMMER auf einem Feature-Branch entwickeln!

```bash
# Feature-Branch erstellen
git checkout -b feature/neues-feature

# Nach Fertigstellung
git push -u origin feature/neues-feature
# Dann PR erstellen
```

**Branch-Namenskonventionen:**
- `feature/` - Neue Features (z.B. `feature/svg-export`)
- `fix/` - Bugfixes (z.B. `fix/height-calculation`)
- `chore/` - Wartung (z.B. `chore/update-deps`)

Ein **SessionStart Hook** (`.claude/hooks/check-feature-branch.py`) erinnert automatisch, falls du auf `main` bist.

## Datenfluss (SmartBuildingService)

Der zentrale SmartBuildingService sammelt alle Daten in einer 10-Schritte Pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATENFLUSS                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend (Suche)                                               │
│       │                                                         │
│       ▼                                                         │
│  GET /api/v1/smart-building/data?address=...                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │       SmartBuildingService              │                   │
│  │       (10-Schritte Pipeline)            │                   │
│  ├─────────────────────────────────────────┤                   │
│  │  1. Geocoding (swisstopo)               │                   │
│  │  2. GWR-Daten (Geschosse, Fläche)       │                   │
│  │  3. Höhendaten (swissBUILDINGS3D)       │                   │
│  │  4. Terrain (swissALTI3D, Hanglage)     │                   │
│  │  5. Polygon (geodienste.ch WFS)         │                   │
│  │  6. Dach-Analyse (berechnet)            │                   │
│  │  7. Recherche (Claude Sonnet)           │ ← building_name   │
│  │  8. Zonen-Analyse (bei komplexen)       │                   │
│  │  9. SUVA Zugänge (berechnet)            │                   │
│  │ 10. Qualitätsbewertung                  │                   │
│  └─────────────────────────────────────────┘                   │
│       │                                                         │
│       ▼                                                         │
│  BuildingDataBundle (gecacht 24h)                               │
│       │                                                         │
│       ├──────────────────────────────────────┐                 │
│       ▼                                      ▼                 │
│  Frontend (Anzeige)               SVG-Generierung              │
│  - Koordinaten                    - Claude API                 │
│  - Höhen                          - Einheitlicher Prompt       │
│  - Gebäudename                    - Gecacht pro EGID           │
│  - Zonen                                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Wichtig:** Nach Adress-Suche werden ALLE Daten gesammelt, inkl. Gebäudename aus Claude-Recherche.

## Integrierte Datenquellen

| Quelle | Daten | Genauigkeit | Status |
|--------|-------|-------------|--------|
| **swisstopo API** | Geokodierung, GWR, Terrain | ±1m | Live-API |
| **GWR (BFS)** | EGID, Adresse, Geschosse, Kategorie, Baujahr | Amtlich, aktuell | via swisstopo |
| **geodienste.ch WFS** | Gebäudegrundriss (Polygon) | ±10cm (AV-Daten) | Live-API |
| **swissBUILDINGS3D 3.0** | Gemessene Gebäudehöhe | ±50cm (Photogrammetrie) | DB + On-Demand |
| **swissALTI3D** | Terrain-Höhen (m ü.M.) | ±0.5m (LiDAR) | Live-API |

### Höhendaten-Verfügbarkeit

**On-Demand für ALLE Gebäude (NEU 30.12.2025):**
- Höhendaten werden automatisch per STAC API abgerufen
- Beim ersten Aufruf: ~5-10s für Tile-Download
- Danach: Sofort aus lokaler DB (gecacht)
- Funktioniert für **jedes Gebäude in der Schweiz**

**Technische Details:**
- LV03→LV95 Koordinatenkonvertierung automatisch
- Tile-Größe: 1km × 1km (~100-500 Gebäude pro Tile)
- Koordinaten-Toleranz: ±50m für Lookup

### Datengenauigkeit

| Messwert | Quelle | Genauigkeit |
|----------|--------|-------------|
| Gebäudehöhe (gemessen) | swissBUILDINGS3D | ±0.5m |
| Gebäudehöhe (geschätzt) | Geschosse × 3.2m | ±2-3m |
| Terrain-Höhe | swissALTI3D | ±0.5m |
| Fassadenlänge | AV-Grundriss | ±10cm |
| Grundfläche | AV-Grundriss | ±0.1m² |
| Koordinaten | LV95 | ±1m |

## Architektur

```
geodaten-ch/
├── backend/          # FastAPI + Python 3.11
│   └── app/
│       ├── main.py           # API Endpunkte
│       ├── models/schemas.py # Pydantic Models
│       ├── data/             # SQLite Datenbanken
│       │   └── building_heights.db  # swissBUILDINGS3D Höhen
│       └── services/
│           ├── swisstopo.py  # swisstopo API Adapter
│           ├── geodienste.py # geodienste.ch WFS (Gebäudegeometrie)
│           ├── terrain.py    # swissALTI3D Terrain-Höhen (NEU)
│           ├── height_db.py  # Höhendatenbank Service
│           └── cache.py      # SQLite Cache
│   └── scripts/
│       └── import_building_heights.py  # swissBUILDINGS3D Import
│
├── frontend/         # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── SearchForm.tsx
│           ├── BuildingCard.tsx
│           ├── ScaffoldingCard.tsx  # Gerüstbau-Daten
│           └── ApiStatus.tsx
│
└── Deployed on Railway.app
```

## API-Testergebnisse (20.12.2025)

### swisstopo (api3.geo.admin.ch) - EMPFOHLEN ✅
- **Erfolgsrate: 100%** (8/8 Tests)
- **Ø Antwortzeit: 222ms**
- Score: 93.3/100

Funktionierende Endpunkte:
- Adresssuche: 43-48ms
- Feature Search (GWR): 46ms
- Find by EGID: 28ms
- Identify: 89ms

### GWR (madd.bfs.admin.ch)
- Erfolgsrate: 44% (4/9 Tests)
- MADD XML funktioniert
- Address-to-EGID problematisch

### geodienste.ch
- Erfolgsrate: 50% (4/8 Tests)
- WMS funktioniert
- WFS hat Probleme (Status 400)

## Wichtige API-Endpunkte (swisstopo)

```python
# Adresssuche
GET https://api3.geo.admin.ch/rest/services/api/SearchServer
    ?searchText=Bundesplatz 3, Bern
    &type=locations
    &origins=address

# Gebäude per EGID
GET https://api3.geo.admin.ch/rest/services/api/MapServer/find
    ?layer=ch.bfs.gebaeude_wohnungs_register
    &searchText=190365
    &searchField=egid

# Identify an Koordinate
GET https://api3.geo.admin.ch/rest/services/api/MapServer/identify
    ?geometryType=esriGeometryPoint
    &geometry=2600000,1199000
    &layers=all:ch.bfs.gebaeude_wohnungs_register
```

## swissALTI3D Terrain API (NEU)

Präzise Geländehöhen für die Schweiz (LiDAR-basiert).

### Endpunkte (swisstopo)

```python
# Einzelpunkt-Höhe
GET https://api3.geo.admin.ch/rest/services/height
    ?easting=2600423        # LV95 E-Koordinate
    &northing=1199521       # LV95 N-Koordinate
    &sr=2056                # Optional: Koordinatensystem (default: LV95)
# Response: {"height": "543.1"}

# Terrain-Profil entlang einer Linie
GET https://api3.geo.admin.ch/rest/services/profile.json
    ?geom={"type":"LineString","coordinates":[[E1,N1],[E2,N2]]}
    &sr=2056
    &nb_points=50           # Anzahl Punkte
# Response: {"alts": {"COMB": [...], "DTM2": [...], "DTM25": [...]}}
```

### Höhenmodelle

| Modell | Auflösung | Beschreibung |
|--------|-----------|--------------|
| **COMB** | 2m | Kombiniertes Modell (empfohlen) |
| **DTM2** | 2m | Digitales Terrainmodell |
| **DTM25** | 25m | Gröbere Auflösung |

### Backend-Integration

```python
# In app/services/terrain.py
terrain_service = get_terrain_service()

# Einzelpunkt
height = await terrain_service.get_height(2600423, 1199521)
# -> 543.1 (m ü.M.)

# Profil
profile = await terrain_service.get_profile(
    start_e=2600000, start_n=1199000,
    end_e=2600500, end_n=1199500,
    nb_points=50
)
# -> {"model": "COMB", "heights": [...], "distances": [...]}
```

### App-API Endpunkte

```python
# Terrain-Höhe an Koordinate
GET /api/v1/terrain/height?e=2600423&n=1199521
# Response: {"height_m": 543.1, "model": "COMB"}

# Terrain-Profil
GET /api/v1/terrain/profile?start_e=...&start_n=...&end_e=...&end_n=...
# Response: {"heights": [...], "distances": [...]}
```

### Beispiel-Höhen

| Ort | Koordinaten (LV95) | Höhe |
|-----|-------------------|------|
| Bundeshaus Bern | 2600423, 1199521 | 543.1 m ü.M. |
| Zermatt | 2620845, 1097886 | 2627.8 m ü.M. |
| Bern Münster | 2600656, 1199497 | 535.4 m ü.M. |

## Dachneigung-Berechnung (Option C)

Heuristische Berechnung der Dachdaten aus verfügbaren Höhen.

### Berechnung

```python
# Formel für Satteldach
neigung_grad = arctan((firsthoehe - traufhoehe) / (gebaeudetiefe / 2)) × (180/π)

# Beispiel: EFH mit 6m Traufe, 9m First, 10m Tiefe
neigung = arctan((9 - 6) / 5) = arctan(0.6) = 31°
```

### Dachformen (RoofType)

| Typ | Neigung | Beschreibung |
|-----|---------|--------------|
| `flachdach` | < 5° | Attika-Dach |
| `pultdach` | 5-15° | Einseitig geneigt |
| `satteldach` | 15-45° | Standard Wohnbau |
| `walmdach` | 15-45° | Quadratisches Gebäude |
| `mansarddach` | > 60° | Gebrochene Flächen |

### Backend-Integration

```python
# In app/services/roof.py
roof_service = get_roof_service()

result = roof_service.calculate(
    traufhoehe_m=6.0,
    firsthoehe_m=9.0,
    building_depth_m=10.0,
    polygon=[(E1,N1), (E2,N2), ...]
)
# -> RoofData(roof_type=SATTELDACH, roof_angle_deg=31.0, ...)
```

### API Response (im Scaffolding-Endpoint)

```json
{
  "roof": {
    "roof_type": "satteldach",
    "roof_angle_deg": 31.0,
    "roof_orientation": "O-W",
    "first_azimuth_deg": 90.0,
    "roof_area_m2": 153.9,
    "scaffolding_height_m": 10.0,
    "confidence": 0.6
  }
}
```

### Einschränkungen

- **Einfache Gebäude:** Gute Ergebnisse für EFH/MFH
- **Komplexe Gebäude:** Für Bundeshaus, Kirchen → Option A/B nötig
- **Konfidenz:** Gibt an wie verlässlich die Berechnung ist (0-1)

## Orthofoto-Service (NEU 28.12.2025)

Ruft Luftbilder (Orthofotos) von swisstopo WMS ab für Claude-Analyse.

### Backend-Integration

```python
# In app/services/orthofoto.py
from app.services.orthofoto import get_orthofoto_service

orthofoto_service = get_orthofoto_service()

# Orthofoto für Bereich abrufen
result = await orthofoto_service.get_orthofoto(
    center_e=2600450,           # LV95 E-Koordinate
    center_n=1199830,           # LV95 N-Koordinate
    width_m=100,                # Ausschnittbreite in Metern
    height_m=100,               # Ausschnitthöhe in Metern
    resolution_m=0.5,           # Meter pro Pixel
    layer="orthofoto"           # "orthofoto", "karte" oder "luftbild"
)
# -> OrthofotoResult mit image_base64, width_px, height_px, ...

# Für Gebäude mit automatischem Padding
result = await orthofoto_service.get_building_orthofoto(
    center_e=2600450,
    center_n=1199830,
    building_width_m=30,
    building_depth_m=20,
    padding_factor=1.5,         # 50% mehr Umgebung
    resolution_m=0.25           # Hohe Auflösung
)
```

### OrthofotoResult

```python
@dataclass
class OrthofotoResult:
    image_base64: str           # Base64-kodiertes PNG für Claude Vision API
    width_px: int               # Bildbreite in Pixeln
    height_px: int              # Bildhöhe in Pixeln
    center_e: float             # LV95 E-Koordinate Zentrum
    center_n: float             # LV95 N-Koordinate Zentrum
    resolution_m: float         # Meter pro Pixel
    bbox: Tuple[float, ...]     # Bounding Box (min_e, min_n, max_e, max_n)
    source: str                 # "swisstopo"
    media_type: str             # "image/png"
```

### Integration mit Claude-Analyse

Die Claude-Analyse für komplexe Gebäude kann optional ein Orthofoto einbeziehen:

```python
# In app/services/building_context.py
context = await context_service.analyze_with_claude(
    egid="1234567",
    adresse="Bundesplatz 3, 3011 Bern",
    polygon=polygon,
    height_data=height_data,
    gwr_data=gwr_data,
    include_orthofoto=True      # Orthofoto für Analyse einbeziehen
)

# Ergebnis enthält zusätzliche Analyse
if context.has_orthofoto_analysis:
    print(context.orthofoto_analysis)
    # {
    #   "roof_features": ["gauben_nord", "pv_anlage_sued"],
    #   "courtyards": ["innenhof_zentral"],
    #   "access_issues": ["baum_suedwest"],
    #   "building_style": "gruenderzeit",
    #   "polygon_accuracy": "gut"
    # }
```

### Kosten-Vergleich

| Analyse-Typ | Kosten | Verwendung |
|-------------|--------|------------|
| Nur Geometrie | ~$0.01-0.02 | Standard, schnell |
| Mit Orthofoto | ~$0.05-0.10 | Komplexe Gebäude, Innenhöfe |

### Was Claude aus dem Orthofoto erkennt

1. **Dachaufbauten**: Gauben, Kamine, PV-Anlagen, Dachterrassen
2. **Innenhöfe**: U-Form, Karree, Durchgänge
3. **Gebäudegrenzen**: Polygon-Verifizierung
4. **Architektur-Stil**: Historisch, Gründerzeit, Modern
5. **Zugangsprobleme**: Bäume, enge Gassen, Nachbargebäude

### Neuer ZoneType: INNENHOF

Erkannte Innenhöfe werden als separate Zone mit `beruesten: false` erfasst:

```python
class ZoneType(str, Enum):
    # ... bestehende Typen ...
    INNENHOF = "innenhof"  # Nicht einrüsten
```

## GWR-Daten (verfügbare Felder)

- `egid` - Eidg. Gebäudeidentifikator
- `strname`, `deinr` - Strasse, Hausnummer
- `dplz4`, `ggdename` - PLZ, Ort
- `gdekt` - Kanton
- `gbauj` - Baujahr
- `gkat` - Gebäudekategorie (siehe Tabelle unten)
- `gastw` - Anzahl Geschosse
- `ganzwhg` - Anzahl Wohnungen
- `garea` - Gebäudefläche m²
- `gwaerzh1` - Heizungsart
- `genh1` - Energieträger Heizung

### GKAT Gebäudekategorien (Komplexitäts-Erkennung)

| Code | Bezeichnung | Komplexität |
|------|-------------|-------------|
| **1010** | Provisorische Unterkunft | SIMPLE |
| **1020** | Einfamilienhaus (EFH) | SIMPLE |
| **1030** | Mehrfamilienhaus (MFH) | SIMPLE |
| **1040** | Wohngebäude mit Nebennutzung | MODERATE |
| **1060** | Gebäude für Bildung/Kultur | COMPLEX |
| **1080** | Gebäude für Gesundheit | COMPLEX |
| **1110** | Kirchen, religiöse Gebäude | COMPLEX |
| **1130** | Museen, Bibliotheken | COMPLEX |
| **1212** | Industriegebäude | COMPLEX |

**Verwendung:** Der Prompt-Selektor nutzt `gkat` als eines von mehreren Kriterien zur Komplexitäts-Erkennung.

## SVG Prompt-Selektor System (NEU v2.0)

Automatische Unterscheidung zwischen einfachen und komplexen Gebäuden für die Claude API SVG-Generierung.

### Problem (vor v2.0)

Claude fügte fälschlicherweise Kuppeln zu einfachen Wohnhäusern hinzu, weil der Prompt alle möglichen Zone-Typen erwähnte.

### Lösung: Separate Prompts

| Gebäudetyp | Prompt | Erlaubte Elemente |
|------------|--------|-------------------|
| **SIMPLE** | `simple_building_prompt.py` | Rechteck + Satteldach, KEINE Kuppeln/Türme/Arkaden |
| **COMPLEX** | `complex_building_prompt.py` | Alle Elemente, aber NUR wenn in Zonen-Daten vorhanden |

### Komplexitäts-Erkennung (`prompt_selector.py`)

```python
# Kriterien für COMPLEX
COMPLEX_ZONE_TYPES = {'kuppel', 'turm', 'arkade', 'treppenhaus'}
COMPLEX_GKAT_CODES = {1040, 1060, 1080, 1110, 1130, 1212}
COMPLEX_POLYGON_POINTS = 12  # > 12 Punkte
COMPLEX_AREA_M2 = 1000       # > 1000 m²
COMPLEX_HEIGHT_DIFF = 5      # > 5m zwischen Zonen

# Kriterien für MODERATE
MODERATE_ZONE_TYPES = {'anbau', 'garage', 'vordach'}
MODERATE_POLYGON_POINTS = 6  # > 6 Punkte
MODERATE_AREA_M2 = 500       # > 500 m²
```

### Entscheidungslogik

```
┌─────────────────────────────────────────────────────────────┐
│                  KOMPLEXITÄTS-ERKENNUNG                     │
├─────────────────────────────────────────────────────────────┤
│  1. Zone-Typen prüfen                                       │
│     → kuppel/turm/arkade vorhanden? → COMPLEX               │
│     → anbau/garage/vordach vorhanden? → MODERATE            │
│                                                             │
│  2. Höhendifferenz zwischen Zonen                           │
│     → > 5m Unterschied? → COMPLEX                           │
│                                                             │
│  3. GKAT-Code prüfen                                        │
│     → 1060/1080/1110/1130/1212? → COMPLEX                   │
│                                                             │
│  4. Polygon-Komplexität                                     │
│     → > 12 Punkte? → COMPLEX                                │
│     → > 6 Punkte? → MODERATE                                │
│                                                             │
│  5. Grundfläche                                             │
│     → > 1000 m²? → COMPLEX                                  │
│     → > 500 m²? → MODERATE                                  │
│                                                             │
│  6. Default                                                 │
│     → SIMPLE (normales Wohngebäude)                         │
└─────────────────────────────────────────────────────────────┘
```

### Dateien

```
backend/app/services/svg_prompts/
├── __init__.py                    # Modul-Export
├── prompt_selector.py             # Komplexitäts-Erkennung
├── simple_building_prompt.py      # Für EFH/MFH (KEINE Kuppeln!)
└── complex_building_prompt.py     # Für öffentliche Gebäude
```

### Cache-Invalidierung

Der Cache-Key enthält jetzt eine Version (`v: "2.0"`), sodass alte SVGs mit Kuppeln automatisch neu generiert werden.

## Gerüstbau-Features

### API-Endpunkte

```python
# Gerüstbau-Daten per Adresse
GET /api/v1/scaffolding?address=Bundesplatz 3, 3011 Bern

# Gerüstbau-Daten per EGID
GET /api/v1/scaffolding/by-egid/2242547

# Höhendatenbank-Statistiken
GET /api/v1/heights/stats
```

## Building Context System (NEU)

Ermöglicht die Analyse komplexer Gebäude mit mehreren Höhenzonen.

### API-Endpunkte

```python
# Kontext abrufen (mit optionaler Auto-Erstellung)
GET /api/v1/building/context/{egid}?create_if_missing=true&analyze_if_complex=true

# Claude-Analyse für komplexes Gebäude triggern
POST /api/v1/building/context/{egid}/analyze
Body: {"include_orthofoto": false, "force_reanalyze": false}

# Kontext manuell aktualisieren
PUT /api/v1/building/context/{egid}
Body: {"zones": [...], "validated": true}

# Kontext löschen (Reset)
DELETE /api/v1/building/context/{egid}
```

### Zonen-Typen

| Typ | Beschreibung | Beispiel |
|-----|--------------|----------|
| `hauptgebaeude` | Hauptbaukörper | Wohnhaus, Bürogebäude |
| `anbau` | Seitenflügel, Erweiterungen | Westflügel, Neubau |
| `turm` | Türme, Treppenhäuser | Kirchturm, Treppenturm |
| `kuppel` | Kuppeln | Bundeshaus-Kuppel |
| `arkade` | Arkaden, Laubengänge | Bundeshaus-Arkaden |
| `vordach` | Vordächer, Überdachungen | Eingangsbereich |
| `treppenhaus` | Aussenliegende Treppenhäuser | Fluchttreppe |
| `garage` | Garagen, Carports | Tiefgaragen-Aufbau |

### Komplexitäts-Erkennung

Das System erkennt automatisch die Gebäudekomplexität:

```python
# Einfach (auto-context, 1 Zone)
- Polygon ≤6 Ecken
- Fläche <300m²
- Konvexe Form
- Kategorie: Wohnen

# Komplex (Claude-Analyse, mehrere Zonen)
- Polygon >12 Ecken
- Fläche >1000m²
- Konkave Form (Einbuchtungen)
- Kategorie: Öffentlich, Kirche, Industrie
```

### Datenbankstruktur

```sql
-- building_contexts.db
CREATE TABLE building_contexts (
    egid TEXT PRIMARY KEY,
    context_json TEXT,           -- BuildingContext als JSON
    source TEXT,                 -- 'auto', 'claude', 'manual'
    confidence REAL,
    validated INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
```

### Kosten (Claude API)
- Pro Analyse: ~$0.01-0.02
- Mit Orthofoto: ~$0.05-0.10
- Caching: Einmal analysiert = gespeichert

### Datenquellen für Höhen (Fallback-Kette)

```
┌─────────────────────────────────────────────────────────────┐
│                    LOOKUP STRATEGIE                         │
├─────────────────────────────────────────────────────────────┤
│  1. Manuell eingegeben (Trauf-/Firsthöhe)                   │
│     ↓ falls nicht gesetzt                                   │
│  2. EGID-Lookup (building_heights_detailed)                 │
│     → Trauf-/Firsthöhe aus swissBUILDINGS3D per EGID       │
│     ↓ falls nicht gefunden                                  │
│  3. EGID-Legacy (building_heights)                          │
│     → Gesamthöhe aus swissBUILDINGS3D per EGID             │
│     ↓ falls nicht gefunden                                  │
│  4. Koordinaten-Lookup (building_heights_by_coord)          │
│     → Höhe per LV95-Koordinaten (±50m Toleranz)            │
│     → Für Gebäude ohne EGID in swissBUILDINGS3D            │
│     ↓ falls nicht gefunden                                  │
│  5. ON-DEMAND FETCH (STAC API) ← NEU 30.12.2025            │
│     → Automatischer Download des swissBUILDINGS3D Tiles    │
│     → Import aller Gebäude im 1km×1km Tile                 │
│     → Funktioniert für JEDES Gebäude in der Schweiz        │
│     ↓ falls nicht verfügbar                                 │
│  6. Geschätzt aus GWR-Daten                                 │
│     → Geschosse × Geschosshöhe + Dachhöhe                  │
│     ↓ falls keine Geschossdaten                             │
│  7. Standard nach Kategorie                                 │
│     → EFH: 8m, MFH: 12m, etc.                              │
└─────────────────────────────────────────────────────────────┘
```

**Wichtig (30.12.2025):** On-Demand Fetch lädt automatisch Höhendaten für jedes Gebäude. Die DB wird "on-the-fly" befüllt - kein Voraus-Import mehr nötig!

### swissBUILDINGS3D Import

```bash
# Daten von swisstopo herunterladen:
# https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta

# Import ausführen
cd backend
python scripts/import_building_heights.py daten.gml --canton BE
```

## Intelligente Datenbank (NEU 29.12.2025)

Erweiterte Datenbank für smarte Suche, SVG-Caching und Umgebungsdaten.

### API-Endpunkte

```python
# Smarte Suche (Alias → FTS → Geocoding)
GET /api/v1/search?q=Bundeshaus
# Response: {"results": [{"egid": "2242547", "name": "Bundeshaus", "score": 1.0, "source": "alias"}]}

# Autocomplete-Vorschläge
GET /api/v1/search/suggestions?q=Bund

# SVG aus Cache laden
GET /api/v1/building/{egid}/svg/{svg_type}
# svg_type: grundriss, ansicht, schnitt

# SVG in Cache speichern
POST /api/v1/building/{egid}/svg/{svg_type}?svg_content=...&generated_by=claude_api

# Cache invalidieren
DELETE /api/v1/building/{egid}/svg?svg_type=ansicht

# Umgebungsdaten (Nachbarn, blockierte Fassaden)
GET /api/v1/building/{egid}/environment

# DB-Statistiken
GET /api/v1/db/stats

# Bekannte Gebäude hinzufügen
POST /api/v1/db/seed-landmarks
```

### Datenbank-Tabellen (building_contexts.db)

| Tabelle | Beschreibung |
|---------|--------------|
| `buildings` | Gebäude-Stammdaten mit Name, Aliases, Keywords |
| `buildings_fts` | FTS5 Volltext-Index für smarte Suche |
| `svg_cache` | Persistenter SVG-Cache mit Versionierung |
| `building_environment` | Umgebungsdaten (Nachbarn, Terrain, Kurven) |
| `claude_research_cache` | Claude API Recherche-Ergebnisse |

### Smarte Suche Strategie

```
┌─────────────────────────────────────────────────────────────┐
│                    SMARTE SUCHE                             │
├─────────────────────────────────────────────────────────────┤
│  1. Alias-Match (Score 1.0)                                 │
│     "Bundeshaus" → EGID 2242547 (exakt)                     │
│     "Parlamentsgebäude" → EGID 2242547 (aus aliases JSON)   │
│     ↓ falls nicht gefunden                                  │
│  2. Volltext-Suche FTS5 (Score 0.5-0.9)                     │
│     "Münster Bern" → Suche in name, aliases, keywords       │
│     ↓ falls nicht gefunden                                  │
│  3. Geocoding-Fallback (Score ~0.7)                         │
│     "Kramgasse 10, Bern" → swisstopo Geocoding             │
└─────────────────────────────────────────────────────────────┘
```

### SVG-Cache Versionierung

```python
# Cache-Key = SHA256(egid + svg_type + version)[:16]
SVG_VERSION = "2.0"

# Cache wird invalidiert bei:
# - Neue Version (Prompt-Änderungen)
# - Manueller Aufruf von DELETE endpoint
# - Höhendaten-Update für das Gebäude
```

### Bekannte Gebäude (Landmarks)

```python
# Seed-Daten mit POST /api/v1/db/seed-landmarks
LANDMARKS = [
    {"egid": "2242547", "name": "Bundeshaus", "aliases": ["Parlamentsgebäude"]},
    {"egid": "1230337", "name": "Berner Münster", "aliases": ["Münster Bern"]},
    {"egid": "191821074", "name": "Kirche St. Peter und Paul"},
    {"egid": "1017961", "name": "Zytglogge", "aliases": ["Zeitglockenturm"]}
]
```

## Einheitliches Prompt-System (v3.0 - 29.12.2025)

Zentrales Template für Claude SVG-Generierung mit dynamischer Gebäude-Recherche.

**WICHTIG:** Der "Professional" Toggle wurde entfernt. Claude API wird jetzt IMMER für
Schnitt und Ansicht verwendet (identischer Prompt wie Export für Claude.ai).

### Architektur

```
┌─────────────────────────────────────────────────────────────┐
│            EINHEITLICHES PROMPT-SYSTEM v3.0                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │     docs/Export_Prompt_Claude.md (VORLAGE)          │   │
│  │     → Zentrale Dokumentation des Templates          │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│           ┌───────────────┴───────────────┐                 │
│           ▼                               ▼                 │
│  ┌─────────────────┐           ┌─────────────────────────┐ │
│  │ Frontend Export │           │ Backend (automatisch)   │ │
│  │ → API Aufruf    │           │ → use_claude=true       │ │
│  └─────────────────┘           └─────────────────────────┘ │
│           │                               │                 │
│           └───────────────┬───────────────┘                 │
│                           ▼                                 │
│           ┌─────────────────────────────────────────────┐   │
│           │    PromptBuilder.build_svg_prompt()         │   │
│           │    → ClaudeResearchService (dynamisch)      │   │
│           │    → IDENTISCHER Prompt für Export & API    │   │
│           └─────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│           ┌─────────────────────────────────────────────┐   │
│           │    claude_research_cache (SQLite)           │   │
│           │    → 30 Tage TTL                            │   │
│           │    → Ca. $0.01-0.02 pro Recherche (Haiku)   │   │
│           └─────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Dateien

```
backend/app/services/prompts/
├── __init__.py              # Modul-Export
├── research_service.py      # Claude-Recherche mit Cache
└── prompt_builder.py        # Template-basierter Prompt-Aufbau
```

### API-Endpunkte

```python
# Prompt generieren (inkl. dynamischer Recherche)
GET /api/v1/prompt/generate
    ?address=Bundesplatz 3, 3011 Bern
    &svg_type=all          # all, grundriss, ansicht, schnitt
    &include_research=true # Dynamische Claude-Recherche

# Response:
{
    "prompt": "# SVG-Generierung: Grundriss + Fassadenansicht + ...",
    "address": "Bundesplatz 3, 3011 Bern",
    "egid": 2242547,
    "svg_type": "all",
    "research_included": true,
    "data_sources": {
        "geocoding": true,
        "gwr": true,
        "heights": true,
        "terrain": true,
        "polygon": true,
        "roof": true
    }
}

# Cache-Statistiken
GET /api/v1/prompt/research/stats

# Abgelaufene Cache-Einträge löschen
POST /api/v1/prompt/research/clear-expired
```

### ClaudeResearchService

Dynamische Gebäude-Recherche via Claude API (Haiku) mit Caching.

```python
from app.services.prompts import get_research_service

service = get_research_service()
research = await service.get_building_research(
    adresse="Bundesplatz 3, 3011 Bern",
    egid="2242547",
    coordinates=(2600450, 1199830),
    gwr_data={"building_category": "Öffentliches Gebäude"}
)

# BuildingResearch enthält:
# - building_name: "Bundeshaus (Schweizer Parlamentsgebäude)"
# - building_type: "Parlamentsgebäude"
# - architectural_style: "Historismus (Neorenaissance)"
# - tower_config: {"count": 0, "position": null}
# - special_features: ["Kuppel", "Arkaden", "Ehrenhof"]
# - suggested_zones: [{"name": "Arkaden", "height_m": 6, ...}, ...]
```

### PromptBuilder

Template-basierter Prompt-Aufbau nach `Export_Prompt_Claude.md`.

```python
from app.services.prompts import get_prompt_builder

builder = get_prompt_builder()
prompt = await builder.build_svg_prompt(
    adresse="Bundesplatz 3, 3011 Bern",
    egid="2242547",
    dimensions={"traufhoehe_m": 14.5, "firsthoehe_m": 62.6},
    gwr_data={"building_category": "Öffentliches Gebäude"},
    terrain={"terrain_height_m": 543.1},
    polygon=[[2600450, 1199830], ...],
    svg_type="all",
    include_research=True  # Dynamische Recherche aktivieren
)
```

### Kosten

| Aktion | Kosten |
|--------|--------|
| Gecachte Recherche | $0.00 |
| Neue Recherche (Haiku) | ~$0.01-0.02 |
| Cache-TTL | 30 Tage |

### Ersetzt building_hints.py

Das neue System ersetzt die statischen Building-Hints:

| Alt (building_hints.py) | Neu (prompts/) |
|-------------------------|----------------|
| 7 hardcoded Gebäude | Dynamisch für alle |
| Manuelle Pflege nötig | Automatische Recherche |
| Keine Kosten | ~$0.01-0.02 pro neuem Gebäude |
| Sofort verfügbar | 1-2s Latenz bei Cache-Miss |

## SmartBuildingService (NEU 29.12.2025)

Zentraler Service für die schrittweise Sammlung aller Gebäudedaten für Gerüstplanung.

### Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                   SmartBuildingService                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  collect_all_data(address) → BuildingDataBundle             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              10-Schritte Pipeline                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  1. Geocoding (swisstopo)                          │   │
│  │  2. GWR-Daten (swisstopo)                          │   │
│  │  3. Höhendaten (swissBUILDINGS3D)                  │   │
│  │  4. Terrain (swissALTI3D, Hanglage)                │   │
│  │  5. Polygon & Fassaden (geodienste.ch)             │   │
│  │  6. Dach-Analyse (berechnet)                       │   │
│  │  7. Gebäude-Recherche (Claude Haiku)               │   │
│  │  8. Zonen-Analyse (Claude Sonnet - bei Komplex)    │   │
│  │  9. SUVA Zugangspunkte (berechnet)                 │   │
│  │ 10. Qualitätsbewertung                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            BuildingDataBundle (Cache)               │   │
│  │            → 24h TTL in SQLite                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         UnifiedPromptGenerator                      │   │
│  │         → IDENTISCHER Prompt für Export & API       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Dateien

```
backend/app/services/smart_building/
├── __init__.py              # Modul-Export
├── models.py                # BuildingDataBundle, ZoneInfo, TerrainProfile
├── service.py               # SmartBuildingService (Orchestrierung)
├── prompt_generator.py      # UnifiedPromptGenerator
├── known_buildings.py       # Bekannte Gebäude-Cache (Bundeshaus, Münster, etc.)
└── research_integration.py  # Integration bekannte Gebäude + Kirchen-Zonen
```

### API-Endpunkte

```python
# Alle Gebäudedaten sammeln
GET /api/v1/smart-building/data?address=Bundesplatz 3, 3011 Bern
    &force_refresh=false   # Bundle-Cache ignorieren
    &include_research=true # Claude-Recherche einbeziehen
    &include_zones=true    # Zonen-Analyse einbeziehen
    &include_terrain=true  # Terrain-Daten einbeziehen
# Response: Vollständiges JSON mit allen gesammelten Daten

# Einheitlichen Prompt generieren
GET /api/v1/smart-building/prompt
    ?address=Bundesplatz 3, 3011 Bern
    &svg_type=all          # all, grundriss, ansicht, schnitt, umgebung
    &force_refresh=false   # ALLE Caches ignorieren (Bundle + Research)
# Response: Prompt-String + Metadaten

# SVG generieren mit vollem Cache-Kontrolle
GET /api/v1/smart-building/svg
    ?address=Bundesplatz 3, 3011 Bern
    &svg_type=schnitt      # grundriss, ansicht, schnitt
    &force_refresh=false   # ALLE Caches ignorieren (Bundle + Research + SVG)
# Response: SVG-String oder null

# Cache-Statistiken
GET /api/v1/smart-building/cache/stats
# Response: { bundle_count, research_entries, svg_versions }

# Cache löschen
DELETE /api/v1/smart-building/cache
    ?address=null          # Optional: nur für diese Adresse
    &cache_type=all        # all, bundle, research, svg
# Response: { cleared_caches: [...], message: "..." }
```

### force_refresh Verhalten

| Parameter | Bundle-Cache | Research-Cache | SVG-Cache |
|-----------|--------------|----------------|-----------|
| `/data?force_refresh=true` | ✅ Ignoriert | ✅ Ignoriert | - |
| `/prompt?force_refresh=true` | ✅ Ignoriert | ✅ Ignoriert | - |
| `/svg?force_refresh=true` | ✅ Ignoriert | ✅ Ignoriert | ✅ Ignoriert |

### Python-Verwendung

```python
from app.services.smart_building import (
    get_smart_building_service,
    get_prompt_generator,
    SVGType,
)

# Daten sammeln
service = get_smart_building_service()
bundle = await service.collect_all_data(
    address="Bundesplatz 3, 3011 Bern",
    force_refresh=False,
    include_research=True,
    include_zones_analysis=True,
    include_terrain=True,
)

# Prompt generieren
generator = get_prompt_generator()
prompt = generator.generate(
    bundle=bundle,
    svg_type=SVGType.ALL,
    include_style_guide=True,
)

# SVG generieren (via claude_svg_zones.py)
from app.services.claude_svg_zones import generate_svg_with_smart_service
svg = await generate_svg_with_smart_service(
    address="Bundesplatz 3, 3011 Bern",
    svg_type="schnitt",
)
```

### BuildingDataBundle

Zentrales Datenmodell mit allen gesammelten Informationen:

```python
@dataclass
class BuildingDataBundle:
    # Identifikation
    egid: Optional[str]
    address_matched: Optional[str]
    building_name: Optional[str]
    building_type: Optional[str]
    architectural_style: Optional[str]

    # Geometrie
    polygon: Optional[List[List[float]]]
    sides: Optional[List[Dict]]
    perimeter_m: Optional[float]

    # Höhen
    traufhoehe_m: Optional[float]
    firsthoehe_m: Optional[float]
    height_quality: DataQuality

    # Terrain (Hanglage)
    terrain: Optional[TerrainProfile]

    # Dach
    roof_type: Optional[str]
    roof_angle_deg: Optional[float]

    # Zonen
    zones: List[ZoneInfo]
    complexity: str  # "simple", "moderate", "complex"

    # Zugänge
    access_points: List[AccessPoint]
    suva_compliant: bool

    # Meta
    data_sources: List[DataSource]
    overall_quality: DataQuality
    warnings: List[str]
```

### Komplexitäts-Erkennung

```
┌─────────────────────────────────────────────────────────────┐
│           _needs_zones_analysis(bundle) → bool              │
├─────────────────────────────────────────────────────────────┤
│  COMPLEX (Claude Sonnet Analyse):                           │
│  → Extreme Höhendifferenz (First - Trauf > 15m)            │
│  → Komplexe GWR-Kategorie (1040, 1060, 1080, 1110, 1130)   │
│  → Grosses Gebäude (> 1000 m²)                             │
│  → Komplexes Polygon (> 12 Punkte)                         │
│                                                             │
│  SIMPLE (Auto-Zone):                                        │
│  → Standard-Wohngebäude                                     │
│  → Einfache Geometrie                                       │
│  → Keine extremen Höhenunterschiede                        │
└─────────────────────────────────────────────────────────────┘
```

### Kosten

| Szenario | Cache | Recherche | Zonen-Analyse | Total |
|----------|-------|-----------|---------------|-------|
| Cache-Hit | ✓ | - | - | $0.00 |
| Einfaches Gebäude | ✗ | Haiku | Auto | ~$0.01-0.02 |
| Komplexes Gebäude | ✗ | Haiku | Sonnet | ~$0.05-0.15 |

### Vorteile gegenüber altem System

| Alt (separate Services) | Neu (SmartBuildingService) |
|-------------------------|---------------------------|
| Daten verstreut | Alles in BuildingDataBundle |
| Mehrfache API-Calls | Bundle-Cache (24h) |
| Separate Prompts | IDENTISCHER Prompt für Export & API |
| Manuelle Integration | Einheitliche Pipeline |
| Keine Qualitätskontrolle | overall_quality, warnings, errors |

## Douglas-Peucker Polygon-Vereinfachung

Die App verwendet den Douglas-Peucker Algorithmus zur Reduktion der Fassadensegmente.
Implementiert in `backend/app/services/geodienste.py`.

### Aktuelle Parameter

```python
# In geodienste.py (GeodiensteService Klasse)
SIMPLIFY_EPSILON = 0.3          # Meter - Toleranz für Punktreduktion
COLLINEAR_ANGLE_TOLERANCE = 8.0  # Grad - für kollineare Segmente
MIN_SIDE_LENGTH = 1.0            # Meter - minimale Seitenlänge
```

### Empfehlungen nach Gebäudegrösse

| Gebäudetyp | EPSILON | ANGLE_TOL | Bemerkung |
|------------|---------|-----------|-----------|
| EFH (10×12m) | 0.3–0.5 | 5–8° | Wenig Vereinfachung nötig |
| MFH/Gewerbe | 0.5–1.0 | 8–10° | Standard |
| Grossprojekt (>50m) | 1.0–2.0 | 8–12° | Starke Vereinfachung |

### Algorithmus-Ablauf

1. **Douglas-Peucker**: Finde Punkt mit max. Abstand zur Verbindungslinie. Wenn > EPSILON → rekursiv teilen
2. **Kollineare Punkte entfernen**: Punkte mit Winkel ≈ 180° (Toleranz ANGLE_TOL) werden entfernt
3. **Kurze Segmente zusammenfassen**: Segmente < MIN_SIDE_LENGTH werden vereint

## NPK 114 Konstanten

Ausmass-Berechnung gemäss NPK 114 D/2012. Implementiert in `backend/app/services/npk114_calculator.py`.

```python
# Zuschläge
FASSADENABSTAND_LF = 0.30        # m - Abstand Gebäude zu Gerüst
GERUESTGANGBREITE_LG = 0.70      # m - für W09
STIRNSEITIGER_ABSCHLUSS_LS = 1.00 # m - beidseitig (= LF + LG)
HOEHENZUSCHLAG = 1.00            # m - über Arbeitshöhe

# Mindestmasse
MIN_AUSMASSLAENGE = 2.5          # m
MIN_AUSMASSHOEHE = 4.0           # m

# Formeln
# LA = LS + L + LS (beidseitiger Abschluss)
# HA = H + Höhenzuschlag
# A = LA × HA
# Giebel: H_mittel = H_Traufe + (H_Giebel × 0.5)
```

## Layher Blitz 70 System

Material-Schätzung implementiert in `backend/app/services/layher_catalog.py`.

### Feldlängen (m)
`3.07, 2.57, 2.07, 1.57, 1.09, 0.73`

### Rahmenhöhen (m)
`2.00, 1.50, 1.00, 0.50`

### Richtwerte
| Parameter | Wert |
|-----------|------|
| Gewicht | 18–22 kg/m² Gerüstfläche |
| Lastklasse | 3 (200 kg/m²) |
| Breitenklasse | W09 (0.90 m) |
| Verankerung | alle 4 m horizontal, alle 4 m vertikal |

### Feldlängen-Verhältnis (Slider in UI)

Der Slider steuert das Verhältnis zwischen 2.57m und 3.07m Feldern:
- **0%**: Nur 2.57m Felder (mehr Flexibilität, mehr Teile)
- **100%**: Nur 3.07m Felder (weniger Teile, weniger Flexibilität)
- **Standard: 50%**: Ausgewogenes Verhältnis

## Höhenzonen bei komplexen Gebäuden

⚠️ **Problem**: SwissBuildings3D liefert oft nur einen globalen Höhenwert, der nicht repräsentativ ist.

**Beispiel Bundeshaus Bern:**
- SwissBuildings3D Traufhöhe: 14.5m → Dies ist der Arkaden-Wert!
- Tatsächliche Parlamentsfassade: 22–25m Traufe

### Empfohlene Strategie

1. **Z-Koordinaten der Polygonpunkte nutzen** (falls verfügbar)
2. **Lokale Höhen pro Fassade** statt globaler Höhe
3. **Fallback-Werte nach Gebäudeteil**:

| Gebäudeteil | Traufhöhe | Gerüsthöhe |
|-------------|-----------|------------|
| Standard (West/Ost) | 18.0 m | 19.0 m |
| Hauptfassaden | 25.0 m | 26.0 m |
| Türme | – | 36.0 m |
| Kuppeln | – | Spezialgerüst |

## SVG-Visualisierung: Aktuell vs. Ziel

**Referenz:** `lawil/claude_ai_bundeshaus/` - Von Claude.ai handgefertigte SVGs für Bundeshaus

### Vergleichstabelle (Stand 25.12.2025)

| Feature | App (aktuell) | Claude.ai Ziel | Status |
|---------|---------------|----------------|--------|
| **Gebäudegeometrie** | 1 Polygon aus geodienste.ch | Mehrere Polygone pro Gebäudeteil | ⚠️ Zonen erkannt |
| **Höhendaten** | Mehrere Zonen (Claude-Analyse) | Höhenzonen pro Gebäudeteil | ✅ |
| **Höhe pro Fassade** | ✅ Implementiert (traufhoehe_m) | Individuelle Höhen | ✅ |
| **Semantische Elemente** | Arkade, Hauptfassade, Kuppel | Kuppel, Türme, Arkaden, Ehrenhof | ✅ Basis |
| **Gerüstzonen** | Farbcodiert im Grundriss | Separate Zonen pro Fassade/Höhe | ✅ |
| **Ständerpositionen** | Rote Punkte alle 2.57m | Punkte alle 2.5-3m (Feldlänge) | ✅ |
| **Verankerungen** | Ecken + alle 4m dazwischen | Entlang Fassade alle 4m h/v | ✅ |
| **Zugänge (Z1-Zn)** | Gelbe Rechtecke (SUVA-konform) | Gelbe Markierungen | ✅ |
| **Masslinien** | Nur Umfang/Fläche | Mit Pfeilen, Beschriftung | ⚠️ |
| **Lagenbeschriftung** | Nur in Schnitt | In Ansicht nummeriert | ⚠️ |
| **Gebäudebeschriftung** | Zonen-Namen im Grundriss | Zonen-Namen (BH West, etc.) | ✅ |
| **Dachform (Ansicht)** | Einfaches Dreieck/Rechteck | Giebel, Kuppel, Laterne | ❌ |
| **Material-Details** | Keine | Säulen, Beläge, Kupfer-Gradient | ❌ |
| **Titelblock** | Professional mode | Vollständig | ✅ |
| **Fusszeile** | Professional mode | Vollständig | ✅ |
| **Legende** | Einfach | Detailliert mit allen Elementen | ⚠️ |
| **Nordpfeil** | ✅ Vorhanden | ✅ | ✅ |
| **Massstab** | ✅ Vorhanden | ✅ | ✅ |
| **Schraffur-Pattern** | Professional mode | Gebäude schraffiert | ✅ |

### Was fehlt für professionelle Grafik (Claude.ai Niveau)

**Implementiert ✅:**
1. ~~Höhenzonen-Erkennung~~ → Claude-Analyse bei Höhendifferenz >15m
2. ~~Gebäudeteil-Klassifikation~~ → Arkade, Hauptfassade, Kuppel
3. ~~Ständer-Berechnung~~ → Alle 2.57m (Layher Blitz 70)
4. ~~Verankerungs-Raster~~ → Ecken + alle 4m
5. ~~Ständer-Punkte~~ → Rote Punkte im SVG
6. ~~Zugangs-Markierungen~~ → Gelbe Rechtecke (Z1, Z2, etc.)

**Noch offen ❌:**
1. **Innenhöfe/Ehrenhof** als Ausschnitt im Polygon markieren
2. **Masslinien mit Pfeilen** statt nur Text-Labels
3. **Separate Gebäudepolygone** bei U/L-Form (aktuell: 1 Polygon mit Zonen)
4. **Ansicht-SVG**: Kuppel, Giebel, Säulen-Details
5. **Detaillierte Legende** mit allen Symbolen

### Dateien zum Vergleich

```
lawil/
├── claude_ai_bundeshaus/           # Handgefertigte Referenz-SVGs
│   ├── anhang_a_grundriss.svg      # Grundriss mit Höhenzonen
│   ├── anhang_b_ansicht.svg        # Ansicht mit Kuppel, Säulen
│   ├── anhang_c_schnitt.svg        # Schnitt durch Parlament
│   ├── anhang_d_gerustkarte.svg    # Feldaufteilung
│   └── PROJEKT_KONTEXT.md          # Projektdokumentation
│
└── geodaten-ch/                    # App-generierte SVGs
    └── backend/app/services/
        └── svg_generator.py        # Automatische Generierung
```

---

## ⚠️ KRITISCHE ANALYSE: SVG-Qualität (Stand 25.12.2025)

### Das Problem

Die automatisch generierten SVGs erreichen **NICHT** die Qualität der Claude.ai Referenz-SVGs.
Trotz umfangreicher Datensammlung (Polygon, Höhen, Zonen, GWR) ist das Ergebnis "schematisch" statt "architektonisch".

### Was wir haben (Daten)

| Datenquelle | Was wir bekommen | Qualität |
|-------------|------------------|----------|
| geodienste.ch | Polygon mit 26-175 Punkten | ✅ Gut |
| swissBUILDINGS3D | Trauf-/First-/Gebäudehöhe | ✅ Gut |
| GWR (swisstopo) | Geschosse, Kategorie, Baujahr | ✅ Gut |
| Claude API | Zonen-Analyse (Arkade, Hauptgebäude, Kuppel) | ✅ Gut |

**Fazit Daten:** Wir haben alle nötigen Informationen.

### Was wir produzieren (SVG)

| Element | Unsere Implementierung | Claude.ai Referenz |
|---------|------------------------|-------------------|
| Arkaden | Rechteck + 1 Bogen | Säulenreihe mit Bögen, Schatten |
| Kuppel | Ellipse (oval) | Detaillierte Kuppelform mit Laterne |
| Fenster | Kleine Rechtecke (Raster) | Architektonisch korrekte Anordnung |
| Proportionen | Berechnet aus Zonen-Breite | Visuell ausbalanciert |
| Gerüst | Linien + Rechtecke | Detaillierte Ständer, Riegel, Beläge |
| Gesamteindruck | **Technisches Diagramm** | **Architekturzeichnung** |

### Warum der Unterschied?

#### 1. Regelbasiert vs. Kontextverständnis

**Unser Code:**
```python
if zone_type == 'arkade':
    # Zeichne Rechteck + Bögen
    svg += f'<rect x="{x}" y="{y}" ...>'
    for i in range(num_arches):
        svg += f'<path d="M ... Q ..." />'  # Bogen
```

**Claude.ai (interaktiv):**
- Versteht "Bundeshaus" als historisches Parlamentsgebäude
- Weiss wie Arkaden in der Schweizer Neorenaissance aussehen
- Passt Proportionen visuell an
- Iteriert basierend auf Feedback

#### 2. One-Shot vs. Iterativ

| Ansatz | Prozess | Ergebnis |
|--------|---------|----------|
| **Claude API** | 1 Prompt → 1 Antwort | "Gut genug" beim ersten Versuch |
| **Claude.ai Chat** | Prompt → Feedback → Anpassung → Feedback → ... | Verfeinert bis perfekt |

#### 3. SVG-Generierung ist schwer

Selbst wenn wir Claude API bitten "generiere SVG wie Referenz":
- Claude hat keinen visuellen Feedback-Loop
- Kann das Ergebnis nicht "sehen"
- Muss alles in einem Durchgang richtig machen

### Mögliche Lösungsansätze

#### Option A: Akzeptieren (Status Quo)
- Schematische SVGs für Funktionalität (Gerüstplanung)
- Für Präsentationen: Manuell mit Claude.ai erstellen
- **Aufwand:** Keiner
- **Qualität:** ⭐⭐ (funktional, nicht schön)

#### Option B: Template-basiert
- Vorgefertigte SVG-Templates für Gebäudetypen (EFH, MFH, Kirche, etc.)
- Parameter einsetzen (Höhe, Breite, Zonen)
- **Aufwand:** Hoch (viele Templates nötig)
- **Qualität:** ⭐⭐⭐ (besser, aber starr)

#### Option C: Multi-Step Claude API
1. Claude generiert SVG
2. Wir rendern es (headless browser)
3. Screenshot zurück an Claude: "Verbessere das"
4. Iteration bis gut
- **Aufwand:** Sehr hoch (Infrastruktur, Kosten)
- **Qualität:** ⭐⭐⭐⭐ (potenziell gut)

#### Option D: Hybrid-Workflow
- App sammelt alle Daten + generiert JSON-Export
- User öffnet Claude.ai manuell
- Kopiert JSON rein: "Erstelle SVG für dieses Gebäude"
- Claude.ai generiert hochwertige SVG
- **Aufwand:** Mittel (Export-Funktion)
- **Qualität:** ⭐⭐⭐⭐⭐ (wie Referenz)

### Empfehlung

**Für PoC:** Option A (Status Quo)
- Die schematischen SVGs zeigen, dass die Daten korrekt sind
- Die Zonen-Erkennung funktioniert
- Für Gerüstplanung reicht die Qualität

**Für Produktion:** Option D (Hybrid)
- Export-Button: "Daten für Claude.ai exportieren"
- Generiert strukturierten Prompt mit allen Daten
- User kann in Claude.ai hochwertige SVGs erstellen

### Verfügbare Daten für Claude.ai Prompt

Wenn wir Option D implementieren, hätten wir:

```json
{
  "gebaeude": {
    "adresse": "Bundesplatz 3, 3011 Bern",
    "egid": 1017961,
    "polygon": [[2600450.2, 1199800.5], ...],  // 26 Punkte
    "umfang_m": 285.4,
    "flaeche_m2": 4200
  },
  "hoehen": {
    "traufhoehe_m": 14.53,
    "firsthoehe_m": 62.57,
    "geschosse": 4
  },
  "zonen": [
    {"name": "Arkaden/Erdgeschoss", "typ": "arkade", "hoehe_m": 14.5},
    {"name": "Hauptgebäude", "typ": "hauptgebaeude", "hoehe_m": 28.0},
    {"name": "Kuppel/Turm", "typ": "kuppel", "hoehe_m": 30.0, "spezialgeruest": true}
  ],
  "geruest": {
    "system": "Layher Blitz 70",
    "breitenklasse": "W09",
    "feldlaengen_m": [3.07, 2.57, 2.07, 1.57],
    "gesamtflaeche_m2": 1850
  }
}
```

Dies ist **deutlich mehr Information** als Claude.ai ursprünglich hatte, als die Referenz-SVGs erstellt wurden.

---

## 🎨 Claude API SVG-Generierung: Style-Guidelines (Stand 25.12.2025)

### Problem: Zu künstlerisch statt technisch

Die Claude API generiert aktuell SVGs mit:
- ❌ Farbigem Himmel (blau)
- ❌ Vollfarben statt Schraffur
- ❌ Künstlerischer Interpretation
- ❌ Fehlender/falscher Höhenskala
- ❌ Vermischten Perspektiven

**Ziel:** Technisch-professionelle Architekturzeichnung wie `anhang_b_ansicht.svg`

### Referenz-Analyse: anhang_b_ansicht.svg

| Element | Referenz-Implementierung |
|---------|-------------------------|
| **Hintergrund** | `fill="white"` - Reinweiss, KEIN Himmel |
| **Gebäude-Füllung** | `fill="url(#hatch)"` - Schraffur-Pattern |
| **Hauptlinien** | `stroke="#333"` - Dunkelgrau, 2px |
| **Gerüst** | `stroke="#0066CC"` - EINZIGE blaue Elemente |
| **Verankerungen** | `stroke="#CC0000"`, gestrichelt |
| **Beläge** | `fill="#8B4513"` - Braun |
| **Kuppel** | `fill="url(#copper)"` - Einziger Gradient |

### Pflicht-Patterns für SVG

```xml
<defs>
  <!-- Schraffur für Gebäude (diagonal 45°) -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- Boden/Terrain -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR für Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>

  <!-- Pfeil-Marker für Masslinien -->
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
    <path d="M0,0 L0,6 L9,3 z" fill="#333"/>
  </marker>
</defs>
```

### Farbpalette (STRIKT einhalten!)

| Verwendung | Farbe | Code |
|------------|-------|------|
| Hintergrund | Weiss | `#FFFFFF` |
| Hauptlinien | Dunkelgrau | `#333333` |
| Gebäude-Füllung | Schraffur | `url(#hatch)` |
| Gerüst-Ständer | Blau | `#0066CC` |
| Verankerung | Rot gestrichelt | `#CC0000` |
| Beläge | Braun | `#8B4513` |
| Kupferkuppel | Gradient | `url(#copper)` |
| Beschriftung | Dunkelgrau | `#333` oder `#555` |
| Terrain | Pattern | `url(#ground)` |

### Struktur-Template für Ansicht-SVG

```
1. Weisser Hintergrund (rect fill="white")
2. Terrain-Linie unten (OK Terrain ±0.00)
3. Gebäude mit Schraffur-Füllung
4. Gerüst-Elemente (Ständer, Riegel, Beläge)
5. Verankerungen (gestrichelte Linien)
6. Höhenskala links (±0.00 bis +Xm)
7. Lagenbeschriftung rechts (1. Lage, 2. Lage...)
8. Legende-Box (oben rechts)
```

### Prompt-Verbesserungen für claude_svg_zones.py

**VERBOTEN im Prompt:**
- "handgezeichnet wirkend"
- "Hintergrund mit Himmel"
- "kreativ", "künstlerisch"
- Farbige Fenster (#87CEEB)

**ERFORDERLICH im Prompt:**
```
STIL: Technische Architekturzeichnung, NICHT künstlerisch!
- Hintergrund: WEISS (kein Himmel, kein Gradient)
- Gebäude: Schraffur-Pattern url(#hatch), KEINE Vollfarben
- Gerüst: NUR Blau #0066CC für Ständer/Riegel
- Alle Elemente: Graustufen und technische Patterns
- Perspektive: Reine Frontalansicht (Orthogonalprojektion)
```

### Vergleich: Aktuell vs. Ziel

| Aspekt | Claude API (Fehler) | Referenz (Korrekt) |
|--------|---------------------|-------------------|
| Himmel | `fill="url(#sky)"` blau | Kein Himmel, weiss |
| Gebäude | `fill="#E8DCC8"` Vollfarbe | `fill="url(#hatch)"` |
| Perspektive | 3D-artig, verzerrt | 2D Frontalansicht |
| Fenster | Farbige Rechtecke | Optional, grau |
| Höhenskala | "+0.00" (falsch) | "±0.00 bis +64.0" |
| Proportionen | Fantasie | Massstabsgetreu |

### Nächste Schritte

1. ~~**Prompt in claude_svg_zones.py überarbeiten**~~ ✅ Erledigt
2. ~~**Referenz-SVG als Example im Prompt**~~ ✅ Erledigt (Patterns definiert)
3. **Validierung** - Prüfe generierte SVGs auf Style-Compliance
4. **Fallback** - Bei Style-Fehler: Standard-Generator verwenden

---

## 🧪 Claude API SVG-Generierung: Testergebnisse (28.12.2025)

### Getestete Gebäude

| Gebäude | Adresse | Zonen erkannt | Qualität |
|---------|---------|---------------|----------|
| **Bundeshaus** | Bundesplatz 3, 3011 Bern | 3 (Arkade, Hauptgebäude, Kuppel) | ⭐⭐⭐⭐ |
| **Kramgasse 10** | Kramgasse 10, 3011 Bern | 2 (Hauptgebäude, Anbau) | ⭐⭐⭐⭐ |
| **Berner Münster** | Münsterplatz 1, 3011 Bern | 3 (Kirchenschiff, Seitenkapellen, Turm) | ⭐⭐⭐⭐ |
| **St. Peter & Paul** | Rathausgasse 2, 3011 Bern | 2 (Kirchenschiff, Doppeltürme) | ⭐⭐⭐⭐ |

### Erkannte Zonen-Details

#### Bundeshaus (EGID: 2242547)
- **Arkaden**: 6m (arkade)
- **Hauptgebäude**: 25m (hauptgebaeude)
- **Kuppel**: 64m (kuppel, sonderkonstruktion)

#### Berner Münster (EGID: 1230337)
- **Kirchenschiff**: 28m (hauptgebaeude)
- **Seitenkapellen**: 15m (anbau)
- **Turm**: 100.3m (turm, sonderkonstruktion)

#### St. Peter & Paul (EGID: 191821074)
- **Kirchenschiff**: 22m (hauptgebaeude)
- **Doppeltürme**: 60m (turm)

### Erkenntnisse

1. **Building-Hints sind kritisch**: Ohne spezifische Hinweise für bekannte Gebäude erkennt Claude nur 1-2 Zonen
2. **Echte Höhendaten wichtig**: swissBUILDINGS3D liefert zuverlässige Trauf-/Firsthöhen
3. **Prompt-Selektor funktioniert**: SIMPLE vs COMPLEX wird korrekt unterschieden
4. **SVG-Stil konsistent**: Weisser Hintergrund, Schraffur, blaue Gerüste

### Generierte Test-SVGs

```
docs/showcase/api_test/
├── bundesplatz_3_elevation_complex.svg
├── bundesplatz_3_cross_section_complex.svg
├── kramgasse_10_elevation_complex.svg
├── kramgasse_10_cross_section_complex.svg
├── münsterplatz_1_elevation_complex.svg
├── münsterplatz_1_cross_section_complex.svg
├── rathausgasse_2_elevation_complex.svg
└── rathausgasse_2_cross_section_complex.svg
```

### Test-Script

`backend/scripts/test_improved_prompts.py` - Automatisierter Test mit:
- Geocoding + GWR-Daten
- Echte Höhen aus swissBUILDINGS3D
- Claude-Analyse für komplexe Gebäude
- SVG-Generierung + Speicherung

## Neue Features (Stand 24.12.2025)

### URL-Parameter für Adresse

Die App kann mit vorausgefüllter Adresse aufgerufen werden:
```
https://[app-url]/?address=Bundesplatz%203,%203011%20Bern
```

### Compact-Modus für Grundriss-SVG

Im Gerüstbau-Tab wird das SVG im Compact-Modus gerendert:
- Keine "Gebäudedaten"-Box
- Kleinere Margins → mehr Platz für Polygon
- Kompaktere Fassaden-Labels

## Test-Adressen

### Kantone mit WFS-Unterstützung (Gerüstbau-Daten verfügbar)

| Kanton | Adresse | Höhendaten | WFS |
|--------|-----------------------------------|------------|-----|
| BE | Kramgasse 49, 3011 Bern | DB | ✅ |
| BE | Bundesplatz 3, 3011 Bern | DB | ✅ |
| SO | Hauptgasse 10, 4500 Solothurn | DB | ✅ |
| BS | Marktplatz 10, 4051 Basel | On-Demand | ✅ |
| FR | Rue de Romont 10, 1700 Fribourg | On-Demand | ✅ |
| ZH | Bahnhofstrasse 50, 8001 Zürich | On-Demand | ✅ |
| AG | Bahnhofstrasse 20, 5000 Aarau | On-Demand | ✅ |
| SG | Marktgasse 11, 9000 St. Gallen | On-Demand | ✅ |
| TG | Freiestrasse 10, 8500 Frauenfeld | On-Demand | ✅ |
| BL | Hauptstrasse 50, 4410 Liestal | On-Demand | ✅ |
| SH | Vordergasse 17, 8200 Schaffhausen | On-Demand | ✅ |

### 3D Tiles API Test-Koordinaten

| Region | Koordinaten (WGS84) | Status |
|--------|---------------------|--------|
| Tessin/Graubünden | lat=46.3131, lon=8.4476 | ✅ Funktioniert |
| Wallis | lat=46.2305, lon=10.1451 | ✅ Funktioniert |
| Bern Stadt | lat=46.9466, lon=7.4448 | ❌ Keine Abdeckung |
| Zürich Stadt | lat=47.3769, lon=8.5417 | ❌ Keine Abdeckung |

### Kantone ohne WFS-Unterstützung

| Kanton | Grund |
|--------|-------|
| LU | Keine geodienste.ch WFS-Daten |
| NE | Keine geodienste.ch WFS-Daten |
| GE, VD, VS | Kantonale Geodienste nicht integriert |

## Deployment

**Plattform:** Railway.app
- Backend: FastAPI Container (acceptable-trust-production.up.railway.app)
- Frontend: Nginx mit Vite Build (cooperative-commitment-production.up.railway.app)

### Railway Volume (WICHTIG für Datenpersistenz)

Ein Railway Volume ist konfiguriert unter `/app/data` für persistente SQLite-Datenbanken.
Ohne Volume gehen on-demand importierte Höhendaten bei jedem Deployment verloren!

**Volume einrichten (falls nicht vorhanden):**
```bash
npx @railway/cli login
cd backend
npx @railway/cli link
npx @railway/cli volume add --mount-path /app/data
```

**Datenpersistenz-Übersicht:**

| Daten | Speicherung | Bei Deployment |
|-------|-------------|----------------|
| GWR-Daten (EGID, Geschosse) | Live von swisstopo API | Kein Problem - wird neu abgefragt |
| Gebäudegeometrie (Polygon) | Live von geodienste.ch | Kein Problem - wird neu abgefragt |
| **Gemessene Höhen** | SQLite in Volume | ✅ Bleibt erhalten (mit Volume) |
| Layher-Katalog | SQLite in Volume | ✅ Bleibt erhalten |

## Status (Stand: 30.12.2025)

### Fertig ✅
- [x] Backend + Frontend Deployment
- [x] swissBUILDINGS3D On-Demand Import via STAC API
- [x] Railway Volume für persistente Daten
- [x] SVG-Visualisierungen (Schnitt, Ansicht, Grundriss)
- [x] Fassaden-Auswahl mit interaktivem Grundriss
- [x] NPK 114 Ausmass-Berechnung
- [x] Material-Schätzung (Layher Blitz 70)
- [x] Koordinaten-basierter Höhen-Lookup (für Gebäude ohne EGID)
- [x] Douglas-Peucker Polygon-Vereinfachung
- [x] URL-Parameter für Adresse (?address=...)
- [x] Compact-Modus für Grundriss-SVG
- [x] **Building Context System** (poc_bundeshaus_mvp Branch → main)
  - Pydantic Models (BuildingZone, BuildingContext)
  - SQLite Speicherung (building_contexts.db)
  - Komplexitäts-Erkennung (simple/moderate/complex)
  - Auto-Context für einfache Gebäude
  - Claude API Integration für komplexe Gebäude
  - API Endpoints (GET/POST/PUT/DELETE)
  - Frontend TypeScript Types
  - **Mehrzonenerkennung** bei extremer Höhendifferenz (>15m)
  - **Frontend Zonen-Editor** mit Bearbeitung
- [x] **Gerüstbau-SVG Features** (poc_bundeshaus_mvp Branch → main)
  - Ständerpositionen (alle 2.57m, Layher Blitz 70)
  - Verankerungen (Ecken + alle 4m)
  - Zugänge (Z1-Zn) nach SUVA-Vorschriften (max 50m)
  - Zonen-Farbcodierung im Grundriss
  - Professional-Mode mit Schraffur
- [x] **Claude API SVG-Generierung mit Zonen** (NEU 28.12.2025)
  - Prompt-Selektor System (SIMPLE vs COMPLEX)
  - Building-Hints für bekannte Gebäude
  - Echte Höhendaten aus swissBUILDINGS3D
  - Getestet mit: Bundeshaus, Kramgasse, Münster, St. Peter & Paul
- [x] **swissALTI3D Terrain-Integration** (NEU 28.12.2025)
  - TerrainService in `backend/app/services/terrain.py`
  - Terrain-Höhe bei Geocoding (automatisch, m ü.M.)
  - API Endpoints: `/api/v1/terrain/height`, `/api/v1/terrain/profile`
  - In SVG-Prompts: Absolute Höhenkoten (m ü.M.)
- [x] **Dachneigung-Berechnung Option C** (NEU 28.12.2025)
  - RoofService in `backend/app/services/roof.py`
  - Heuristische Berechnung aus Trauf-/Firsthöhe
  - Dachform-Klassifikation (Flach, Sattel, Walm, Pult)
  - Dachausrichtung aus Polygon-Geometrie
  - Im Scaffolding-Response als `roof` Objekt
- [x] **Orthofoto-Service & Claude-Analyse Integration** (NEU 28.12.2025)
  - OrthofotoService in `backend/app/services/orthofoto.py`
  - swisstopo WMS für Luftbilder
  - Integration in Claude-Analyse (`include_orthofoto=True`)
  - Neuer ZoneType: `INNENHOF` (nicht einrüsten)
  - Orthofoto-spezifische Analyse (Dachaufbauten, Innenhöfe, Zugangsprobleme)
  - Kosten: ~$0.01-0.02 ohne, ~$0.05-0.10 mit Orthofoto
- [x] **SVG Prompt-System V2.0** (NEU 29.12.2025)
  - Separate Prompts: `terrain_prompt.py`, `environment_prompt.py`
  - Zwei Schraffur-Typen: `url(#hatch)` vs. `url(#cut-hatch)`
  - ASCII-Diagramme für Fassade vs. Schnitt Unterscheidung
  - Verdeckungsregel: Vorne verdeckt hinten
  - Bounding-Box Berechnung für komplexe Polygone
  - Terrain-Höhe in m ü.M. Referenz
- [x] **Intelligente Datenbank** (NEU 29.12.2025)
  - `intelligent_db.py` Service für erweiterte DB-Funktionen
  - Smarte Suche: Alias-Match → FTS5 → Geocoding-Fallback
  - SVG-Cache mit Versionierung und Cache-Invalidierung
  - Umgebungsdaten-Cache (Nachbargebäude, blockierte Fassaden)
  - Claude-Recherche-Cache (Wiederverwendung von API-Ergebnissen)
  - Landmark-Buildings Seed-Daten (Bundeshaus, Münster, etc.)
  - API-Endpoints: `/api/v1/search`, `/api/v1/building/{egid}/svg/*`, `/api/v1/db/stats`
- [x] **Einheitliches Prompt-System v3.0** (NEU 29.12.2025)
  - `research_service.py` - Dynamische Gebäude-Recherche via Claude Haiku
  - `prompt_builder.py` - Template-basiert nach `Export_Prompt_Claude.md`
  - `claude_svg_zones.py` - Nutzt jetzt PromptBuilder (identische Prompts)
  - Ersetzt statische `building_hints.py` durch dynamische Recherche
  - 30 Tage Cache für Recherche-Ergebnisse (~$0.01-0.02 pro Gebäude)
  - Frontend Export nutzt Backend-API für konsistente Prompts
  - **"Professional" Toggle entfernt** - Claude wird immer für Schnitt/Ansicht verwendet
  - Backend `use_claude` Default geändert auf `True`
  - API-Endpoints: `/api/v1/prompt/generate`, `/api/v1/prompt/research/stats`
- [x] **SmartBuildingService** (NEU 29.12.2025)
  - Zentraler Service für schrittweise Gebäudedaten-Sammlung
  - 10-Schritte Pipeline: Geocoding → GWR → Höhen → Terrain → Polygon → Dach → Recherche → Zonen → Zugänge → Qualität
  - `smart_building/models.py` - BuildingDataBundle, ZoneInfo, TerrainProfile
  - `smart_building/service.py` - Orchestrierung aller Datenquellen
  - `smart_building/prompt_generator.py` - Einheitliche Prompt-Generierung
  - `smart_building/known_buildings.py` - Bekannte Gebäude-Cache (NEU 30.12.2025)
  - `smart_building/research_integration.py` - Kirchen-Zonen + bekannte Gebäude Integration (NEU 30.12.2025)
  - Bundle-Caching (24h TTL) in SQLite
  - Komplexitäts-Erkennung: simple → auto-zone, complex → Claude Sonnet Analyse
  - SUVA-konforme Zugangspunkt-Berechnung
  - API-Endpoints: `/api/v1/smart-building/data`, `/api/v1/smart-building/prompt`, `/api/v1/smart-building/cache/stats`
  - Integration in `claude_svg_zones.py`: `generate_svg_with_smart_service()`
- [x] **Frontend SmartService Integration** (NEU 29.12.2025)
  - Frontend ruft direkt `/api/v1/smart-building/data` auf (statt `/api/v1/scaffolding`)
  - TypeScript: `SmartBuildingData` Interface in `types.ts`
  - Konverter-Funktion: `smartToScaffoldingData()` für Abwärtskompatibilität
  - Visualisierungs-Endpunkte nutzen SmartService Cache
  - `/api/v1/scaffolding` als **deprecated** markiert
- [x] **5 Claude.ai Analyse-Fixes** (NEU 30.12.2025)
  - Fix 1: UTF-8 Encoding (FastAPI Standard)
  - Fix 2: Prompt-Konsolidierung mit SVGType.ALL
  - Fix 3: "RECHERCHIEREN" entfernt, sinnvoller Fallback in prompt_generator.py
  - Fix 4: Kirchen-spezifische Zonen (Seitenschiffe, Kirchenschiff, Turm)
  - Fix 5: Bekannte Gebäude-Cache (known_buildings.py)
  - Bundeshaus, Münster, Zytglogge, St. Peter & Paul mit korrekten Höhenzonen
  - Priorisierung: Bekannte Gebäude → Claude Recherche → Standard-Zonen

### API Migration (29.12.2025)

| Alt (deprecated) | Neu (empfohlen) |
|------------------|-----------------|
| `GET /api/v1/scaffolding?address=...` | `GET /api/v1/smart-building/data?address=...` |
| `GET /api/v1/scaffolding/by-egid/{egid}` | `GET /api/v1/smart-building/data?address=...` |
| Separate Datensammlung pro Endpunkt | Einheitlicher Bundle-Cache (24h) |

### In Arbeit 🔨
- [ ] SVG-Visualisierung: Qualität wie Claude.ai Referenz-SVGs
  - Separate Gebäudeteile statt 1 Polygon (teilweise gelöst durch Zonen)
  - Ehrenhof/Innenhöfe markieren
  - Masslinien mit Pfeilen
  - Detaillierte Legende

### Geplant 🔜
- [ ] **Sonnendach-Import (Option A)** - Dachneigung/Ausrichtung aus BFE-Daten
- [ ] **swissBUILDINGS3D 3D-Analyse (Option B)** - Präzise Dachgeometrie
- [ ] **DXF/IFC-Export** - 3D-Modellierung
- [ ] Custom Domain

## ACHTUNG: Technische Schulden

### Höhendatenbank - Drei Tabellen

Es gibt **drei** SQLite-Tabellen für Höhendaten in `building_heights.db`:

1. **`building_heights`** (Legacy, EGID-basiert)
   - Felder: `egid`, `height_m`, `height_type`, `source`
   - Einfache Struktur, nur eine Höhe pro Gebäude
   - **Status:** Wird noch unterstützt als Fallback

2. **`building_heights_detailed`** (EGID-basiert)
   - Felder: `egid`, `traufhoehe_m`, `firsthoehe_m`, `gebaeudehoehe_m`, `dach_max_m`, `dach_min_m`, `terrain_m`, `source`
   - Detaillierte Struktur für Gerüstbau
   - **Status:** Primäre Tabelle für EGID-Lookups

3. **`building_heights_by_coord`** (Koordinaten-basiert, NEU)
   - Felder: `lv95_e`, `lv95_n`, `uuid`, `traufhoehe_m`, `firsthoehe_m`, `gebaeudehoehe_m`, ...
   - Für Gebäude ohne EGID in swissBUILDINGS3D
   - **Status:** Fallback wenn EGID-Lookup fehlschlägt

**Lookup-Reihenfolge in `geodienste.py`:**
1. `building_heights_detailed` (per EGID)
2. `building_heights` (per EGID, Legacy)
3. `building_heights_by_coord` (per Koordinaten ±25m)

**TODO (optional):** Legacy-Tabelle `building_heights` kann entfernt werden, sobald alle Daten in `_detailed` migriert sind.

### Debug-Code (Stand 23.12.2025)

Debug-Code aus Backend entfernt:
- ✅ `_height_debug` aus API Response entfernt (`geodienste.py`)
- ✅ Debug-Prints aus `height_fetcher.py` entfernt
- `[DEBUG]` Console-Logs im Frontend (`App.tsx`) können optional entfernt werden

### 3D-Viewer-URL Format (Stand 23.12.2025)

**Entscheidung:** LV95-Format mit `sr=2056` verwenden.

```
https://map.geo.admin.ch/#/map?lang=de&sr=2056&center={E},{N}&z=13&bgLayer=ch.swisstopo.pixelkarte-farbe&3d
```

**Getestete Alternativen (funktionieren NICHT zuverlässig):**

| Format | Problem |
|--------|---------|
| `camera=lon,lat,height,pitch` | Ungültiges Format laut map.geo.admin.ch |
| `center=...&z=20&3d=true` | z=20 ungültig (max z=13), `3d=true` statt `3d` |
| `camera=lon,lat,elevation,pitch,,&3d` | Browser-abhängige Probleme, Koordinaten werden verfälscht |

**Warum LV95 (`sr=2056`):**
- Zuverlässig in allen Browsern (getestet normal + Inkognito)
- Offizielle Schweizer Koordinaten (EPSG:2056)
- Zoom z=13 ist Maximum laut docs.geo.admin.ch
- `&3d` aktiviert 3D-Modus (nicht `&3d=true`)

**Nachteil:** Keine Kontrolle über Kamera-Winkel (immer Draufsicht). Das `camera`-Format würde schräge Ansichten erlauben, funktioniert aber nicht zuverlässig.

## Lokale Entwicklung

```bash
# Backend (Terminal 1)
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
