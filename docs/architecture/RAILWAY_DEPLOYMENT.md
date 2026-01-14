# Railway Deployment Guide

> **Stand:** 14.01.2026 14:45
> **Status:** Production ✅
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

### Worker-Konfiguration

`uvicorn` läuft mit `--workers 4` für parallele Request-Verarbeitung.

Bei Memory-Problemen reduzieren:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

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
