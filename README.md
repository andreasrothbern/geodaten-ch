# Geodaten Schweiz - Gerüstbau-Modul

API und Web-App für Schweizer Geodaten mit Fokus auf Gerüstbau-Berechnungen.

## Live Demo

- **Frontend:** https://cooperative-commitment-production.up.railway.app
- **Backend API:** https://acceptable-trust-production.up.railway.app
- **Mit Adresse:** `?address=Bundesplatz%203,%203011%20Bern`

## API-Dokumentation

- **Swagger UI:** https://acceptable-trust-production.up.railway.app/docs
- **ReDoc:** https://acceptable-trust-production.up.railway.app/redoc

## Lokale Entwicklung

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Import-Skripte

### swissBUILDINGS3D Höhendaten

```bash
# Daten von swisstopo herunterladen:
# https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta

cd backend
python scripts/import_building_heights.py daten.gml --canton BE
```

## Deployment (Railway.app)

### Volume für Datenpersistenz

Ein Railway Volume ist unter `/app/data` konfiguriert für persistente SQLite-Datenbanken.

**Volume einrichten (einmalig):**

```bash
npm install -g @railway/cli
npx @railway/cli login
cd backend
npx @railway/cli link
npx @railway/cli volume add --mount-path /app/data
```

**Gespeicherte Daten im Volume:**
- `building_heights.db` - swissBUILDINGS3D Höhen
- `building_contexts.db` - Gebäude-Kontexte und SVG-Cache
- `layher_catalog.db` - Gerüst-Materialkatalog

## Architektur

```
geodaten-ch/
├── backend/                 # FastAPI + Python 3.11
│   ├── app/
│   │   ├── main.py         # API Endpunkte
│   │   ├── models/         # Pydantic Schemas
│   │   ├── services/       # Business Logic
│   │   └── data/           # SQLite Datenbanken
│   └── scripts/            # Import-Skripte
│
├── frontend/               # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│
└── CLAUDE.md               # Technische Dokumentation
```

## Dokumentation

- **CLAUDE.md** - Vollständige technische Dokumentation (API-Details, Datenquellen, Implementierung)
- **PROJEKT_KONTEXT.md** - Projekt-Überblick für Claude.ai

## Datenquellen & Lizenzen

- **swisstopo:** [Open Government Data](https://www.swisstopo.admin.ch/de/geodata.html)
- **BFS GWR:** [Gebäude- und Wohnungsregister](https://www.housing-stat.ch/)
- **geodienste.ch:** [Amtliche Vermessung](https://geodienste.ch/)
