# Entwicklungsumgebung

## Projekt-Pfade

```
C:/Users/vonro/projects/lawil/geodaten-ch/
├── backend/              # FastAPI (Port 8000)
├── geruestbau-app/       # React (Port 3001) ← Primäres Frontend
└── frontend/             # React (Port 3000) - Geodaten-Viewer
```

## Start-Befehle

### Backend starten
```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend
"C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/python.exe" -m uvicorn app.main:app --reload --port 8000
```

### geruestbau-app starten (primäres Frontend)

**WICHTIG:** Vor dem Starten IMMER Build ausführen um Änderungen zu validieren!

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app

# 1. Build prüfen (TypeScript-Fehler erkennen)
npm run build

# 2. Dev-Server starten (im Background für Claude)
npm run dev -- --port 3001
```

Das Frontend MUSS auf Port 3001 laufen (nicht 3002, 3003, etc.)!

## Stop-Befehle (Windows)

**ACHTUNG für Claude:** NIEMALS `taskkill /F /IM node.exe` verwenden!
Das würde auch den Claude Code Prozess selbst beenden.

### Sicheres Stoppen (für Claude)

```bash
# 1. Port-basiert stoppen (SICHER - nur spezifischen Prozess)
netstat -ano | findstr :3001
taskkill /F /PID <PID>

# 2. Alternativ: Vite-Prozess finden und stoppen
wmic process where "commandline like '%vite%'" get processid,commandline
taskkill /F /PID <PID>
```

### Manuelles Stoppen (für User)

```bash
# Alle Node-Prozesse (NICHT für Claude!)
taskkill /F /IM node.exe

# Python-Prozess auf Port 8000
netstat -ano | findstr :8000
taskkill /F /PID <PID>
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
