# Railway Deployment Guide

> **Stand:** 07.02.2026 14:00
> **Status:** Production ✅ (Railway Pro Plan)
> **URLs:**
> - Frontend: https://cooperative-commitment-production.up.railway.app/
> - Backend: https://acceptable-trust-production.up.railway.app/

---

## Übersicht

Das Projekt ist auf Railway.app deployed mit:
- **Backend:** FastAPI Container (Python 3.11)
- **Frontend:** Vite/React Build mit Nginx
- **Volume:** Persistenter Speicher für SQLite/DuckDB Datenbanken

---

## Railway CLI Installation

```bash
# NPM (empfohlen)
npm install -g @railway/cli

# Oder via npx (ohne Installation)
npx @railway/cli <command>
```

### Authentifizierung

```bash
# Login (öffnet Browser)
railway login

# Status prüfen
railway whoami
```

---

## Wichtige CLI Befehle

### Projekt-Verwaltung

```bash
# Projekt verlinken (im Projektordner ausführen)
cd geodaten-ch/backend
railway link

# Projekte auflisten
railway list

# Environment Variables anzeigen
railway variables

# Environment Variable setzen
railway variables set KEY=value

# Logs anzeigen (live)
railway logs

# Logs der letzten N Zeilen
railway logs --tail 100
```

### Deployment

```bash
# Manuelles Deployment triggern
railway up

# Mit Build-Logs
railway up --verbose

# Status prüfen
railway status
```

### Volume-Verwaltung

```bash
# Volume erstellen und mounten
railway volume add --mount-path /app/data

# Volume-Info anzeigen
railway volume list

# Volume-Nutzung prüfen (via API Endpoint)
curl https://acceptable-trust-production.up.railway.app/debug/paths
```

---

## Volume-Konfiguration

### Warum ein Volume?

Ohne persistentes Volume gehen alle Datenbanken bei jedem Deployment verloren:
- `building_3d.duckdb` - Gebäude-Grunddaten (Polygon, Höhen)
- `tiles.db` - Tile-Metadaten
- `building_contexts.db` - Zonen, Terrain-Cache
- `geruestbau.db` - Projekte (Benutzerdaten!)

### Volume Setup

```bash
# 1. In Backend-Ordner wechseln
cd geodaten-ch/backend

# 2. Projekt verlinken (falls noch nicht)
railway link

# 3. Volume hinzufügen (500 MB Standard)
railway volume add --mount-path /app/data

# 4. Deployment triggern
railway up
```

### Environment Variable

Railway setzt automatisch:
```
RAILWAY_VOLUME_MOUNT_PATH=/app/data
```

Diese Variable wird von `config.py` erkannt:

```python
# backend/app/config.py
DATA_DIR = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", str(Path(__file__).parent / "data")))
```

---

## Pfad-Konfiguration (config.py)

Alle Services MÜSSEN das zentrale `DATA_DIR` aus `config.py` verwenden:

```python
from app.config import DATA_DIR, BUILDING_3D_DB_PATH, TILES_DB_PATH

# Korrekte Pfade (Railway-kompatibel)
TILES_DIR = DATA_DIR / "tiles"
TILE_CACHE_DB = TILES_DB_PATH
```

### Betroffene Services

| Datei | Import |
|-------|--------|
| `tile_cache.py` | `from app.config import DATA_DIR, TILES_DB_PATH` |
| `layer_fetcher.py` | `from app.config import DATA_DIR` |
| `roof_3d_service.py` | `from app.config import DATA_DIR` |
| `neighbors_service.py` | `self.data_path = DATA_DIR` |
| `blocked_facades_service.py` | `self.data_path = DATA_DIR` |

### Falsch (hardcodiert):

```python
# ❌ FALSCH - funktioniert nicht auf Railway!
self.data_path = Path(__file__).parent.parent / "data"
```

### Richtig (zentralisiert):

```python
# ✅ RICHTIG - funktioniert lokal UND auf Railway
from app.config import DATA_DIR
self.data_path = DATA_DIR
```

---

## Debug-Endpoints

### /debug/paths

Zeigt aktuelle Pfad-Konfiguration:

```bash
curl https://acceptable-trust-production.up.railway.app/debug/paths
```

Response:
```json
{
  "data_dir": "/app/data",
  "building_3d_db": "/app/data/building_3d.duckdb",
  "tiles_db": "/app/data/tiles.db",
  "building_3d_exists": true,
  "tiles_db_exists": true,
  "volume_mounted": true,
  "volume_usage_mb": 26.5,
  "volume_limit_mb": 500
}
```

### /health

Health-Check Endpoint:

```bash
curl https://acceptable-trust-production.up.railway.app/health
```

---

## Bekannte Probleme & Lösungen

### Problem: Daten verschwinden nach Deployment

**Symptom:** Nach Deployment sind alle Gebäudedaten weg.

**Ursache:** Volume nicht korrekt gemountet.

**Lösung:**
```bash
# Volume-Status prüfen
railway volume list

# Falls leer: Volume neu erstellen
railway volume add --mount-path /app/data

# Deployment triggern
railway up
```

