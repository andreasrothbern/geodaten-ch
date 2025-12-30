# Claude.ai Prompts für SVG-Generierung

Diese Prompts können direkt in [Claude.ai](https://claude.ai) kopiert werden, um hochwertige SVG-Grafiken zu generieren.

## Verfügbare Prompts

### Bundeshaus Bern
- [bundeshaus_schnitt.md](bundeshaus_schnitt.md) - Gebäudeschnitt
- [bundeshaus_ansicht.md](bundeshaus_ansicht.md) - Fassadenansicht
- [bundeshaus_grundriss.md](bundeshaus_grundriss.md) - Grundriss mit Gerüstplanung

### Berner Münster
- [muenster_schnitt.md](muenster_schnitt.md) - Gebäudeschnitt

### Kirche St. Peter und Paul
- [st_peter_paul_schnitt.md](st_peter_paul_schnitt.md) - Gebäudeschnitt

## Verwendung

1. Öffne [claude.ai](https://claude.ai)
2. Kopiere den gesamten Prompt-Text (ab "Erstelle...")
3. Füge ihn in Claude.ai ein
4. Claude generiert das SVG
5. Kopiere das SVG und speichere es als `.svg` Datei

## Datenquellen

Die Prompts enthalten echte Daten aus:
- **swisstopo API** - Koordinaten, GWR-Daten
- **swissBUILDINGS3D** - Trauf-/Firsthöhen
- **known_buildings.py** - Verifizierte Höhenzonen

## Eigene Prompts erstellen

Nutze die API um Daten für andere Gebäude zu sammeln:

```bash
# Gebäudedaten abrufen
curl "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/data?address=Kramgasse%2049%2C%203011%20Bern&include_research=true&include_zones=true"

# Prompt generieren
curl "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/prompt?address=Kramgasse%2049%2C%203011%20Bern&svg_type=all"
```

## Qualitätsunterschiede

| Methode | Qualität | Kosten |
|---------|----------|--------|
| Claude.ai (manuell) | Sehr hoch | Subscription |
| Claude API (automatisch) | Gut | ~$0.05-0.15/SVG |

Die manuellen Claude.ai Prompts ermöglichen Iteration und Verfeinerung für optimale Ergebnisse.
