# API-generierte Prompts

Diese Dateien enthalten die **echten Prompts**, die von der Claude API verwendet werden.
Sie wurden direkt vom `/api/v1/smart-building/prompt` Endpunkt exportiert.

## Dateien

| Datei | Gebaeude | SVG-Typ | Beschreibung |
|-------|----------|---------|--------------|
| `bundeshaus_schnitt.md` | Bundeshaus | schnitt | Gebaeudeschnitt |
| `bundeshaus_ansicht.md` | Bundeshaus | ansicht | Fassadenansicht |
| `bundeshaus_grundriss.md` | Bundeshaus | grundriss | Grundriss |
| `bundeshaus_all.md` | Bundeshaus | all | Alle 3 SVGs |
| `st_peter_paul_all.md` | Kirche St. Peter und Paul | all | Alle 3 SVGs |

## Verwendung

Diese Prompts koennen in Claude.ai eingefuegt werden um:
1. Die Prompt-Qualitaet zu analysieren
2. Verbesserungen zu identifizieren
3. Manuell hochwertige SVGs zu generieren

**Empfohlen:** Immer `svg_type=all` verwenden fuer alle 3 SVGs gleichzeitig.

## Regenerieren

```bash
# Alle SVGs fuer ein Gebaeude (EMPFOHLEN)
curl -s "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/prompt?address=Bundesplatz%203%2C%203011%20Bern&svg_type=all"

# Kirche St. Peter und Paul
curl -s "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/prompt?address=Rathausgasse%202%2C%20Bern&svg_type=all"

# Berner Muenster
curl -s "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/prompt?address=Muensterplatz%201%2C%20Bern&svg_type=all"

# Einzelne SVG-Typen (optional)
curl -s "...&svg_type=schnitt"
curl -s "...&svg_type=ansicht"
curl -s "...&svg_type=grundriss"
```

## Bekannte Gebaeude

Diese Gebaeude haben vordefinierte Hoehenzonen in `known_buildings.py`:

| Adresse | Gebaeude | Zonen |
|---------|----------|-------|
| Bundesplatz 3, 3011 Bern | Bundeshaus | Arkaden, Hauptgebaeude, Kuppel |
| Rathausgasse 2, 3011 Bern | Kirche St. Peter und Paul | Kirchenschiff, Seitenschiffe, Turm |
| Muensterplatz 1, 3011 Bern | Berner Muenster | Kirchenschiff, Seitenkapellen, Turm |
| Kramgasse 49, 3011 Bern | Zytglogge | Torhaus, Turm |

## Stand

Exportiert am: 30.12.2025
