# Teststrategie: SVG-Qualität & Prompt-Optimierung

## Übersicht

Diese Teststrategie vergleicht die SVG-Generierung zwischen:
- **Claude API** (automatisch im Backend)
- **Claude.ai** (manuell mit exportiertem Prompt)

**Ziel:** Identische Prompts → vergleichbare Ergebnisse → Optimierungspotential erkennen

**Scope:** Aktuell beschränken wir uns auf **10 Gebäude der Stadt Bern** pro Testdurchlauf. Dies ermöglicht eine überschaubare manuelle Analyse mit Claude.ai und bildet die Grundlage für das spätere ML-System.

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TESTSTRATEGIE WORKFLOW                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. TEST AUSFÜHREN                                                  │
│     python scripts/test_svg_comparison.py                           │
│                                                                     │
│  2. GENERIERTE ARTEFAKTE (im Report-Ordner)                        │
│     ├── CLAUDE_AI_ANALYSE.md  ← HAUPTDATEI für Claude.ai          │
│     ├── report.md                       # Zusammenfassung          │
│     ├── results.json                    # Rohdaten                 │
│     ├── recherche_prompts/              # Einzelne Recherche-Docs  │
│     ├── svg_prompts/                    # Einzelne SVG-Prompts     │
│     └── svg_api/                        # Generierte SVGs          │
│                                                                     │
│  3. CLAUDE.AI ANALYSE (NUR 1 DATEI HOCHLADEN!)                     │
│     a) Öffne Claude.ai                                             │
│     b) Lade CLAUDE_AI_ANALYSE.md hoch                              │
│     c) Claude.ai generiert SVGs + analysiert + vergleicht          │
│     d) Erhalte Verbesserungsvorschläge                             │
│                                                                     │
│  4. ANALYSE & OPTIMIERUNG                                          │
│     a) Kopiere report.md + alle Prompts zu Claude.ai               │
│     b) Frage nach Optimierungsvorschlägen                          │
│     c) Implementiere Verbesserungen                                │
│                                                                     │
│  5. ITERATION                                                      │
│     → Wiederhole bis Qualität ausreichend                          │
│     → Dokumentiere Verbesserungen                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Auslöser

**Befehl:** `Teste gemäss Teststrategie` oder `Führe Teststrategie aus`

**Aktion:**
1. Cache leeren für Testgebäude (nur diese, nicht global!)
2. Test-Script ausführen
3. Report-Ordner mit Zeitstempel erstellen
4. Alle Artefakte generieren inkl. **CLAUDE_AI_ANALYSE.md**
5. Zusammenfassung ausgeben

**Wichtig:** Das Script generiert automatisch eine Datei `CLAUDE_AI_ANALYSE.md` die ALLES enthält (Prompts, SVGs, Anweisungen) - nur diese eine Datei zu Claude.ai hochladen!

---

## Cache-Handling

**Wichtig:** Das Test-Script leert den Cache **nur für die Testgebäude**, nicht global!

Dies stellt sicher, dass:
- Andere gecachte Daten erhalten bleiben
- Die Tests reproduzierbar sind (frische Daten für Testgebäude)
- Keine unnötigen API-Calls für unbeteiligte Gebäude entstehen

```python
# Im Script: Cache pro Gebäude leeren
for building in TEST_BUILDINGS:
    DELETE /api/v1/smart-building/cache?address={building.address}
```

---

## Test-Script

### Datei

```
backend/scripts/test_svg_comparison.py
```

### Ausführung

```bash
cd backend
python scripts/test_svg_comparison.py
```

### Parameter (optional)

```bash
# Nur bestimmte Gebäude
python scripts/test_svg_comparison.py --buildings "Bundeshaus,Münster"

# Nur bestimmte SVG-Typen
python scripts/test_svg_comparison.py --svg-types "schnitt,ansicht"

# Lokale API
python scripts/test_svg_comparison.py --api-url "http://localhost:8000"
```

