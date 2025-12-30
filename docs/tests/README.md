# Test-Dokumentation

## AKTUELLE TESTSTRATEGIE

> **WICHTIG:** Die aktuelle Teststrategie ist in `TESTSTRATEGIE.md` dokumentiert!
>
> **Befehl:** `Teste gemaess Teststrategie` oder `Fuehre Teststrategie aus`
>
> **Script:** `python scripts/test_svg_comparison.py`

Die neue Teststrategie (v2.0) vergleicht SVG-Generierung zwischen Claude API und Claude.ai:
- Prompts exportieren (identisch fuer API & Claude.ai)
- SVGs generieren
- Mit Claude.ai vergleichen und optimieren

**Scope:** 10 Gebaeude der Stadt Bern pro Testdurchlauf (5 bekannte + 5 unbekannte)

---

# Legacy: Building Comparison

## Uebersicht

Diese aeltere Teststrategie prueft die Qualitaet der SmartBuildingService-Pipeline anhand von Berner Gebaeuden.

**Ziel:** Vergleich zwischen bekannten Gebaeuden (in `known_buildings.py`) und unbekannten Gebaeuden, um Optimierungspotential zu identifizieren.

---

## Test-Script

### Datei

```
backend/scripts/test_building_comparison.py
```

### Ausfuehrung

```bash
# Im Backend-Verzeichnis
cd backend
python scripts/test_building_comparison.py
```

### Konfiguration

Das Script testet standardmaessig 10 Gebaeude:

| Kategorie | Anzahl | Beispiele |
|-----------|--------|-----------|
| Bekannte Gebaeude | 4 | Bundeshaus, Muenster, St. Peter & Paul, Einsteinhaus |
| Unbekannte Gebaeude | 6 | Bahnhof, Kornhaus, Theater, Kunstmuseum, etc. |

### API-Endpunkt

```
GET /api/v1/smart-building/data?address=...
    &include_research=true
    &include_zones=true
    &include_terrain=true
```

---

## Ausgabe-Dateien

### 1. JSON-Rohdaten

**Datei:** `docs/tests/building_comparison_results.json`

Enthaelt:
- Timestamp
- API-Metriken (Anzahl, Zeiten, Fehler)
- Vollstaendige Ergebnisse pro Gebaeude
- Rohdaten der API-Response

### 2. Analyse-Prompt

**Datei:** `docs/tests/building_comparison_prompt.md`

Markdown-Dokument zum Kopieren in Claude.ai fuer:
- Datenqualitaets-Analyse
- Zonen-Erkennung-Bewertung
- Optimierungsvorschlaege

---

## Erwartete Ergebnisse

### Bekannte Gebaeude

| Kriterium | Erwartung |
|-----------|-----------|
| Name erkannt | Ja (aus known_buildings.py) |
| Zonen korrekt | Ja (vordefiniert) |
| Response-Zeit | < 1 Sekunde (kein Claude-Call) |
| Komplexitaet | Korrekt klassifiziert |

### Unbekannte Gebaeude

| Kriterium | Erwartung |
|-----------|-----------|
| Name erkannt | Nein oder via Claude Sonnet |
| Zonen | 1-2 (Standard-Fallback) |
| Response-Zeit | 10-20 Sekunden (Claude API) |
| Hoehendaten | Aus swissBUILDINGS3D |

---

## Metriken

### Response-Zeiten (Richtwerte)

| Szenario | Zeit |
|----------|------|
| Bekanntes Gebaeude (Cache Hit) | 300-800ms |
| Bekanntes Gebaeude (Cache Miss) | 1-3s |
| Unbekanntes Gebaeude (Claude) | 10-20s |
| Unbekanntes Gebaeude + On-Demand Hoehen | 20-30s |

### API-Calls pro Gebaeude

Die SmartBuildingService-Pipeline:

```
1. Geocoding          (swisstopo API)
2. GWR-Daten          (swisstopo API)
3. Hoehendaten        (DB oder STAC On-Demand)
4. Terrain            (swissALTI3D API)
5. Polygon            (geodienste.ch WFS)
6. Dach-Analyse       (berechnet)
7. Recherche          (known_buildings ODER Claude Sonnet)
8. Zonen-Analyse      (bei COMPLEX: Claude Sonnet)
9. SUVA Zugaenge      (berechnet)
10. Qualitaetsbewertung (berechnet)
```

### Kosten (Claude API)

