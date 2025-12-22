# CLAUDE.md - Projekt-Kontext für Claude Code

## Projekt: Geodaten Schweiz

Dieses Projekt bietet eine API und Web-App für Schweizer Geodaten (Gebäude, Adressen, Grundstücke).

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

## GWR-Daten (verfügbare Felder)

- `egid` - Eidg. Gebäudeidentifikator
- `strname`, `deinr` - Strasse, Hausnummer
- `dplz4`, `ggdename` - PLZ, Ort
- `gdekt` - Kanton
- `gbauj` - Baujahr
- `gkat` - Gebäudekategorie (1020=EFH, 1030=MFH)
- `gastw` - Anzahl Geschosse
- `ganzwhg` - Anzahl Wohnungen
- `garea` - Gebäudefläche m²
- `gwaerzh1` - Heizungsart
- `genh1` - Energieträger Heizung

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

### Datenquellen für Höhen (Fallback-Kette)

1. **Manuell eingegeben** - Höchste Priorität
2. **swissBUILDINGS3D** - Gemessene Höhe aus lokaler DB
3. **Berechnet aus Geschossen** - GWR-Daten × Geschosshöhe
4. **Standard nach Kategorie** - EFH: 8m, MFH: 12m
5. **Allgemeiner Standard** - 10m

### swissBUILDINGS3D Import

```bash
# Daten von swisstopo herunterladen:
# https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta

# Import ausführen
cd backend
python scripts/import_building_heights.py daten.gml --canton BE
```

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

## Status (Stand: Dezember 2025)

- [x] Backend + Frontend Deployment
- [x] swissBUILDINGS3D On-Demand Import via STAC API
- [x] Railway Volume für persistente Daten
- [x] SVG-Visualisierungen (Schnitt, Ansicht, Grundriss)
- [x] Fassaden-Auswahl mit interaktivem Grundriss
- [x] NPK 114 Ausmass-Berechnung
- [x] Material-Schätzung (Layher Blitz 70)
- [ ] Gerüstkonfiguration → Berechnung (Arbeitstyp, Gerüstart, Breitenklasse)
- [ ] Custom Domain

## ACHTUNG: Technische Schulden

### Höhendatenbank - Zwei Tabellen (BEREINIGEN!)

Es gibt **zwei** SQLite-Tabellen für Höhendaten in `building_heights.db`:

1. **`building_heights`** (Legacy)
   - Felder: `egid`, `height_m`, `height_type`, `source`
   - Einfache Struktur, nur eine Höhe pro Gebäude

2. **`building_heights_detailed`** (Neu)
   - Felder: `egid`, `traufhoehe_m`, `firsthoehe_m`, `gebaeudehoehe_m`, `dach_max_m`, `dach_min_m`, `terrain_m`, `source`
   - Detaillierte Struktur für Gerüstbau

**Problem:** Der On-Demand Import schreibt in BEIDE Tabellen, aber nicht immer konsistent. Die Abfrage in `geodienste.py` prüft zuerst `detailed`, dann `legacy` als Fallback.

**TODO:** Eine der Tabellen entfernen und nur noch `building_heights_detailed` verwenden. Die Legacy-Tabelle migrieren oder löschen.

### Debug-Code entfernen

Nach dem Fix vom 22.12.2025 gibt es temporären Debug-Code:
- `_height_debug` in API Response (`geodienste.py`)
- `[DEBUG]` Console-Logs im Frontend (`App.tsx`)

Kann entfernt werden sobald das Höhen-Feature stabil läuft.

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
