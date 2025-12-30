# CLAUDE.md - Projekt-Kontext für Claude Code

## Modulare Dokumentation

Detaillierte Regeln sind in `.claude/rules/` aufgeteilt:

| Datei | Inhalt |
|-------|--------|
| [formatting.md](.claude/rules/formatting.md) | Umlaute, Encoding, Code-Style |
| [api-standards.md](.claude/rules/api-standards.md) | Endpunkte, Response-Format |
| [data-sources.md](.claude/rules/data-sources.md) | swisstopo, geodienste, Höhen |
| [smart-building.md](.claude/rules/smart-building.md) | 10-Schritte Pipeline, Zonen |
| [svg-generation.md](.claude/rules/svg-generation.md) | Stil-Vorgaben, Farben, Patterns |

### Wichtigste Rule: Formatierung
**Umlaute:** Immer äöü verwenden, NICHT ae/oe/ue!

### Weitere Dokumentation

| Datei | Inhalt |
|-------|--------|
| [docs/tests/README.md](docs/tests/README.md) | Building Comparison Teststrategie |
| [docs/roadmap/CURRENT_BUGS.md](docs/roadmap/CURRENT_BUGS.md) | Aktuelle Bugs und Fixes |
| [docs/roadmap/ML_LEARNING_SYSTEM.md](docs/roadmap/ML_LEARNING_SYSTEM.md) | ML Learning System (geplant) |

---

## Projekt: Geodaten Schweiz

Dieses Projekt bietet eine API und Web-App für Schweizer Geodaten (Gebäude, Adressen, Grundstücke).

**Deployment auf Railway.app:**
- Frontend: https://cooperative-commitment-production.up.railway.app/
- Backend: https://acceptable-trust-production.up.railway.app/
- Mit Adresse: `?address=Bundesplatz%203,%203011%20Bern`

---

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

---

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

---

## Integrierte Datenquellen

| Quelle | Daten | Genauigkeit | Status |
|--------|-------|-------------|--------|
| **swisstopo API** | Geokodierung, GWR, Terrain | ±1m | Live-API |
| **GWR (BFS)** | EGID, Adresse, Geschosse, Kategorie, Baujahr | Amtlich, aktuell | via swisstopo |
| **geodienste.ch WFS** | Gebäudegrundriss (Polygon) | ±10cm (AV-Daten) | Live-API |
| **swissBUILDINGS3D 3.0** | Gemessene Gebäudehöhe | ±50cm (Photogrammetrie) | DB + On-Demand |
| **swissALTI3D** | Terrain-Höhen (m ü.M.) | ±0.5m (LiDAR) | Live-API |

### Datengenauigkeit

| Messwert | Quelle | Genauigkeit |
|----------|--------|-------------|
| Gebäudehöhe (gemessen) | swissBUILDINGS3D | ±0.5m |
| Gebäudehöhe (geschätzt) | Geschosse × 3.2m | ±2-3m |
| Terrain-Höhe | swissALTI3D | ±0.5m |
| Fassadenlänge | AV-Grundriss | ±10cm |
| Grundfläche | AV-Grundriss | ±0.1m² |
| Koordinaten | LV95 | ±1m |

---

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
│           ├── geodienste.py # geodienste.ch WFS
│           ├── terrain.py    # swissALTI3D Terrain-Höhen
│           ├── height_db.py  # Höhendatenbank Service
│           ├── cache.py      # SQLite Cache
│           └── smart_building/
│               ├── service.py           # Orchestrierung
│               ├── models.py            # BuildingDataBundle
│               ├── prompt_generator.py  # Prompt-Aufbau
│               ├── known_buildings.py   # Bekannte Gebäude
│               └── research_integration.py
│
├── frontend/         # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│
├── .claude/
│   └── rules/        # Modulare Dokumentation
│
└── docs/
    ├── tests/
    └── roadmap/
```

---

## API-Endpunkte

### SmartBuildingService (empfohlen)

```python
# Alle Gebäudedaten sammeln
GET /api/v1/smart-building/data?address=Bundesplatz 3, 3011 Bern
    &force_refresh=false   # Bundle-Cache ignorieren
    &include_research=true # Claude-Recherche einbeziehen
    &include_zones=true    # Zonen-Analyse einbeziehen
    &include_terrain=true  # Terrain-Daten einbeziehen

# Einheitlichen Prompt generieren
GET /api/v1/smart-building/prompt?address=...&svg_type=all

# Cache-Statistiken
GET /api/v1/smart-building/cache/stats
```

### SVG-Visualisierung

```python
GET /api/v1/visualize/floor-plan?address=...    # Grundriss
GET /api/v1/visualize/cross-section?address=... # Schnitt
GET /api/v1/visualize/elevation?address=...     # Ansicht
```

### Terrain

```python
GET /api/v1/terrain/height?e=2600423&n=1199521
GET /api/v1/terrain/profile?start_e=...&start_n=...&end_e=...&end_n=...
```

---

## Bekannte Gebäude

Definiert in `backend/app/services/smart_building/known_buildings.py`:

| Gebäude | EGID | Zonen |
|---------|------|-------|
| Bundeshaus | 2242547 | Arkaden, Hauptgebäude, Kuppel |
| Berner Münster | 1230337 | Kirchenschiff, Seitenkapellen, Turm |
| St. Peter & Paul | 191821074 | Kirchenschiff, Seitenschiffe, Westturm |
| Zytglogge | 1017961 | Torhaus, Turm |
| Einsteinhaus | - | Hauptgebäude |

---

## SVG Style-Vorgaben

| Element | Farbe | Verwendung |
|---------|-------|------------|
| Hintergrund | #FFFFFF | Immer weiss |
| Gebäude-Füllung | url(#hatch) | Schraffur-Pattern |
| Gerüst-Ständer | #0066CC | Blau |
| Verankerung | #CC0000 | Rot, gestrichelt |
| Beläge | #8B4513 | Braun |
| Kuppel | url(#copper) | Kupfer-Gradient |

### Patterns (in `<defs>`)

```xml
<!-- Schraffur für Gebäude -->
<pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
  <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
</pattern>

<!-- Schnittflächen (dichter) -->
<pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
  <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
</pattern>

<!-- Terrain/Boden -->
<pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
  <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
</pattern>

<!-- Kupfer-Gradient NUR für Kuppeln -->
<linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0%" style="stop-color:#7CB9A5"/>
  <stop offset="100%" style="stop-color:#4A8A77"/>
</linearGradient>
```

---

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

---

## Technische Schulden

### Höhendatenbank - Drei Tabellen

Es gibt **drei** SQLite-Tabellen für Höhendaten in `building_heights.db`:

1. **`building_heights`** (Legacy, EGID-basiert) - Fallback
2. **`building_heights_detailed`** (EGID-basiert) - Primär
3. **`building_heights_by_coord`** (Koordinaten-basiert) - Für Gebäude ohne EGID

**Lookup-Reihenfolge:**
1. `building_heights_detailed` (per EGID)
2. `building_heights` (per EGID, Legacy)
3. `building_heights_by_coord` (per Koordinaten ±50m)
4. On-Demand STAC API Fetch
5. Geschätzt aus GWR

---

*Für aktuellen Projektstand, Bugs und Roadmap: siehe [PROJEKT_KONTEXT.md](PROJEKT_KONTEXT.md)*