| Schritt | Modell | Kosten |
|---------|--------|--------|
| Recherche (unbekannt) | Sonnet | ~$0.03-0.05 |
| Zonen-Analyse (komplex) | Sonnet | ~$0.05-0.15 |
| Bekanntes Gebaeude | - | $0.00 |

---

## Interpretation der Ergebnisse

### Status-Codes

| Status | Bedeutung |
|--------|-----------|
| OK | Name und Zonen stimmen mit Erwartung ueberein |
| WARNUNG | Abweichung bei Name oder Zonen-Anzahl |
| FEHLER | API-Call fehlgeschlagen |

### Haeufige Probleme

| Problem | Ursache | Loesung |
|---------|---------|---------|
| `building_name = N/A` | Claude-Recherche fehlgeschlagen | Gebaeude zu known_buildings.py hinzufuegen |
| Nur 1 Zone bei komplexem Gebaeude | Keine Hoehendifferenz erkannt | Manuell Zonen definieren |
| Timeout | API-Ueberlastung | Erneut versuchen |
| Falsche Hoehen | EGID-Mismatch | Koordinaten-Lookup pruefen |

---

## Erweiterung der Tests

### Neue Gebaeude hinzufuegen

1. **In test_building_comparison.py:**

```python
# Bekanntes Gebaeude (mit known_buildings.py Eintrag)
KNOWN_BUILDINGS = {
    "Neue Adresse, PLZ Ort": {
        "name": "Gebaeudebezeichnung",
        "egid": "1234567",
        "expected_zones": 3,
        "zone_names": ["Zone1", "Zone2", "Zone3"],
        "max_height": 50.0,
        "is_known": True,
    },
}

# Unbekanntes Gebaeude (ohne known_buildings.py Eintrag)
UNKNOWN_BUILDINGS = {
    "Neue Adresse, PLZ Ort": {
        "name": "Erwarteter Name",
        "expected_type": "Gebaeudetyp",
        "is_known": False,
    },
}
```

2. **Optional in known_buildings.py:**

```python
"EGID": {
    "egid": "EGID",
    "building_name": "Name",
    "building_type": "Typ",
    "zones": [...],
    ...
}
```

### Lokale Tests

```python
# In test_building_comparison.py
API_BASE_URL = "http://localhost:8000"  # Statt Railway
```

---

## Workflow: Neue Stadt testen

1. **Adressen recherchieren:**
   - 4-5 bekannte Wahrzeichen
   - 5-6 normale Gebaeude

2. **Script anpassen:**
   - Adressen eintragen
   - Erwartungen definieren

3. **Test ausfuehren:**
   ```bash
   python scripts/test_building_comparison.py
   ```

4. **Ergebnisse analysieren:**
   - Claude.ai Prompt kopieren
   - Optimierungen identifizieren

5. **Bekannte Gebaeude ergaenzen:**
   - Wahrzeichen zu known_buildings.py hinzufuegen
   - Tests erneut ausfuehren

---

## Beispiel-Ergebnisse (30.12.2025)

### Zusammenfassung Bern

| Metrik | Wert |
|--------|------|
| Getestete Gebaeude | 10 |
| Bekannte Gebaeude | 4 (100% Erfolg) |
| Unbekannte Gebaeude | 6 (Hoehen OK, Namen fehlen) |
| Durchschnittliche Response | 10.2s |

### Erkenntnisse

1. **Staerken:**
   - Bekannte Gebaeude werden perfekt erkannt
   - Hoehendaten aus swissBUILDINGS3D funktionieren
   - Zonen-Struktur ist korrekt

2. **Schwaechen:**
   - Unbekannte Gebaeude: Kein building_name
   - Lange Response-Zeit bei Claude-Calls
   - Nur 1-2 Zonen bei unbekannten komplexen Gebaeuden

3. **Empfehlungen:**
   - Wichtige Wahrzeichen zu known_buildings.py hinzufuegen
   - Caching verbessern
   - Fallback-Zonen fuer Gebaeudetypen definieren

---

## Referenzen

- [SmartBuildingService Architektur](../../.claude/rules/smart-building.md)
- [known_buildings.py](../../backend/app/services/smart_building/known_buildings.py)
- [API-Standards](../../.claude/rules/api-standards.md)

---

## Manuelles Testverfahren (curl + Claude.ai)

Dieses Verfahren ermoeglicht schnelle Tests ohne Python-Umgebung.

### Schritt 1: Test-Adressen definieren