---

## Generierte Artefakte

### 1. Recherche-Prompts

**Ordner:** `report-{timestamp}/recherche_prompts/`

Für jedes Gebäude wird der Prompt exportiert, der für die Claude-Recherche verwendet wird:

```markdown
# Recherche-Prompt: Bundeshaus

## System-Prompt
Du bist ein Experte für Schweizer Architektur...

## User-Prompt
Analysiere das Gebäude an der Adresse: Bundesplatz 3, 3011 Bern
...

## Erwartete Ausgabe
- building_name
- building_type
- zones[]
- ...
```

### 2. SVG-Prompts

**Ordner:** `report-{timestamp}/svg_prompts/`

Der **identische** Prompt der sowohl für Claude API als auch für Export verwendet wird:

```markdown
# SVG-Generierung: Bundeshaus - Schnitt

## Gebäudedaten
- Adresse: Bundesplatz 3, 3011 Bern
- EGID: 2242547
- Höhen: Traufe 53.2m, First 62.6m
...

## Zonen
1. Arkaden (6.0m)
2. Hauptgebäude (25.0-30.0m)
3. Kuppel (30.0-64.0m)

## SVG-Anforderungen
...
```

### 3. API-generierte SVGs

**Ordner:** `report-{timestamp}/svg_api/`

Die SVGs die von der Claude API generiert wurden:

- `bundeshaus_grundriss.svg`
- `bundeshaus_ansicht.svg`
- `bundeshaus_schnitt.svg`
- ...

### 4. Report

**Datei:** `report-{timestamp}/report.md`

```markdown
# Test-Report: {timestamp}

## Übersicht
| Gebäude | Grundriss | Ansicht | Schnitt | Zeit |
|---------|-----------|---------|---------|------|
| Bundeshaus | ✅ | ✅ | ✅ | 2.3s |
| Münster | ✅ | ✅ | ✅ | 1.8s |
...

## Recherche-Analyse
...

## SVG-Qualität
...

## Optimierungsvorschläge
(wird von Claude.ai ausgefüllt)
```

---

## Claude.ai Analyse

### Schritt 1: SVG-Vergleich

Kopiere zu Claude.ai:

```
Hier ist der Prompt den unsere API verwendet:

[Inhalt von svg_prompts/bundeshaus_schnitt_prompt.md]

Bitte generiere das SVG und vergleiche es mit diesem Ergebnis unserer API:

[Inhalt von svg_api/bundeshaus_schnitt.svg]

Analysiere:
1. Was macht die API richtig?
2. Was macht die API falsch?
3. Wie kann der Prompt verbessert werden?
```

### Schritt 2: Recherche-Optimierung

Kopiere zu Claude.ai:

```
Hier ist der Recherche-Prompt:

[Inhalt von recherche_prompts/bundeshaus_recherche.md]

Und hier das Ergebnis:

[building_name, zones, etc.]

Analysiere:
1. Ist das Ergebnis korrekt?
2. Fehlen wichtige Informationen?
3. Wie kann der Prompt verbessert werden?
```

### Schritt 3: Gesamtanalyse

Kopiere zu Claude.ai:

```
Hier ist der vollständige Test-Report:

[Inhalt von report.md]

Plus alle Prompts und SVGs.

Erstelle eine priorisierte Liste von Optimierungen:
1. Quick Wins (sofort umsetzbar)
2. Mittelfristig (1-2 Tage)
3. Langfristig (ML-System)
```

---

## Testgebäude

### Aktueller Scope: Stadt Bern (10 Gebäude)

Wir beschränken uns bewusst auf 10 Gebäude der Stadt Bern pro Testdurchlauf:
- **Überschaubare Menge** für manuelle Claude.ai Analyse
- **Mix aus Komplexitäten** (simple, moderate, complex)
- **Bekannte & unbekannte** Gebäude gemischt
- **Reproduzierbar** für Vergleiche zwischen Iterationen

