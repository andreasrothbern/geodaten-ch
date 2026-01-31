# Entwicklungsumgebung

**Stand 28.01.2026 00:50**

## Projekt-Pfade

```
C:/Users/vonro/projects/lawil/geodaten-ch/
├── backend/              # FastAPI (Port 8000)
├── geruestbau-app/       # React (Port 3001) ← Primäres Frontend
└── frontend/             # React (Port 3000) - Geodaten-Viewer
```

---

## SCHNELLSTART (für Claude)

### 1. STOP - Alle Prozesse beenden

```bash
# SCHRITT 1: Alle Python-Prozesse auflisten
wmic process where "name='python.exe'" get ProcessId,CommandLine 2>nul

# SCHRITT 2: PIDs notieren und beenden (Git Bash kompatibel!)
cmd //c "taskkill /PID <PID1> /PID <PID2> /F"

# SCHRITT 3: Prüfen ob Port frei
netstat -ano | findstr :8000 || echo "Port 8000 frei"
```

### 2. RESET - Caches löschen (optional, bei Datenproblemen)

```bash
# WICHTIG: Backend MUSS gestoppt sein!
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend/app/data

# Alle Cache-DBs löschen (NICHT geruestbau.db!)
del /F /Q building_3d.db building_3d.duckdb tiles.db 2>nul
rmdir /S /Q tiles 2>nul
echo "Caches gelöscht"
```

### 3. START - Backend starten

**WICHTIG 28.01.2026 00:50:** Für Entwicklung OHNE `--workers` und OHNE `--reload` starten!
- `--reload` verursacht Datei-Konflikte beim Editieren
- `--workers N` verursacht DuckDB-Datei-Locks (Multi-Prozess nicht unterstützt)
- Bei Code-Änderungen: Backend stoppen + neu starten

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend && "C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/python.exe" -m uvicorn app.main:app --port 8000
```

### 4. TEST - Prüfen ob Backend läuft

```bash
powershell -Command "(Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing).StatusCode"
# Erwartete Ausgabe: 200
```

---

## Detaillierte Befehle

### Backend starten

**Stand 28.01.2026 00:50:**
- DuckDB ist der Default - kein `USE_DUCKDB=true` mehr nötig!
- **KEIN `--workers`** - DuckDB unterstützt keinen Multi-Prozess-Zugriff
- **KEIN `--reload`** - verursacht Datei-Konflikte beim Editieren

```bash
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend

# Windows CMD/PowerShell (Standard - verwendet DuckDB):
"C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/python.exe" -m uvicorn app.main:app --port 8000

# Nur falls SQLite benötigt wird (Legacy):
set USE_DUCKDB=false && "C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/python.exe" -m uvicorn app.main:app --port 8000
```

**Warum kein `--reload` und kein `--workers`?**
- `--reload` überwacht Dateien → Konflikte beim Editieren mit Claude
- `--workers N` startet N Prozesse → DuckDB-Datei kann nur von einem Prozess geöffnet werden
- Bei Code-Änderungen: Backend stoppen + neu starten

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

---

## Stop-Befehle (Windows)

**Stand 28.01.2026 00:50**

**ACHTUNG für Claude:** NIEMALS `taskkill /F /IM node.exe` oder `taskkill /F /IM python.exe` verwenden!
Das würde auch den Claude Code Prozess selbst beenden.

### Backend sauber stoppen (Optimierte Prozedur)

**Problem:** Git Bash konvertiert `/PID` zu Pfaden → `cmd //c "..."` verwenden!

```bash
# SCHRITT 1: Alle uvicorn-Prozesse auflisten
wmic process where "name='python.exe'" get ProcessId,CommandLine 2>nul

# Beispiel-Ausgabe (Dev ohne workers = 1 Prozess):
# CommandLine                                                                    ProcessId
# ...venv\Scripts\python.exe -m uvicorn app.main:app --port 8000                13712

# SCHRITT 2: PID beenden (Git Bash kompatibel!)
cmd //c "taskkill /PID 13712 /F"

# SCHRITT 3: Prüfen ob Port frei ist
netstat -ano | findstr :8000 || echo "Port 8000 ist frei"
```

