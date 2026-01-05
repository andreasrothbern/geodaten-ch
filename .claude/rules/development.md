# Entwicklungsumgebung

## Projekt-Pfade

```
C:/Users/vonro/projects/lawil/geodaten-ch/
├── backend/              # FastAPI (Port 8000)
├── geruestbau-app/       # React (Port 3001) ← Primäres Frontend
└── frontend/             # React (Port 3000) - Geodaten-Viewer
```

## Start-Befehle

**WICHTIG:** Vor dem Starten IMMER zuerst alle alten Prozesse stoppen:
```bash
taskkill /F /IM node.exe
```
Das Frontend MUSS auf Port 3001 laufen (nicht 3002, 3003, etc.)!

### Backend starten
```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend
"C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/python.exe" -m uvicorn app.main:app --reload --port 8000
```

### geruestbau-app starten (primäres Frontend)
```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app
npm run dev -- --port 3001
```

## Stop-Befehle (Windows)

```bash
# Alle Node-Prozesse
taskkill /F /IM node.exe

# Alle Python-Prozesse
taskkill /F /PID <PID>  # PID von netstat -ano | findstr :8000
```

## Dependencies

### Backend (bei ModuleNotFoundError)
```bash
"C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/pip.exe" install fastapi pydantic python-dotenv httpx uvicorn geopandas fiona anthropic pytest pytest-asyncio
```

### Frontend (bei npm Fehlern)
```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app && npm install
```

## Typische Session-Reihenfolge

1. **Alte Prozesse stoppen** (falls blockiert)
2. **Backend starten** (Port 8000)
3. **Frontend starten** (Port 3001)

## Port-Konflikte beheben

```bash
# Port prüfen
netstat -ano | findstr :8000

# Prozess beenden
taskkill /F /PID <PID>
```
