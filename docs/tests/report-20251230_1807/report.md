# Test-Report: 20251230_1807

## Uebersicht

| Metrik | Wert |
|--------|------|
| **Testzeit** | 20251230_1807 |
| **API** | https://acceptable-trust-production.up.railway.app |
| **Getestete Gebaeude** | 10 |
| **SVG-Typen** | grundriss, ansicht, schnitt |

### Cache-Status vor Test

```json
{
  "status": "ok",
  "buildings_cleared": 10,
  "total_deleted": 0,
  "details": [
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Bundesplatz 3, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Muensterplatz 1, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Rathausgasse 2, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Kramgasse 49, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Hodlerstrasse 8, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Kornhausplatz 18, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Bahnhofplatz 10, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Theaterplatz 7, 3011 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Helvetiaplatz 5, 3005 Bern",
      "cache_type": "all"
    },
    {
      "status": "ok",
      "deleted": {
        "bundle": 0,
        "research": 0,
        "svg": 0
      },
      "total": 0,
      "address_filter": "Bahnhofplatz 11, 3011 Bern",
      "cache_type": "all"
    }
  ]
}
```

---

## Ergebnisse pro Gebaeude

### Bundeshaus

**Adresse:** Bundesplatz 3, 3011 Bern
**EGID:** 2242547
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 29ms |
| ansicht | OK | 30ms |
| schnitt | OK | 27ms |

---

### Berner Muenster

**Adresse:** Muensterplatz 1, 3011 Bern
**EGID:** 1230337
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 26ms |
| ansicht | OK | 27ms |
| schnitt | OK | 34ms |

---

### St. Peter und Paul

**Adresse:** Rathausgasse 2, 3011 Bern
**EGID:** 191821074
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 28ms |
| ansicht | OK | 27ms |
| schnitt | OK | 29ms |

---

### Einsteinhaus

**Adresse:** Kramgasse 49, 3011 Bern
**EGID:** 1230393
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 26ms |
| ansicht | OK | 26ms |
| schnitt | OK | 38ms |

---

### Kunstmuseum

**Adresse:** Hodlerstrasse 8, 3011 Bern
**EGID:** 2247274
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 26ms |
| ansicht | OK | 50ms |
| schnitt | OK | 38ms |

---

### Kornhaus

**Adresse:** Kornhausplatz 18, 3011 Bern
**EGID:** 1230631
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 28985ms |
| ansicht | OK | 32224ms |
| schnitt | OK | 30156ms |

---

### Hauptbahnhof

**Adresse:** Bahnhofplatz 10, 3011 Bern
**EGID:** 2241912
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 30678ms |
| ansicht | OK | 27391ms |
| schnitt | OK | 27662ms |

---

### Stadttheater

**Adresse:** Theaterplatz 7, 3011 Bern
**EGID:** 1230414
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 32876ms |
| ansicht | OK | 31454ms |
| schnitt | OK | 35756ms |

---

### Historisches Museum

**Adresse:** Helvetiaplatz 5, 3005 Bern
**EGID:** 2243518
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 27642ms |
| ansicht | OK | 25547ms |
| schnitt | OK | 24914ms |

---

### Hotel Schweizerhof

**Adresse:** Bahnhofplatz 11, 3011 Bern
**EGID:** 1230691
**Status:** OK

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
| grundriss | OK | 29459ms |
| ansicht | OK | 29470ms |
| schnitt | OK | 29812ms |

---

## Zusammenfassung

| Metrik | Wert |
|--------|------|
| **SVGs generiert** | 30/30 |
| **Erfolgsrate** | 100.0% |
| **Durchschnittliche SVG-Zeit** | 14816ms |

---

## Dateien in diesem Report

### Recherche-Prompts
```
recherche_prompts/
  bundeshaus_recherche.md
  berner_muenster_recherche.md
  st_peter_und_paul_recherche.md
  einsteinhaus_recherche.md
  kunstmuseum_recherche.md
  kornhaus_recherche.md
  hauptbahnhof_recherche.md
  stadttheater_recherche.md
  historisches_museum_recherche.md
  hotel_schweizerhof_recherche.md
```

