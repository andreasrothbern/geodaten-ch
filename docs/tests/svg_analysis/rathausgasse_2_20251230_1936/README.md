# SVG-Analyse: Kirche St. Peter und Paul

## Inhalt

| Datei | Beschreibung |
|-------|--------------|
| `prompt.md` | Generierter SVG-Prompt |
| `building_data.json` | Rohdaten vom SmartBuildingService |
| `ANLEITUNG_CLAUDE_AI.md` | Anleitung für Claude.ai Analyse |
| `grundriss_api.svg` | Von Claude API generiertes SVG (grundriss) |
| `ansicht_api.svg` | Von Claude API generiertes SVG (ansicht) |
| `schnitt_api.svg` | Von Claude API generiertes SVG (schnitt) |

## Verwendung mit Claude.ai

1. Öffne Claude.ai (https://claude.ai)
2. Starte einen neuen Chat
3. Kopiere den Inhalt von `ANLEITUNG_CLAUDE_AI.md`
4. Kopiere den Inhalt von `prompt.md`
5. **Kopiere die SVG-Dateien** (grundriss_api.svg, ansicht_api.svg, schnitt_api.svg)
6. Lass Claude die SVGs analysieren und Verbesserungen vorschlagen

## Gebäude-Details

- **Adresse:** Rathausgasse 2, 3011 Bern
- **Name:** Kirche St. Peter und Paul
- **EGID:** 191821074
- **Komplexität:** complex
- **Zonen:** 4

## Generierte SVGs

3 SVGs wurden von der Claude API generiert:
- grundriss_api.svg - Draufsicht
- ansicht_api.svg - Fassadenansicht
- schnitt_api.svg - Gebäudeschnitt

Diese SVGs können an Claude.ai übergeben werden zur:
- Qualitätsanalyse
- Vergleich mit manuell erstellten SVGs
- Identifikation von Verbesserungspotential

## Generiert

- **Datum:** 2025-12-30 19:36
- **API:** https://acceptable-trust-production.up.railway.app
- **Tool:** generate_svg_analysis.py