### Problem: Langsame Performance

**Symptom:** API-Requests dauern >5 Sekunden.

**Mögliche Ursachen:**
1. **Erster Request nach Cold Start:** Worker muss initialisieren
2. **Tile-Download:** Erste Abfrage für neue Region lädt Tile (~5-10s)
3. **DuckDB nicht verwendet:** Prüfe ob `USE_DUCKDB` korrekt gesetzt

**Diagnose:**
```bash
# Logs prüfen
railway logs --tail 200

# Performance-Metriken
curl https://acceptable-trust-production.up.railway.app/api/v1/smart-building/data?address=Bundesplatz%203,%20Bern
```

### Problem: Hardcodierte Pfade in Service

**Symptom:** `FileNotFoundError` oder leere Datenbank-Abfragen.

**Lösung:** Import aus `config.py` verwenden:
```python
# Ändern von:
self.data_path = Path(__file__).parent.parent / "data"

# Zu:
from app.config import DATA_DIR
self.data_path = DATA_DIR
```

---

## Environment Variables

### Backend (Required)

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `RAILWAY_VOLUME_MOUNT_PATH` | Volume-Pfad (automatisch) | `/app/data` |
| `PORT` | Server-Port (automatisch) | `8000` |

### Backend (Optional)

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| `USE_DUCKDB` | DuckDB verwenden | `true` (seit 13.01.2026) |
| `ANTHROPIC_API_KEY` | Claude API Key | - |

### Frontend

| Variable | Beschreibung | Wert |
|----------|--------------|------|
| `VITE_API_BASE_URL` | Backend-URL | `https://acceptable-trust-production.up.railway.app` |

---

## Deployment-Workflow

### Automatisches Deployment (GitHub Integration)

Railway deployed automatisch bei Push auf `main`:

```bash
git add .
git commit -m "fix(backend): update service"
git push origin main
# → Railway startet automatisch Build + Deploy
```

### Manuelles Deployment

```bash
# Im Projektordner
cd geodaten-ch/backend

# Projekt verlinken (einmalig)
railway link

# Deployment starten
railway up
```

### Rollback

```bash
# Letzte Deployments anzeigen
railway deployments

# Zu bestimmtem Deployment zurück
railway rollback <deployment-id>
```

---

## Monitoring

### Logs anzeigen

```bash
# Live-Logs
railway logs

# Letzte 500 Zeilen
railway logs --tail 500

# Nach Fehler filtern
railway logs | grep -i error
```

### Metriken

Railway Dashboard zeigt:
- CPU-Nutzung
- Memory-Nutzung
- Network I/O
- Volume-Nutzung

---

## Kosten-Optimierung

### Volume-Grösse

Standard: 500 MB (kostenlos im Hobby-Plan)

Aktuelle Nutzung prüfen:
```bash
curl https://acceptable-trust-production.up.railway.app/debug/paths | jq '.volume_usage_mb'
```

### Worker-Konfiguration (Stand 07.02.2026)

> **WICHTIG:** `uvicorn` läuft mit `--workers 1` wegen DuckDB Single-Writer Lock!

**Warum `--workers 1`?**
DuckDB erlaubt nur EINEN Schreibzugriff (Single-Writer). Mit `--workers N` startet uvicorn
N separate Prozesse, die alle versuchen eine DB-Connection zu öffnen → Lock-Konflikte!

```
--workers=4 (uvicorn) startet 4 separate PROZESSE:
     │
     ├─ Prozess 1: duckdb.connect("building_3d.duckdb") → Bekommt WRITE-Lock ✅
     ├─ Prozess 2: duckdb.connect("building_3d.duckdb") → ❌ "database is locked"
     ├─ Prozess 3: duckdb.connect("building_3d.duckdb") → ❌ "database is locked"
     └─ Prozess 4: duckdb.connect("building_3d.duckdb") → ❌ "database is locked"
```

**Lösung:** `--workers 1` + `DUCKDB_THREADS=16` = Parallele Queries OHNE Lock-Konflikte

| Parameter | Was es macht | Lock-Konflikt? |
|-----------|--------------|----------------|
| `--workers 4` | 4 separate PROZESSE | **JA!** Jeder Prozess = separater DB-Lock |
| `DUCKDB_THREADS=16` | 16 Threads IN EINEM Prozess | **NEIN** - DuckDB-interne Parallelisierung |

