
# Entwicklungsumgebung - Schnellstart

> **Für Claude Code:** Dieses Dokument enthält alle Befehle zum Starten/Stoppen der Entwicklungsumgebung.

## Verzeichnisstruktur

```
geodaten-ch/
├── backend/              # FastAPI Backend (Port 8000)
│   ├── venv/             # Python Virtual Environment
│   ├── requirements.txt  # Python Dependencies
│   └── app/              # FastAPI Applikation
│
├── frontend/             # React Frontend (geodaten-viewer)
│   └── package.json
│
└── geruestbau-app/       # React Frontend (Gerüstbau-Konfigurator)
    └── package.json      # Port 3001 (primär)
```

## Schnellstart-Befehle

### Backend starten (Port 8000) - WICHTIG: DuckDB-Modus

**NEU 13.01.2026:** Das Backend MUSS mit `USE_DUCKDB=true` gestartet werden!

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend

# Windows CMD:
set USE_DUCKDB=true && ".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000

# PowerShell:
$env:USE_DUCKDB="true"; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> **Ohne `USE_DUCKDB=true`** wird SQLite verwendet (Legacy-Modus).

### geruestbau-app starten (Port 3001)

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app
npm run dev -- --port 3001
```

### geodaten-viewer starten (Port 3000)

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/frontend
npm run dev
```

## Prozesse stoppen (Windows)

### Alle Node-Prozesse stoppen
```bash
taskkill /F /IM node.exe
```

### Alle Python-Prozesse stoppen
```bash
taskkill /F /IM python.exe
```

### Spezifischen Port freigeben
```bash
# Port 8000 freigeben
netstat -ano | findstr :8000
# Dann mit der PID:
taskkill /F /PID <PID>
```

## Dependencies installieren

### Backend (einmalig nach Clone)

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend

# venv erstellen (falls nicht vorhanden)
python -m venv venv

# Dependencies installieren
"C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/pip.exe" install -r requirements.txt
```

**Bekannte Probleme:**
- Python 3.13 hat Kompatibilitätsprobleme mit einigen Packages (pydantic-core, uvloop)
- Lösung: Dependencies ohne strikte Versionen installieren:
  ```bash
  pip install fastapi pydantic python-dotenv httpx uvicorn geopandas fiona anthropic
  ```

### Frontend (einmalig nach Clone)

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app
npm install

cd C:/Users/vonro/projects/lawil/geodaten-ch/frontend
npm install
```

## Typische Entwicklungs-Session

```bash
# 1. Backend starten MIT DuckDB (neues Terminal)
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend
set USE_DUCKDB=true && venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# 2. Frontend starten (neues Terminal)
cd C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app
npm run dev -- --port 3001

# 3. Browser öffnen
# http://localhost:3001   - geruestbau-app
# http://localhost:8000/docs - API Dokumentation
```

## Port-Belegung

| Service | Port | Beschreibung |
|---------|------|--------------|
| Backend | 8000 | FastAPI (uvicorn) |
| geruestbau-app | 3001 | Gerüst-Konfigurator |
| frontend | 3000 | Geodaten-Viewer |

## Troubleshooting

### "Port bereits belegt"

```bash
# Windows: Prozess auf Port finden
netstat -ano | findstr :8000

# Prozess beenden
taskkill /F /PID <PID>
```

### "ModuleNotFoundError"

```bash
# Prüfen ob venv aktiv ist
which python  # Sollte auf venv zeigen

# Dependencies neu installieren
pip install -r requirements.txt
```

### Backend startet nicht

1. Prüfe ob Port 8000 frei ist
2. Prüfe ob venv aktiviert ist
3. Prüfe `.env` Datei (ANTHROPIC_API_KEY etc.)

## Umgebungsvariablen (.env)

```bash
# backend/.env
ANTHROPIC_API_KEY=sk-...
```

## Tests ausführen

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend

# Alle Tests
venv\Scripts\python.exe -m pytest tests/ -v

# Einzelner Test
venv\Scripts\python.exe -m pytest tests/test_integration.py -v

# E2E Tests geruestbau-app
venv\Scripts\python.exe -m pytest tests/test_geruesbau_e2e.py -v

```