### Standard-Set

| Nr | Adresse | Typ | Komplexität | Status |
|----|---------|-----|-------------|--------|
| 1 | Bundesplatz 3, 3011 Bern | Parlamentsgebäude | complex | bekannt |
| 2 | Münsterplatz 1, 3011 Bern | Kirche | complex | bekannt |
| 3 | Rathausgasse 2, 3011 Bern | Kirche | complex | bekannt |
| 4 | Kramgasse 49, 3011 Bern | Wohnhaus | simple | bekannt |
| 5 | Hodlerstrasse 8, 3011 Bern | Museum | complex | bekannt |
| 6 | Kornhausplatz 18, 3011 Bern | Kulturgebäude | complex | unbekannt |
| 7 | Bahnhofplatz 10, 3011 Bern | Bahnhof | complex | unbekannt |
| 8 | Theaterplatz 7, 3011 Bern | Theater | complex | unbekannt |
| 9 | Helvetiaplatz 5, 3005 Bern | Museum | complex | unbekannt |
| 10 | Bahnhofplatz 11, 3011 Bern | Hotel | moderate | unbekannt |

### Erweiterung (geplant)

Nach Abschluss der Bern-Optimierung:
- Weitere Städte: Zürich, Basel, Genf
- Spezialfälle: Industriegebäude, moderne Architektur
- Erhöhung auf 50-100 Gebäude für ML-Training

---

## Metriken

### Qualitäts-Kriterien SVG

| Kriterium | Gewichtung | Beschreibung |
|-----------|------------|--------------|
| Proportionen | 30% | Höhen/Breiten korrekt |
| Zonen | 25% | Alle Zonen dargestellt |
| Stil | 20% | Technische Zeichnung (nicht künstlerisch) |
| Details | 15% | Gerüst, Verankerungen, Zugänge |
| Lesbarkeit | 10% | Beschriftungen, Massstab |

### Qualitäts-Kriterien Recherche

| Kriterium | Gewichtung | Beschreibung |
|-----------|------------|--------------|
| Name korrekt | 30% | building_name stimmt |
| Zonen-Anzahl | 25% | Richtige Anzahl Zonen |
| Höhen plausibel | 25% | Zone-Höhen realistisch |
| Typ korrekt | 20% | building_type stimmt |

---

## Integration ML-System

Diese Teststrategie ist die Grundlage für das geplante ML-System:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ML LEARNING PIPELINE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. DATENSAMMLUNG (aktuell)                                        │
│     - Test-Reports speichern                                       │
│     - Claude.ai Feedback dokumentieren                             │
│     - Korrekturen erfassen                                         │
│                                                                     │
│  2. FEATURE-EXTRAKTION                                             │
│     - GKAT, Fläche, Polygon-Form                                   │
│     - Höhendifferenzen                                             │
│     - Geographische Lage                                           │
│                                                                     │
│  3. TRAINING                                                       │
│     - Zone-Template Klassifikation                                 │
│     - Komplexitäts-Erkennung                                       │
│     - Prompt-Parameter Optimierung                                 │
│                                                                     │
│  4. INFERENCE                                                      │
│     - ML statt Claude für 95% der Anfragen                        │
│     - Claude nur bei confidence < 0.8                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Checkliste

### Vor dem Test

- [ ] API erreichbar? (`curl https://acceptable-trust-production.up.railway.app/health`)
- [ ] Cache geleert? (wird automatisch vom Script gemacht)
- [ ] Genug Claude API Credits?

### Nach dem Test

- [ ] Report-Ordner vollständig?
- [ ] SVGs visuell geprüft?
- [ ] Claude.ai Analyse durchgeführt?
- [ ] Optimierungen dokumentiert?
- [ ] Code angepasst?
- [ ] Erneut getestet?

---

*Stand: 30.12.2025*
*Version: 2.0 (SVG-Vergleich + Prompt-Export)*
