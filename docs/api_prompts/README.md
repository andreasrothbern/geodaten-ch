# API-generierte Prompts

Diese Dateien enthalten die **echten Prompts**, die von der Claude API verwendet werden.
Sie wurden direkt vom `/api/v1/smart-building/prompt` Endpunkt exportiert.

## Dateien

| Datei | SVG-Typ | Beschreibung |
|-------|---------|--------------|
| `bundeshaus_schnitt.md` | schnitt | Gebäudeschnitt (Querschnitt) |
| `bundeshaus_ansicht.md` | ansicht | Fassadenansicht |
| `bundeshaus_grundriss.md` | grundriss | Grundriss mit Gerüstplanung |
| `bundeshaus_all.md` | all | Alle 3 SVGs in einem Prompt |

## Verwendung

Diese Prompts können in Claude.ai eingefügt werden um:
1. Die Prompt-Qualität zu analysieren
2. Verbesserungen zu identifizieren
3. Manuell hochwertige SVGs zu generieren

## Regenerieren

```bash
# Schnitt-Prompt neu generieren
curl -s "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/prompt?address=Bundesplatz%203%2C%203011%20Bern&svg_type=schnitt"

# Alle Typen
curl -s "...&svg_type=all"
curl -s "...&svg_type=ansicht"
curl -s "...&svg_type=grundriss"
```

## Stand

Exportiert am: 30.12.2025
Adresse: Bundesplatz 3, 3011 Bern (Bundeshaus)
