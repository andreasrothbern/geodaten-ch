# Setup-Anleitung: Claude.ai Integration

> **Version:** 1.0
> **Datum:** 24.12.2025

## Voraussetzungen

1. **Anthropic API Key** - Von https://console.anthropic.com/
2. **Python 3.11+** mit installierten Dependencies
3. **Backend Server** läuft (lokal oder Railway)

---

## 1. API Key einrichten

### Lokal (Entwicklung)

```bash
# .env Datei im backend/ Ordner erstellen
cd backend
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
```

Oder als Umgebungsvariable:

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."

# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-api03-...

# Linux/Mac
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Railway (Production)

1. Railway Dashboard öffnen
2. Backend Service auswählen
3. Variables → Add Variable
4. Name: `ANTHROPIC_API_KEY`
5. Value: `sk-ant-api03-...`
6. Deploy

---

## 2. Abhängigkeiten installieren

```bash
cd backend
pip install anthropic
# oder
pip install -r requirements.txt
```

Die `anthropic` Bibliothek ist bereits in `requirements.txt` enthalten.

---

## 3. Building Context System testen

### API Test (curl)

```bash
# 1. Einfaches Gebäude (Auto-Context)
curl "http://localhost:8000/api/v1/building/context/1234567?create_if_missing=true"

# 2. Komplexes Gebäude analysieren (Bundeshaus)
curl -X POST "http://localhost:8000/api/v1/building/context/1230564/analyze" \
  -H "Content-Type: application/json" \
  -d '{"include_orthofoto": false, "force_reanalyze": false}'

# 3. Gespeicherten Kontext abrufen
curl "http://localhost:8000/api/v1/building/context/1230564"
```

### Python Test

```python
import asyncio
from app.services.building_context import BuildingContextService

async def test():
    service = BuildingContextService()

    # Bundeshaus EGID
    egid = "1230564"

    # Test-Polygon (vereinfacht)
    polygon = [
        (2600420.0, 1199480.0),
        (2600480.0, 1199480.0),
        (2600480.0, 1199580.0),
        (2600420.0, 1199580.0),
    ]

    # GWR-Daten
    gwr_data = {
        "gkat": 1060,  # Öffentliches Gebäude
        "gastw": 5,
        "gbauj": 1902,
        "garea": 5000
    }

    # Komplexität prüfen
    complexity = service.detect_complexity(polygon, gwr_data, 5000)
    print(f"Komplexität: {complexity}")  # -> "complex"

    # Claude-Analyse
    context = await service.analyze_with_claude(
        egid=egid,
        adresse="Bundesplatz 3, 3011 Bern",
        polygon=polygon,
        gwr_data=gwr_data,
        traufhoehe_m=14.5,
        firsthoehe_m=25.0,
        gebaeudehoehe_m=25.0
    )

    print(f"Zonen: {len(context.zones)}")
    for zone in context.zones:
        print(f"  - {zone.name}: {zone.gebaeudehoehe_m}m ({zone.type})")

asyncio.run(test())
```

---

## 4. Kosten überwachen

### Claude API Kosten (Claude Sonnet 4)

| Operation | Input Tokens | Output Tokens | Kosten |
|-----------|--------------|---------------|--------|
| Einfache Analyse | ~2000 | ~500 | ~$0.01 |
| Mit Orthofoto | ~10000 | ~800 | ~$0.05 |
| Komplexes Gebäude | ~3000 | ~1000 | ~$0.02 |

### Kosten minimieren

1. **Caching**: Einmal analysierte Gebäude werden in SQLite gespeichert
2. **Auto-Context**: Einfache Gebäude brauchen keine Claude-Analyse
3. **Batch-Analyse**: Mehrere Gebäude in einer Session analysieren

---

## 5. Fehlerbehandlung

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| `ANTHROPIC_API_KEY not set` | Umgebungsvariable fehlt | API Key setzen (siehe oben) |
| `Invalid API key` | Falscher Key | Key in Anthropic Console prüfen |
| `Rate limit exceeded` | Zu viele Anfragen | Warten oder Tier upgraden |
| `Model not found` | Falsches Modell | `claude-sonnet-4-20250514` verwenden |

### Logs prüfen

```bash
# Backend Logs (lokal)
uvicorn app.main:app --reload --log-level debug

# Railway Logs
railway logs
```

---

## 6. Claude.ai Chat-Kontext einrichten

Für manuelle Analysen in Claude.ai (chat.anthropic.com):

### Projekt-Kontext kopieren

1. Diese Dateien in Claude.ai hochladen oder einfügen:
   - `docs/poc_bundeshaus_mvp/CLAUDE.md` - Projekt-Kontext
   - `docs/poc_bundeshaus_mvp/BUILDING_CONTEXT.md` - System-Doku
   - `docs/poc_bundeshaus_mvp/SVG_SPEC.md` - SVG-Spezifikation

2. System-Prompt setzen:

```
Du bist ein Experte für Schweizer Geodaten und Gerüstplanung.
Du analysierst Gebäudepolygone und identifizierst Höhenzonen.

Verwende die Dokumentation in BUILDING_CONTEXT.md für das Datenmodell.
Antworte immer mit validem JSON im BuildingContext-Format.
```

### Beispiel-Anfrage

```
Analysiere dieses Gebäudepolygon:

Koordinaten (LV95): [(2600420, 1199480), (2600480, 1199480), ...]
Grundfläche: 5000 m²
Globale Höhe: 14.5m Traufe, 25m First
Kategorie: 1060 (Öffentliches Gebäude)
Adresse: Bundesplatz 3, 3011 Bern

Identifiziere die Höhenzonen und gib das Ergebnis als BuildingContext JSON zurück.
```

---

## 7. Architektur-Dateien

### Backend

```
backend/
├── app/
│   ├── models/
│   │   └── building_context.py    # Pydantic Models
│   ├── services/
│   │   └── building_context.py    # Service mit Claude API
│   └── main.py                    # API Endpoints
└── data/
    └── building_contexts.db       # SQLite Cache
```

### Frontend

```
frontend/
└── src/
    └── types.ts                   # TypeScript Types
```

---

## 8. Nächste Schritte

1. **Frontend Zonen-Editor** - Zonen im UI bearbeiten
2. **SVG-Generator erweitern** - Zonen farbcodiert darstellen
3. **Orthofoto-Integration** - Bessere Analyse mit Luftbild
4. **Validierungs-Workflow** - User bestätigt Claude-Analyse

---

## Kontakt

Bei Fragen oder Problemen:
- Repository: https://github.com/andreasrothbern/geodaten-ch/
- Branch: `poc_bundeshaus_mvp`
