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
│       └── services/
│           ├── swisstopo.py  # swisstopo API Adapter
│           └── cache.py      # SQLite Cache
│
├── frontend/         # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│
└── railway.toml      # Railway.app Deployment
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

## Deployment

**Ziel:** Railway.app
- Backend: FastAPI Container
- Frontend: Nginx mit Vite Build
- Kosten: ~$10-15/Monat

## Nächste Schritte

1. [ ] Backend lokal testen: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
2. [ ] Frontend lokal testen: `cd frontend && npm install && npm run dev`
3. [ ] Git Repository erstellen
4. [ ] Railway.app Deployment
5. [ ] Custom Domain einrichten

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