```
# Bekannte Gebaeude (in known_buildings.py)
Bundesplatz 3, 3011 Bern          # Bundeshaus
Muensterplatz 1, 3011 Bern        # Berner Muenster
Rathausgasse 2, 3011 Bern         # St. Peter und Paul
Kramgasse 49, 3011 Bern           # Einsteinhaus
Hodlerstrasse 8, 3011 Bern        # Kunstmuseum
Kornhausplatz 18, 3011 Bern       # Kornhaus
Bahnhofplatz 10, 3011 Bern        # Hauptbahnhof
Theaterplatz 7, 3011 Bern         # Stadttheater
Helvetiaplatz 5, 3005 Bern        # Historisches Museum
Bahnhofplatz 11, 3011 Bern        # Hotel Schweizerhof

# Unbekannte Gebaeude (zum Testen der Claude-Recherche)
Marktgasse 10, 3011 Bern          # Wohnhaus
Spitalgasse 4, 3011 Bern          # Geschaeftshaus
```

### Schritt 2: API-Daten abrufen

**Basis-URL:**
```
# Production (Railway)
https://acceptable-trust-production.up.railway.app

# Lokal
http://localhost:8000
```

**Einzelnes Gebaeude testen:**
```bash
# Ersetze ADRESSE mit URL-encodierter Adresse
# z.B. "Bundesplatz%203%2C%203011%20Bern"

curl -s "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/data?address=ADRESSE"
```

**Schnelltest (nur Name und Zonen):**
```bash
curl -s "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/data?address=Bundesplatz%203%2C%203011%20Bern" | grep -o '"building_name":"[^"]*"\|"complexity":"[^"]*"'
```

### Schritt 3: Batch-Test Script

Kopiere dieses Script in eine Datei `test_batch.sh`:

```bash
#!/bin/bash
# Batch-Test fuer Berner Gebaeude

API="https://acceptable-trust-production.up.railway.app/api/v1/smart-building/data"

echo "=== GEBAEUDE-TEST $(date) ==="
echo ""

# Funktion zum Testen
test_building() {
    local name="$1"
    local addr="$2"
    echo -n "$name: "
    result=$(curl -s "$API?address=$addr" 2>/dev/null)
    building_name=$(echo "$result" | grep -o '"building_name":"[^"]*"' | cut -d'"' -f4)
    complexity=$(echo "$result" | grep -o '"complexity":"[^"]*"' | cut -d'"' -f4)
    echo "$building_name | $complexity"
}

# Tests ausfuehren
test_building "Bundeshaus" "Bundesplatz%203%2C%203011%20Bern"
test_building "Muenster" "Muensterplatz%201%2C%203011%20Bern"
test_building "St. Peter" "Rathausgasse%202%2C%203011%20Bern"
test_building "Kunstmuseum" "Hodlerstrasse%208%2C%203011%20Bern"
test_building "Kornhaus" "Kornhausplatz%2018%2C%203011%20Bern"
test_building "Bahnhof" "Bahnhofplatz%2010%2C%203011%20Bern"
test_building "Theater" "Theaterplatz%207%2C%203011%20Bern"
test_building "Hist.Museum" "Helvetiaplatz%205%2C%203005%20Bern"
test_building "Schweizerhof" "Bahnhofplatz%2011%2C%203011%20Bern"

echo ""
echo "=== ENDE ==="
```

### Schritt 4: Vollstaendige JSON-Daten sammeln

Fuer eine detaillierte Analyse, sammle die kompletten JSON-Responses:

```bash
#!/bin/bash
# Sammelt vollstaendige API-Responses in eine Datei

API="https://acceptable-trust-production.up.railway.app/api/v1/smart-building/data"
OUTPUT="test_results_$(date +%Y%m%d_%H%M%S).json"

echo "[" > "$OUTPUT"

addresses=(
    "Bundesplatz%203%2C%203011%20Bern"
    "Muensterplatz%201%2C%203011%20Bern"
    "Rathausgasse%202%2C%203011%20Bern"
    "Hodlerstrasse%208%2C%203011%20Bern"
    "Kornhausplatz%2018%2C%203011%20Bern"
    "Bahnhofplatz%2010%2C%203011%20Bern"
    "Theaterplatz%207%2C%203011%20Bern"
    "Helvetiaplatz%205%2C%203005%20Bern"
    "Bahnhofplatz%2011%2C%203011%20Bern"
)

first=true
for addr in "${addresses[@]}"; do
    echo "Fetching: $addr"
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$OUTPUT"
    fi
    curl -s "$API?address=$addr" >> "$OUTPUT"
done

echo "]" >> "$OUTPUT"
echo "Results saved to: $OUTPUT"
```