```dockerfile
# Aktueller Dockerfile CMD (KORREKT):
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

---

### DuckDB Concurrency (Stand 07.02.2026)

**DuckDB Konfiguration** (`config.py`):
```python
DUCKDB_CONFIG = {
    "threads": int(os.getenv("DUCKDB_THREADS", "16")),      # Parallele Queries
    "memory_limit": os.getenv("DUCKDB_MEMORY_LIMIT", "4GB"), # RAM-Limit
    "temp_directory": str(DUCKDB_TEMP_DIR),                  # Ephemeral Storage
}
```

**Read vs. Write:**
- **Write:** NUR EINE Connection kann gleichzeitig schreiben
- **Read:** UNBEGRENZT viele read_only Connections parallel möglich

---

### SSE-Pipeline Concurrency (Stand 07.02.2026)

Die SSE-Pipeline für Gebäudedaten (`/building/data/stream`) nutzt ein **3-Stufen-System**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                  3-STUFEN IMPORT                                       │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  STUFE 1: Angefragtes Gebäude SOFORT speichern (~50ms)                │
│  ═══════════════════════════════════════════════════                   │
│  → import_single_building() für das Bundle                            │
│  → has_3d_layers=1 wird gesetzt                                       │
│  → SSE "polygon" Event wird SOFORT gesendet                           │
│                                                                        │
│  STUFE 2+3: Background prefetch (fire-and-forget)                     │
│  ═════════════════════════════════════════════════                     │
│  → asyncio.create_task(prefetch_and_cleanup(...))                     │
│  → SSE wartet NICHT auf diesen Task                                   │
│  → Heights, Terrain, Zones Events werden sofort gesendet              │
│                                                                        │
│  RESULTAT: User bekommt Daten in ~50ms + SSE Events                   │
│            Tile-Prefetch läuft im Background                          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Bei 2 gleichzeitigen Imports:**

| Phase | Parallelität | Wie? |
|-------|--------------|------|
| **Download** | ✅ Parallel | Separate HTTP-Streams |
| **GDB → Parquet** | ✅ Parallel | Separate Dateien pro Tile |
| **Parquet → DuckDB** | ⚠️ Serialisiert | DuckDB Single-Writer queued |

**Wichtig:** Die SSE-Pipeline bricht NICHT ab. DuckDB serialisiert die Writes intern.

**Code-Referenzen:**
- `building_data_stream.py:696-756` - 3-Stufen Import
- `tile_prefetch.py:264-269` - Tile-Deduplication
- `parquet_writer.py:561-652` - DuckDB Bulk-Load

---

### Railway Pro Konfiguration (Stand 07.02.2026)

> **Upgrade 07.02.2026:** Railway Pro Plan ($20/Monat)
> - bis 1,000 vCPU / 1 TB RAM pro Service
> - bis 50 Replicas × 32 vCPU / 32 GB RAM
> - bis 1 TB Storage (Volume)

**Optimierte Settings** (`railway.toml`):
```toml
[variables]
DUCKDB_THREADS = "16"           # Nutze Multi-Core!
DUCKDB_MEMORY_LIMIT = "4GB"     # Für grössere Batch-Imports
CLEANUP_TILES_AFTER_IMPORT = "true"
NEIGHBOR_SEARCH_RADIUS_M = "100"
```

**Lokal (Entwicklung)** (`.env`):
```env
DUCKDB_THREADS=4
DUCKDB_MEMORY_LIMIT=512MB
```

---

### Read-Replica Architektur (GEPLANT)

> **Status:** Geplant für horizontale Skalierung
> **Aufwand:** 5-8 Stunden

**Ziel:** 1 Writer + 3 Reader + Load Balancer

```
┌─────────────────────────────────────────────────────────────┐
│                    LOAD BALANCER (Nginx)                    │
│                    Port 8080 (PUBLIC)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │  READER 1   │   │  READER 2   │   │  READER 3   │
   │  read_only  │   │  read_only  │   │  read_only  │
   │  workers=4  │   │  workers=4  │   │  workers=4  │
   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │ READ
                            ▼
   ┌───────────────────────────────────────────────────────┐
   │                    SHARED VOLUME                      │
   │                    /app/data                          │
   └───────────────────────────────────────────────────────┘
                            ▲
                            │ WRITE
                            │
   ┌───────────────────────────────────────────────────────┐
   │                    WRITER SERVICE                     │
   │                    Port 8000 (INTERNAL)               │
   │                    workers=1 (DuckDB Lock!)           │
   └───────────────────────────────────────────────────────┘
```

**Routing:**
- GET Requests → Reader (Round-Robin)
- POST/PUT/DELETE → Writer

**Kapazität:**
- 12 parallele Lese-Requests (3 Reader × 4 Workers)
- 112 DuckDB Query-Threads (Writer 16 + Reader 3×4×8)

Siehe Plan-Datei für vollständige Details.

---

## Checkliste: Neues Deployment

1. [ ] Volume existiert (`railway volume list`)
2. [ ] Environment Variables gesetzt (`railway variables`)
3. [ ] Keine hardcodierten Pfade (alle Services nutzen `DATA_DIR`)
4. [ ] DuckDB als Default (`USE_DUCKDB` nicht auf `false`)
5. [ ] Frontend `VITE_API_BASE_URL` korrekt
6. [ ] Health-Check erfolgreich (`/health`)
7. [ ] Debug-Pfade korrekt (`/debug/paths`)

---

## Referenzen

- [Railway CLI Dokumentation](https://docs.railway.app/develop/cli)
- [Railway Volumes](https://docs.railway.app/reference/volumes)
- [`config.py`](../../backend/app/config.py) - Zentrale Pfad-Konfiguration
- [`CLAUDE.md`](../../CLAUDE.md) - Projekt-Übersicht
