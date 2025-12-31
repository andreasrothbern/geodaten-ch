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
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD Pipeline (GitHub Actions)
│
├── backend/                    # FastAPI + Python 3.11
│   ├── app/
│   │   ├── main.py             # API Endpunkte
│   │   ├── models/             # Pydantic Schemas
│   │   ├── routers/
│   │   │   └── geruestbau.py   # Gerüstbau-API Router
│   │   ├── services/           # Business Logic
│   │   │   ├── smart_building/ # SmartBuildingService
│   │   │   └── geruestbau/     # Projekt-Service
│   │   └── data/               # SQLite Datenbanken
│   ├── tests/
│   │   └── test_geruestbau.py  # API Tests
│   └── scripts/                # Import-Skripte
│
├── frontend/                   # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│
├── geruestbau-app/             # Mobile-First PWA (NEU)
│   ├── src/
│   │   ├── api/                # API Client
│   │   ├── components/         # UI-Komponenten
│   │   ├── pages/              # Seiten
│   │   ├── stores/             # Zustand State
│   │   └── types/              # TypeScript Types
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── README.md               # Entwickler-Guide
│
├── docs/
│   └── geruestbau-app/         # Setup-Guides
│
├── CLAUDE.md                   # Technische Dokumentation
├── CLAUDE_GERUESTBAU.md        # Gerüstbau-Erweiterung
└── PROJEKT_KONTEXT.md          # Projekt-Überblick
```

## Dokumentation

| Dokument | Beschreibung |
|----------|--------------|
| **CLAUDE.md** | Vollständige technische Dokumentation |
| **CLAUDE_GERUESTBAU.md** | Gerüstbau-Modul Erweiterung |
| **PROJEKT_KONTEXT.md** | Projekt-Überblick für Claude.ai |
| **geruestbau-app/README.md** | PWA-Entwickler-Guide |
| **docs/geruestbau-app/** | Setup-Guides, Quickstart |

## Gerüstbau-App (PWA)

Mobile-First Progressive Web App für Gerüstbau-Projekterfassung.

```bash
cd geruestbau-app
npm install
npm run dev
# → http://localhost:3001
```

**Tech Stack:** React 18, TypeScript, Vite 5, TailwindCSS, Zustand, vite-plugin-pwa

## CI/CD Pipeline

GitHub Actions testet alle 3 Komponenten parallel bei Push/PR zu `main`:

| Job | Beschreibung |
|-----|--------------|
| `backend-test` | Python 3.11 + pytest |
| `frontend-test` | Node 20 + npm build |
| `geruestbau-test` | Node 20 + npm build/test |
| `deploy` | Railway.app (bei main push) |

Konfiguration: `.github/workflows/ci.yml`

## Datenquellen & Lizenzen

- **swisstopo:** [Open Government Data](https://www.swisstopo.admin.ch/de/geodata.html)
- **BFS GWR:** [Gebäude- und Wohnungsregister](https://www.housing-stat.ch/)
- **geodienste.ch:** [Amtliche Vermessung](https://geodienste.ch/)