### SVG-Prompts
```
svg_prompts/
  bundeshaus_grundriss_prompt.md
  bundeshaus_ansicht_prompt.md
  bundeshaus_schnitt_prompt.md
  berner_muenster_grundriss_prompt.md
  berner_muenster_ansicht_prompt.md
  berner_muenster_schnitt_prompt.md
  st_peter_und_paul_grundriss_prompt.md
  st_peter_und_paul_ansicht_prompt.md
  st_peter_und_paul_schnitt_prompt.md
  einsteinhaus_grundriss_prompt.md
  einsteinhaus_ansicht_prompt.md
  einsteinhaus_schnitt_prompt.md
  kunstmuseum_grundriss_prompt.md
  kunstmuseum_ansicht_prompt.md
  kunstmuseum_schnitt_prompt.md
  kornhaus_grundriss_prompt.md
  kornhaus_ansicht_prompt.md
  kornhaus_schnitt_prompt.md
  hauptbahnhof_grundriss_prompt.md
  hauptbahnhof_ansicht_prompt.md
  hauptbahnhof_schnitt_prompt.md
  stadttheater_grundriss_prompt.md
  stadttheater_ansicht_prompt.md
  stadttheater_schnitt_prompt.md
  historisches_museum_grundriss_prompt.md
  historisches_museum_ansicht_prompt.md
  historisches_museum_schnitt_prompt.md
  hotel_schweizerhof_grundriss_prompt.md
  hotel_schweizerhof_ansicht_prompt.md
  hotel_schweizerhof_schnitt_prompt.md
```

### API-generierte SVGs
```
svg_api/
  bundeshaus_grundriss.svg
  bundeshaus_ansicht.svg
  bundeshaus_schnitt.svg
  berner_muenster_grundriss.svg
  berner_muenster_ansicht.svg
  berner_muenster_schnitt.svg
  st_peter_und_paul_grundriss.svg
  st_peter_und_paul_ansicht.svg
  st_peter_und_paul_schnitt.svg
  einsteinhaus_grundriss.svg
  einsteinhaus_ansicht.svg
  einsteinhaus_schnitt.svg
  kunstmuseum_grundriss.svg
  kunstmuseum_ansicht.svg
  kunstmuseum_schnitt.svg
  kornhaus_grundriss.svg
  kornhaus_ansicht.svg
  kornhaus_schnitt.svg
  hauptbahnhof_grundriss.svg
  hauptbahnhof_ansicht.svg
  hauptbahnhof_schnitt.svg
  stadttheater_grundriss.svg
  stadttheater_ansicht.svg
  stadttheater_schnitt.svg
  historisches_museum_grundriss.svg
  historisches_museum_ansicht.svg
  historisches_museum_schnitt.svg
  hotel_schweizerhof_grundriss.svg
  hotel_schweizerhof_ansicht.svg
  hotel_schweizerhof_schnitt.svg
```

---

## Naechste Schritte

1. **SVG-Vergleich:** Kopiere einen SVG-Prompt zu Claude.ai und vergleiche das Ergebnis
2. **Recherche-Analyse:** Pruefe ob die Zonen korrekt erkannt wurden
3. **Optimierungen:** Dokumentiere Verbesserungsvorschlaege

---

## Analyse mit Claude.ai

### Prompt fuer Gesamtanalyse

Kopiere diesen Text plus die relevanten Dateien zu Claude.ai:

```
Hier ist ein Test-Report unserer SVG-Generierungs-Pipeline.

Bitte analysiere:

1. **SVG-Qualitaet**
   - Sind die Proportionen korrekt?
   - Werden alle Zonen dargestellt?
   - Entspricht der Stil einer technischen Zeichnung?

2. **Recherche-Qualitaet**
   - Sind die Gebaeude korrekt erkannt?
   - Fehlen wichtige Hoehenzonen?
   - Welche Gebaeude sollten zu known_buildings.py hinzugefuegt werden?

3. **Prompt-Optimierung**
   - Was kann am SVG-Prompt verbessert werden?
   - Was kann am Recherche-Prompt verbessert werden?

4. **Priorisierte Massnahmen**
   - Quick Wins (sofort umsetzbar)
   - Mittelfristig (1-2 Tage)
   - Langfristig (ML-System)

[REPORT UND DATEIEN HIER EINFUEGEN]
```

---

*Generiert: {timestamp}*
*Script: test_svg_comparison.py*
