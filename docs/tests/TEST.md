# SVG-Analyse Testszenario

## Schnellstart

```bash
# Im Backend-Verzeichnis
cd backend

# Test mit Standard-Adresse (St. Peter & Paul)
python scripts/generate_svg_analysis.py "Rathausgasse 2, 3011 Bern"

# Test mit beliebiger Adresse
python scripts/generate_svg_analysis.py "Bundesplatz 3, 3011 Bern"

# Test ohne SVG-Generierung (nur Prompt)
python scripts/generate_svg_analysis.py "Kramgasse 49, 3011 Bern" --no-svg
```

---

## Was das Skript macht

1. **Gebäudedaten abrufen** - SmartBuildingService API (Railway)
2. **Prompt generieren** - Einheitlicher SVG-Prompt mit Quick Wins
3. **SVGs generieren** - 3 SVGs (Grundriss, Ansicht, Schnitt) via Claude API
4. **Analyse-Paket erstellen** - Alle Dateien in `docs/tests/svg_analysis/`

---

## Ausgabe-Ordner

Nach dem Test findest du unter `docs/tests/svg_analysis/<adresse>_<timestamp>/`:

| Datei | Beschreibung |
|-------|--------------|
| `prompt.md` | Der generierte SVG-Prompt |
| `building_data.json` | Rohdaten vom SmartBuildingService |
| `ANLEITUNG_CLAUDE_AI.md` | Anleitung für Claude.ai |
| `grundriss_api.svg` | API-generierter Grundriss |
| `ansicht_api.svg` | API-generierte Ansicht |
| `schnitt_api.svg` | API-generierter Schnitt |
| `README.md` | Übersicht des Ordners |

---

## Workflow mit Claude.ai

### Schritt 1: Test ausführen

```bash
python scripts/generate_svg_analysis.py "Rathausgasse 2, 3011 Bern"
```

### Schritt 2: Claude.ai öffnen

1. Gehe zu https://claude.ai
2. Starte einen neuen Chat

### Schritt 3: Dateien hochladen/kopieren

1. **ANLEITUNG_CLAUDE_AI.md** - Als ersten Text kopieren
2. **prompt.md** - Als zweiten Text kopieren
3. **SVG-Dateien** - Hochladen oder Code kopieren:
   - grundriss_api.svg
   - ansicht_api.svg
   - schnitt_api.svg

### Schritt 4: Claude.ai arbeiten lassen

Claude.ai wird:
1. Eigene SVGs generieren (grundriss_claude.svg, ansicht_claude.svg, schnitt_claude.svg)
2. Die API-SVGs mit den eigenen vergleichen
3. Unterschiede dokumentieren
4. Prompt-Verbesserungen vorschlagen
5. Alles als Download-Paket bereitstellen

---

## Beispiel-Adressen

| Adresse | Gebäude | Komplexität |
|---------|---------|-------------|
| Rathausgasse 2, 3011 Bern | Kirche St. Peter und Paul | complex |
| Bundesplatz 3, 3011 Bern | Bundeshaus | complex |
| Münsterplatz 1, 3011 Bern | Berner Münster | complex |
| Kramgasse 49, 3011 Bern | Einsteinhaus | simple |
| Hodlerstrasse 8, 3011 Bern | Kunstmuseum Bern | complex |

---

## Optionen

```
usage: generate_svg_analysis.py [-h] [--output OUTPUT] [--local]
                                 [--svg-type {all,grundriss,ansicht,schnitt}]
                                 [--no-svg]
                                 address

positional arguments:
  address               Adresse des Gebäudes

optional arguments:
  -h, --help            Hilfe anzeigen
  --output, -o          Ausgabe-Ordner (optional)
  --local               Lokale API statt Railway
  --svg-type            SVG-Typ (default: all)
  --no-svg              SVGs nicht generieren
```

---

## Erwartete Ergebnisse

### Gute SVGs

- Proportionen stimmen mit Prompt überein
- Alle Zonen sind korrekt dargestellt
- Gerüst ist blau (#0066CC)
- Schraffur-Pattern vorhanden
- Höhenskala korrekt

### Bekannte Probleme

- Komplexe Polygone werden vereinfacht
- Innenhöfe werden nicht immer erkannt
- Turm-Proportionen können abweichen

---

## Troubleshooting

### API-Timeout

```
FEHLER: Connection timeout
```
→ Railway-API überlastet. Warte 1-2 Minuten und versuche erneut.

### SVG-Fehler

```
FEHLER - JSON Response
```
→ API hat Fehler statt SVG zurückgegeben. Prüfe die Adresse.

### Lokaler Test

```bash
# Backend lokal starten
cd backend
uvicorn app.main:app --reload --port 8000

# Mit --local Flag testen
python scripts/generate_svg_analysis.py "Rathausgasse 2, Bern" --local
```

---

*Stand: 2025-12-30*
*Tool: generate_svg_analysis.py*