### Schritt 5: Prompt fuer Claude.ai

Kopiere den folgenden Prompt und fuege die JSON-Daten ein:

---

```markdown
# Gebaeude-Datenanalyse

## Kontext

Ich teste die SmartBuildingService API fuer Schweizer Gebaeude.
Die API sammelt Daten aus verschiedenen Quellen:
- Geocoding (swisstopo)
- GWR (Gebaeuderegister)
- swissBUILDINGS3D (Hoehendaten)
- geodienste.ch (Polygon)
- known_buildings.py (vordefinierte Gebaeude)

## Erwartungen

Bekannte Gebaeude sollten:
- `building_name` aus known_buildings.py haben
- Korrekte Hoehenzonen (z.B. Kunstmuseum: 3 Zonen)
- `complexity: "complex"` bei oeffentlichen Gebaeuden

## Test-Daten

Hier sind die API-Responses fuer 10 Berner Gebaeude:

```json
[HIER JSON-DATEN EINFUEGEN]
```

## Analyse-Aufgaben

Bitte analysiere die Daten und beantworte:

1. **Erkennungsrate:**
   - Wie viele Gebaeude haben einen `building_name`?
   - Bei welchen fehlt der Name?

2. **Hoehendaten:**
   - Sind die Hoehen plausibel?
   - Gibt es Ausreisser (z.B. zu niedrig/hoch)?

3. **Zonen-Qualitaet:**
   - Haben komplexe Gebaeude mehrere Zonen?
   - Stimmen die Zonen-Typen (arkade, hauptgebaeude, turm)?

4. **Probleme:**
   - Welche Gebaeude haben fehlerhafte Daten?
   - Was sind moegliche Ursachen?

5. **Empfehlungen:**
   - Welche Gebaeude sollten zu known_buildings.py hinzugefuegt werden?
   - Welche Optimierungen sind sinnvoll?

## Format

Bitte antworte mit:
- Zusammenfassungs-Tabelle
- Detaillierte Analyse pro Problemfall
- Priorisierte Empfehlungen
```

---

### Schritt 6: Ergebnisse interpretieren

**Erfolgreicher Test:**
```
Bundeshaus: Bundeshaus | complex
Muenster: Berner Muenster | complex
St. Peter: Kirche St. Peter und Paul | complex
Kunstmuseum: Kunstmuseum Bern | complex
```

**Fehlgeschlagener Test:**
```
Unbekannt: null | simple
```
→ Gebaeude nicht in known_buildings.py und Claude-Recherche fehlgeschlagen

### Schritt 7: Fixes dokumentieren

Nach der Analyse von Claude.ai:

1. **Bugs in `docs/roadmap/CURRENT_BUGS.md` erfassen**
2. **Fixes implementieren**
3. **Tests wiederholen**
4. **Commit mit Referenz zum Bug**

---

## URL-Encoding Referenz

| Zeichen | Encoded |
|---------|---------|
| Leerzeichen | `%20` |
| Komma | `%2C` |
| Punkt | `.` (kein Encoding) |
| Umlaut ae | `%C3%A4` |
| Umlaut oe | `%C3%B6` |
| Umlaut ue | `%C3%BC` |

**Beispiele:**
```
Bundesplatz 3, 3011 Bern
→ Bundesplatz%203%2C%203011%20Bern

Münsterplatz 1, 3011 Bern
→ M%C3%BCnsterplatz%201%2C%203011%20Bern
(oder einfach: Muensterplatz%201%2C%203011%20Bern)
```

---

## Test-Reports (chronologisch)

### Report 30.12.2025 17:11 (AKTUELL)

**Ordner:** `docs/tests/report-20251230_1711/`

| Metrik | Wert |
|--------|------|
| Getestete Gebaeude | 10 |
| Erfolgsrate | 100% |
| Durchschnittszeit | 418ms |
| Cache geleert vor Test | Ja |

**Ergebnisse:**

