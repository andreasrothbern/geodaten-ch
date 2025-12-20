# 🇨🇭 Geodaten Schweiz

Full-Stack Anwendung für Schweizer Geodaten (Gebäude, Adressen, Grundstücke).

## 📦 Projektstruktur

```
geodaten-ch/
├── backend/          # FastAPI Backend
│   ├── app/
│   │   ├── main.py           # API Endpunkte
│   │   ├── models/           # Pydantic Schemas
│   │   └── services/         # swisstopo Adapter, Cache
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/         # React + Vite Frontend
│   ├── src/
│   │   ├── App.tsx           # Haupt-App
│   │   ├── components/       # React Komponenten
│   │   └── types.ts          # TypeScript Types
│   ├── Dockerfile
│   └── package.json
└── railway.toml      # Railway.app Deployment Config
```

## 🚀 Lokale Entwicklung

### Backend starten

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API Docs: http://localhost:8000/docs

### Frontend starten

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

## 🌐 Deployment auf Railway.app

### 1. Repository erstellen

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

### 2. Railway Projekt erstellen

1. [Railway.app](https://railway.app) öffnen
2. "New Project" → "Deploy from GitHub repo"
3. Repository auswählen
4. Railway erkennt automatisch Backend und Frontend

### 3. Environment Variables setzen

**Backend Service:**
- Keine speziellen Variablen nötig

**Frontend Service:**
- `VITE_API_URL` = `https://<backend-service>.railway.app`

### 4. Custom Domains (optional)

- Backend: `api.geodaten.ch`
- Frontend: `geodaten.ch`

## 📡 API Endpunkte

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/health` | Health Check |
| GET | `/api/v1/address/search?q=...` | Adresssuche |
| GET | `/api/v1/geocode?address=...` | Geokodierung |
| GET | `/api/v1/building/egid/{egid}` | Gebäude per EGID |
| GET | `/api/v1/building/at?x=...&y=...` | Gebäude an Koordinate |
| GET | `/api/v1/building/search?q=...` | Gebäudesuche |
| GET | `/api/v1/lookup?address=...` | Kombinierte Abfrage |

## 🗂️ Datenquellen

- **swisstopo / geo.admin.ch** - Primäre Datenquelle
- **GWR** - Eidg. Gebäude- und Wohnungsregister

## 📄 Lizenz

Daten: © swisstopo, BFS/GWR
