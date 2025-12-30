# Test-Dokumentation: Building Comparison

## Uebersicht

Diese Teststrategie prueft die Qualitaet der SmartBuildingService-Pipeline anhand von Berner Gebaeuden.

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
| Name erkannt | Nein oder via Claude Haiku |
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
7. Recherche          (known_buildings ODER Claude Haiku)
8. Zonen-Analyse      (bei COMPLEX: Claude Sonnet)
9. SUVA Zugaenge      (berechnet)
10. Qualitaetsbewertung (berechnet)
```

### Kosten (Claude API)

| Schritt | Modell | Kosten |
|---------|--------|--------|
| Recherche (unbekannt) | Haiku | ~$0.01 |
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

## Testergebnisse (30.12.2025 - nach Fixes)

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

*Stand: 30.12.2025*
*Letzte Aktualisierung: Nach BUG-001, BUG-002, BUG-003 Fixes*
