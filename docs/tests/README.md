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

*Stand: 30.12.2025*