| Gebaeude | building_name | complexity | Zonen | Zeit |
|----------|---------------|------------|-------|------|
| Bundeshaus | Bundeshaus | complex | 3/3 | 641ms |
| Berner Muenster | Berner Muenster | complex | 3/3 | ~400ms |
| St. Peter und Paul | Kirche St. Peter und Paul | complex | 4/4 | 372ms |
| Einsteinhaus | Einsteinhaus | simple | 1/1 | ~350ms |
| Kunstmuseum | Kunstmuseum Bern | complex | ~2 | ~400ms |
| Kornhaus | Kornhaus | complex | ~2 | ~400ms |
| Hauptbahnhof | Hauptbahnhof Bern | complex | ~2 | ~400ms |
| Stadttheater | Konzert Theater Bern | complex | ~2 | ~400ms |
| Historisches Museum | Bernisches Historisches Museum | complex | ~2 | ~400ms |
| Hotel Schweizerhof | Hotel Schweizerhof Bern | moderate | ~2 | ~400ms |

**Neue Features getestet:**
- height_override fuer Kunstmuseum
- Polygon-Form-Analyse (convexity-based)
- Hoehen-Validierung (BUG-011/012)

---

## Testergebnisse (frueherer Test - Referenz)

### Alle 10 Gebaeude erkannt

| Gebaeude | building_name | complexity | Status |
|----------|---------------|------------|--------|
| Bundeshaus | Bundeshaus | complex | ✅ |
| Berner Muenster | Berner Muenster | complex | ✅ |
| St. Peter und Paul | Kirche St. Peter und Paul | complex | ✅ |
| Einsteinhaus | Einsteinhaus | simple | ✅ |
| Kunstmuseum | Kunstmuseum Bern | complex | ✅ |
| Kornhaus | Kornhaus | complex | ✅ |
| Hauptbahnhof | Hauptbahnhof Bern | complex | ✅ |
| Stadttheater | Konzert Theater Bern | complex | ✅ |
| Historisches Museum | Bernisches Historisches Museum | complex | ✅ |
| Hotel Schweizerhof | Hotel Schweizerhof Bern | moderate | ✅ |

### Implementierte Fixes

1. **BUG-001:** Kunstmuseum Hoehendaten korrigiert (known_buildings.py)
2. **BUG-002:** 6 Berner Gebaeude hinzugefuegt (known_buildings.py)
3. **BUG-003:** Request-Deduplizierung (service.py)
4. **Address-Matching:** Komma-Toleranz (known_buildings.py)

---

## Claude.ai Analyse-Optionen

Nach dem Testlauf stehen **3 Analyse-Dateien** zur Verfuegung, die an Claude.ai uebergeben werden koennen:

### Option 1: Pipeline-Schritte analysieren

**Datei:** `docs/tests/pipeline_analyse.md`

**Inhalt:**
- Dokumentation aller 10 Pipeline-Schritte
- API-Aufrufe und Response-Beispiele
- Identifizierte Probleme pro Schritt
- Empfehlungen zur Optimierung

**Geeignet fuer:**
- Verstaendnis der Datenfluss-Architektur
- Identifikation von Bottlenecks
- Optimierung einzelner Schritte

### Option 2: SVG generieren und bewerten

**Datei:** `docs/tests/svg_generation_analysis.md`

**Inhalt:**
- Vollstaendiger Prompt fuer ein Gebaeude (Bundeshaus)
- Bewertungskriterien (U-Form, Ehrenhof, Proportionen)
- Checklisten fuer Grundriss, Ansicht, Schnitt
- Feedback-Format Vorlage

**Geeignet fuer:**
- SVG-Generierung testen
- Prompt-Qualitaet bewerten
- Verbesserungsvorschlaege sammeln

### Option 3: Datenqualitaet pruefen

**Datei:** `docs/tests/svg_datenqualitaet_vergleich.md`

**Inhalt:**
- Vergleich API-Daten vs. Zonen-Hoehen
- Konsistenz-Analyse (Zone > API-First?)
- Fehlerhafte Daten identifizieren
- Priorisierte Empfehlungen

**Geeignet fuer:**
- Datenqualitaets-Audit
- known_buildings.py Korrekturen
- Hoehen-Validierung verbessern

### Workflow mit Claude.ai