**Hinweis:** Im Dev-Modus (ohne `--workers`) läuft nur **ein** Python-Prozess.

**Falls taskkill fehlschlägt:**
```bash
# Fallback 1: PowerShell (im separaten Terminal)
powershell -Command "Get-Process python | Stop-Process -Force"

# Fallback 2: Windows Task-Manager
# → Details-Tab → python.exe → Task beenden
```

### Frontend stoppen (Port 3001)

```bash
# 1. Prozess auf Port 3001 finden
netstat -ano | findstr :3001
# Ausgabe z.B.: TCP 127.0.0.1:3001 ... ABHÖREN 5678

# 2. Prozess beenden (Git Bash kompatibel!)
cmd //c "taskkill /PID 5678 /F"
```

### Manuelles Stoppen (NUR für User im Terminal!)

```bash
# Alle Node-Prozesse (NICHT für Claude!)
taskkill /F /IM node.exe

# Alle Python-Prozesse (NICHT für Claude!)
taskkill /F /IM python.exe
```

---

## RESET - Cache löschen

**Stand 28.01.2026 00:50**

**WICHTIG:** Backend MUSS gestoppt sein bevor Caches gelöscht werden!
Sonst: Singleton-Problem → Services denken sie sind initialisiert → Fehler!

### Welche Caches gibt es?

| Datei/Ordner | Beschreibung | Löschen bei |
|--------------|--------------|-------------|
| `building_3d.duckdb` | Gebäude-Grunddaten (DuckDB) | Höhen-/Polygon-Problemen |
| `building_3d.db` | Gebäude-Grunddaten (SQLite Legacy) | Nur wenn SQLite verwendet |
| `tiles.db` | Tile-Metadaten | Tile-Download-Problemen |
| `tiles/` | GDB-Rohdateien | Tile-Download-Problemen |
| `building_contexts.db` | Zonen, Terrain-Cache | Zonen-/Terrain-Problemen |
| `cache.db` | API-Response Cache | API-Problemen |
| **geruestbau.db** | **PROJEKTE - NICHT LÖSCHEN!** | NIE (Benutzerdaten!) |

### Vollständiger Reset (alle Caches)

```bash
# 1. Backend stoppen (siehe oben)
wmic process where "name='python.exe'" get ProcessId,CommandLine 2>nul
cmd //c "taskkill /PID <PIDs> /F"

# 2. Alle Caches löschen (NICHT geruestbau.db!)
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend/app/data
del /F /Q building_3d.duckdb building_3d.db tiles.db building_contexts.db cache.db 2>nul
rmdir /S /Q tiles 2>nul
echo "Alle Caches gelöscht"

# 3. Backend neu starten
cd C:/Users/vonro/projects/lawil/geodaten-ch/backend
"C:/Users/vonro/projects/lawil/geodaten-ch/backend/venv/Scripts/python.exe" -m uvicorn app.main:app --port 8000
```

### Partieller Reset (nur bestimmte Caches)

```bash
# Nur Gebäude-Daten (bei Höhen-/Polygon-Problemen)
del /F /Q building_3d.duckdb building_3d.db 2>nul

# Nur Tiles (bei Download-Problemen)
del /F /Q tiles.db 2>nul && rmdir /S /Q tiles 2>nul

# Nur Zonen/Terrain (bei Claude-Analyse-Problemen)
del /F /Q building_contexts.db 2>nul
```

### Warum Singleton-Problem?

```
┌─────────────────────────────────────────────────────────────┐
│  PROBLEM: Backend läuft, Cache wird gelöscht                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Service startet → _initialized = True                   │
│  2. DB wird gelöscht (extern)                               │
│  3. Nächster Request → Service denkt "schon initialisiert"  │
│  4. → Tabellen existieren nicht → FEHLER!                   │
│                                                             │
│  LÖSUNG: IMMER Backend stoppen vor Cache-Löschung!          │
└─────────────────────────────────────────────────────────────┘
```

---

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
cmd //c "taskkill /PID <PID> /F"
```