```
┌─────────────────────────────────────────────────────────────┐
│                 ANALYSE-WORKFLOW                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Test ausfuehren                                         │
│     python scripts/test_building_comparison.py              │
│                                                              │
│  2. Option waehlen                                          │
│     → Pipeline-Analyse     (Architektur verstehen)          │
│     → SVG-Generierung      (Visualisierung testen)          │
│     → Datenqualitaet       (Fehler finden)                  │
│                                                              │
│  3. Datei an Claude.ai senden                               │
│     Kopiere Inhalt der gewaehlten .md Datei                 │
│                                                              │
│  4. Ergebnisse auswerten                                    │
│     → Bugs in CURRENT_BUGS.md erfassen                      │
│     → Fixes implementieren                                  │
│     → Tests wiederholen                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Geplant: ML Learning System

> **Status:** In Planung
> **Dokumentation:** [docs/roadmap/ML_LEARNING_SYSTEM.md](../roadmap/ML_LEARNING_SYSTEM.md)

### Motivation

Aktuell werden Gebaeude entweder:
- **Bekannt:** Manuell in `known_buildings.py` definiert (kostenlos, sofort)
- **Unbekannt:** Via Claude API recherchiert (~$0.05-0.15, 10-20s)

**Problem:** Manuelle Pflege skaliert nicht. Claude-Calls sind teuer bei vielen Abfragen.

### Loesung: Automatisches Lernen

```
┌─────────────────────────────────────────────────────────────┐
│                  ML LEARNING SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: Datensammlung (0-500 Gebaeude)                    │
│  ────────────────────────────────────────                   │
│  - Claude analysiert neue Gebaeude                          │
│  - Ergebnisse werden in training_data.parquet gespeichert   │
│  - Manuelles Review fuer Qualitaetssicherung               │
│                                                              │
│  Phase 2: ML-Training (500+ Gebaeude)                       │
│  ────────────────────────────────────────                   │
│  - XGBoost / Random Forest Classifier                       │
│  - Features: GKAT, Hoehen, Polygon-Form, Flaeche            │
│  - Target: Zone-Template (z.B. "kirche_mit_turm")           │
│                                                              │
│  Phase 3: Production (1000+ Gebaeude)                       │
│  ────────────────────────────────────────                   │
│  - ML-Inference fuer 95% der Anfragen                       │
│  - Claude nur bei confidence < 0.8                          │
│  - Kontinuierliches Lernen aus Korrekturen                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Kosten-Vergleich (Prognose)

| Szenario | Aktuell (Claude) | Mit ML |
|----------|------------------|--------|
| 100 Gebaeude | $5-15 | $0.50 (Training) |
| 1000 Gebaeude | $50-150 | $0.50 |
| 10000 Gebaeude | $500-1500 | $0.50 |

### Naechste Schritte

1. ✅ Bugs beheben (BUG-001 bis BUG-009)
2. ⏳ Trainingsdaten aus aktuellen Tests exportieren
3. ⏳ Feature-Branch `feature/ml-learning-system` erstellen
4. ⏳ TrainingDataCollector implementieren

---

## Test-Prozedur (aktualisiert 30.12.2025)

### Vollstaendiger Test-Workflow

```bash
# 1. Cache leeren (API-Call)
curl -X DELETE "https://acceptable-trust-production.up.railway.app/api/v1/smart-building/cache"

# 2. Tests ausfuehren
cd backend
python scripts/test_building_comparison.py

# 3. Report-Ordner erstellen (Format: report-YYYYMMDD_HHMM)
mkdir -p docs/tests/report-$(date +%Y%m%d_%H%M)

# 4. Ergebnisse kopieren
cp docs/tests/building_comparison_*.* docs/tests/report-$(date +%Y%m%d_%H%M)/

# 5. README im Report-Ordner erstellen (optional)
```

### Cache-Clearing Endpoint

```bash
# Alle Caches leeren
DELETE /api/v1/smart-building/cache

# Nur fuer bestimmte Adresse
DELETE /api/v1/smart-building/cache?address=Bundesplatz%203,%203011%20Bern

# Nur bestimmten Cache-Typ
DELETE /api/v1/smart-building/cache?cache_type=bundle  # oder: research, svg
```

### Report-Ordner Struktur

```
docs/tests/
├── README.md                    # Diese Dokumentation
├── building_comparison_*.json   # Aktuelle Rohdaten
├── building_comparison_*.md     # Aktueller Prompt
└── report-YYYYMMDD_HHMM/        # Archivierte Reports
    ├── README.md                # Report-Zusammenfassung
    ├── building_comparison_results.json
    └── building_comparison_prompt.md
```

---

*Stand: 30.12.2025*
*Letzte Aktualisierung: Test-Reports mit Zeitstempel + Cache-Clearing Dokumentation*
