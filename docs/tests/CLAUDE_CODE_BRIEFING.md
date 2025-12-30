# Claude Code Briefing: geodaten-ch Qualitätsverbesserungen

> **Erstellt:** 30. Dezember 2025
> **Kontext:** Qualitätsanalyse der SVG-Generierungs-Pipeline
> **Projekt:** C:\Users\vonro\projects\geodaten-ch
> **Repository:** https://github.com/andreasrothbern/geodaten-ch/

---

## Zusammenfassung

Die SmartBuildingService-Pipeline wurde analysiert. Es wurden **2 kritische Fehler** und **mehrere Verbesserungsmöglichkeiten** identifiziert. Dieses Dokument enthält alle notwendigen Informationen und konkreten Aufgaben für die Umsetzung.

---

## Teil 1: Kritische Fixes (P0) - SOFORT UMSETZEN

### Fix 1: Einsteinhaus Zone-Höhe korrigieren

**Datei:** `app/services/smart_building/known_buildings.py`

**Problem:** Die Zone-Höhe (12-16m) ist niedriger als die API-Traufhöhe (22.3m). Das ist ein Datenfehler.

**Suche nach diesem Eintrag:**
```python
# Einsteinhaus - Kramgasse 49
```

**Korrigiere die Zone von:**
```python
"zones": [
    {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 12.0, "first": 16.0}
]
```

**Zu:**
```python
"zones": [
    {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 22.0, "first": 26.0}
]
```

**Begründung:** API liefert Traufe 22.3m, First 26.2m - die Zone muss diese Werte widerspiegeln.

---

### Fix 2: Kunstmuseum Override hinzufügen

**Datei:** `app/services/smart_building/known_buildings.py`

**Problem:** Die swissBUILDINGS3D API liefert falsche Höhen (6.7m/7.9m) - vermutlich wird nur ein Nebengebäude gemessen. Die realen Höhen sind 15-18m (Altbau) und 12-15m (Neubau).

**Suche nach dem Kunstmuseum-Eintrag** (falls vorhanden) oder **füge hinzu:**

```python
# Kunstmuseum Bern - Hodlerstrasse 8
"kunstmuseum_bern": {
    "egid": None,  # EGID aus API ermitteln
    "addresses": ["Hodlerstrasse 8, 3011 Bern", "Hodlerstrasse 8"],
    "building_name": "Kunstmuseum Bern",
    "building_type": "Museum",
    "architectural_style": "Historismus / Moderne Erweiterung",
    "construction_year": 1879,
    "building_shape": "Komplex mit mehreren Baukörpern",
    "building_shape_description": "Das Kunstmuseum besteht aus dem historischen Altbau (Stettler-Bau 1879), dem Neubau und der modernen Erweiterung. Die Gebäudeteile haben unterschiedliche Höhen.",
    "special_features": ["Altbau", "Neubau", "Erweiterung", "Museumsgarten"],
    
    # KRITISCH: API-Höhen sind FALSCH - manueller Override
    "height_override": {
        "enabled": True,
        "reason": "swissBUILDINGS3D misst nur Nebengebäude (6.7m). Reale Höhen manuell erfasst.",
        "traufhoehe_m": 15.0,
        "firsthoehe_m": 18.0
    },
    
    "zones": [
        {"name": "Altbau (Stettler)", "type": "hauptgebaeude", "traufe": 15.0, "first": 18.0, "sonderkonstruktion": False},
        {"name": "Neubau", "type": "hauptgebaeude", "traufe": 12.0, "first": 15.0, "sonderkonstruktion": False},
        {"name": "Erweiterung", "type": "anbau", "traufe": 8.0, "first": 10.0, "sonderkonstruktion": False}
    ],
    
    "svg_hints": {
        "grundriss": "Mehrere verbundene Baukörper. Altbau im Zentrum, Neubau und Erweiterung angrenzend.",
        "ansicht": "Unterschiedliche Höhen der Gebäudeteile darstellen. Altbau am höchsten.",
        "schnitt": "Zeige die verschiedenen Deckenhöhen der Museumssäle."
    }
}
```

**Zusätzlich:** Falls die Service-Logik `height_override` noch nicht unterstützt, muss diese implementiert werden (siehe Teil 2).

---

## Teil 2: Service-Erweiterungen (P1)

### Erweiterung 1: Height Override Support

**Datei:** `app/services/smart_building/service.py`

**Aufgabe:** Wenn ein Gebäude in `known_buildings.py` ein `height_override` hat, sollen diese Werte statt der API-Werte verwendet werden.

**Suche nach der Stelle, wo Höhendaten gesetzt werden** (vermutlich in einer Methode wie `_get_height_data` oder `_enrich_building_data`).

**Füge diese Logik hinzu:**

```python
def _apply_height_override(self, bundle: BuildingBundle, known_building: dict) -> BuildingBundle:
    """Wendet manuellen Höhen-Override an, falls in known_buildings definiert."""
    
    height_override = known_building.get("height_override", {})
    
    if height_override.get("enabled", False):
        # Manuellen Override anwenden
        bundle.traufhoehe_m = height_override.get("traufhoehe_m", bundle.traufhoehe_m)
        bundle.firsthoehe_m = height_override.get("firsthoehe_m", bundle.firsthoehe_m)
        bundle.height_source = "manual_override"
        
        # Warnung loggen
        reason = height_override.get("reason", "Manueller Override ohne Begründung")
        bundle.warnings.append(f"Höhen-Override aktiv: {reason}")
        
        logger.info(f"Height override applied for {bundle.building_name}: "
                   f"Traufe={bundle.traufhoehe_m}m, First={bundle.firsthoehe_m}m")
    
    return bundle
```

**Rufe diese Methode auf**, nachdem die API-Höhen geladen wurden, aber bevor die Zonen-Analyse startet.

---

### Erweiterung 2: Höhen-Validierung

**Datei:** `app/services/smart_building/service.py`

**Aufgabe:** Automatische Warnung, wenn Zone-Höhen und API-Höhen stark abweichen.

**Füge diese Validierungsmethode hinzu:**

```python
def _validate_zone_heights(self, bundle: BuildingBundle) -> list[str]:
    """Validiert Zone-Höhen gegen API-Höhen und generiert Warnungen."""
    
    warnings = []
    
    if not bundle.zones or not bundle.firsthoehe_m:
        return warnings
    
    max_zone_height = max(z.get("first", 0) for z in bundle.zones)
    min_zone_height = min(z.get("traufe", float("inf")) for z in bundle.zones)
    
    # Fall 1: Zone deutlich höher als API-First (>50%)
    if max_zone_height > bundle.firsthoehe_m * 1.5:
        warnings.append(
            f"Zone-Höhe ({max_zone_height}m) überschreitet API-First ({bundle.firsthoehe_m}m) um >50%. "
            f"Mögliche Ursache: Turm/Kuppel nicht in swissBUILDINGS3D erfasst."
        )
    
    # Fall 2: Zone niedriger als API-Traufe (Datenfehler!)
    if max_zone_height < bundle.traufhoehe_m * 0.8:
        warnings.append(
            f"FEHLER: Max. Zone-Höhe ({max_zone_height}m) ist niedriger als API-Traufe ({bundle.traufhoehe_m}m). "
            f"Zone-Daten in known_buildings.py prüfen!"
        )
    
    # Fall 3: API-Höhe unplausibel niedrig für Gebäudekategorie
    if bundle.gkat in [1060, 1080, 1110] and bundle.firsthoehe_m < 12:
        warnings.append(
            f"API-First ({bundle.firsthoehe_m}m) unplausibel niedrig für GKAT {bundle.gkat}. "
            f"Möglicherweise falsches Gebäude gemessen."
        )
    
    return warnings
```

**Rufe diese Methode auf** und füge die Warnungen zu `bundle.warnings` hinzu.

---

### Erweiterung 3: Height Source Tracking

**Datei:** `app/models/building.py` (oder wo das BuildingBundle definiert ist)

**Aufgabe:** Neues Feld `height_source` hinzufügen, um die Herkunft der Höhendaten zu tracken.

```python
class BuildingBundle:
    # ... bestehende Felder ...
    
    height_source: str = "unknown"
    # Mögliche Werte:
    # - "swissBUILDINGS3D" (API-Daten)
    # - "estimated" (aus Geschosszahl geschätzt)
    # - "manual_override" (aus known_buildings.py)
    # - "stac_api" (On-Demand STAC Fetch)
```

**Setze diesen Wert** an der Stelle, wo die Höhendaten ermittelt werden.

---

## Teil 3: Dokumentation aktualisieren

### CLAUDE.md erweitern

**Datei:** `CLAUDE.md` (im Root des Projekts)

**Füge diesen Abschnitt hinzu:**

```markdown
## Bekannte Datenqualitäts-Issues

### swissBUILDINGS3D Limitierungen

Die swissBUILDINGS3D API hat folgende bekannte Einschränkungen:

1. **Nur Hauptgebäude gemessen:** Türme, Kuppeln und Dachreiter werden oft nicht separat erfasst
2. **Manchmal falsches Gebäude:** Bei Gebäudekomplexen wird teilweise nur ein Nebengebäude gemessen
3. **Keine Zonen-Differenzierung:** Es gibt nur einen Trauf- und First-Wert pro EGID

### Umgang mit falschen API-Höhen

Wenn API-Höhen offensichtlich falsch sind:

1. Eintrag in `known_buildings.py` mit `height_override` erstellen
2. `enabled: True` und `reason` mit Begründung setzen
3. Realistische Höhen basierend auf Recherche eintragen

### Validierung

Die Service-Pipeline validiert automatisch:
- Zone-Höhen vs. API-Höhen
- Plausibilität für Gebäudekategorie (GKAT)
- Warnungen werden in `bundle.warnings` gesammelt
```

---

## Teil 4: Test-Checkliste

Nach der Implementierung folgende Tests durchführen:

### Manuelle Tests

```bash
# Test 1: Einsteinhaus (korrigierte Zone)
curl "http://localhost:8000/api/v1/building/smart?address=Kramgasse%2049,%203011%20Bern"
# Erwartung: zones[0].first = 26.0 (nicht 16.0)

# Test 2: Kunstmuseum (Height Override)
curl "http://localhost:8000/api/v1/building/smart?address=Hodlerstrasse%208,%203011%20Bern"
# Erwartung: height_source = "manual_override", firsthoehe_m = 18.0 (nicht 7.9)

# Test 3: Bundeshaus (Validierung)
curl "http://localhost:8000/api/v1/building/smart?address=Bundesplatz%203,%203011%20Bern"
# Erwartung: Keine Fehler-Warnung (Zone 64m > API 62.6m ist OK wegen Kuppel)
```

### Automatisierte Tests

Falls vorhanden, erweitere die Tests in `tests/`:

```python
def test_height_override_applied():
    """Testet, dass height_override korrekt angewendet wird."""
    result = smart_building_service.get_building("Hodlerstrasse 8, 3011 Bern")
    assert result.height_source == "manual_override"
    assert result.firsthoehe_m == 18.0

def test_zone_validation_warning():
    """Testet, dass Zone < API-Traufe eine Warnung generiert."""
    # Simuliere falschen Zone-Eintrag
    result = smart_building_service.get_building("Test-Adresse")
    assert any("FEHLER" in w for w in result.warnings)
```

---

## Teil 5: Daten-Referenz

### API-Testergebnisse (aus all_test_results.json)

| Plattform | Erfolgsrate | Ø Antwortzeit |
|-----------|-------------|---------------|
| swisstopo | 100% (8/8) | 222ms |
| GWR | 44% (4/9) | 210ms |
| geodienste.ch | 50% (4/8) | 143ms |

**Empfehlung:** swisstopo als primäre Datenquelle beibehalten.

### Gebäude mit bekannten Höhen-Problemen

| Gebäude | API-First | Reale Höhe | Problem |
|---------|-----------|------------|---------|
| Kunstmuseum | 7.9m | ~18m | API misst Nebengebäude |
| Einsteinhaus | 26.2m | 26.0m | Zone war falsch (16m) |
| Konzert Theater | 17.7m | ~32m | Bühnenturm fehlt |

### GKAT-Codes und erwartete Mindesthöhen

| GKAT | Bezeichnung | Min. Höhe |
|------|-------------|-----------|
| 1020 | Einfamilienhaus | 6m |
| 1030 | Mehrfamilienhaus | 9m |
| 1040 | Wohngebäude mit Nebennutzung | 9m |
| 1060 | Bildung/Kultur | 12m |
| 1080 | Gesundheit | 12m |
| 1110 | Kirchen | 15m |

---

## Zusammenfassung der Aufgaben

| # | Aufgabe | Datei | Priorität | Aufwand |
|---|---------|-------|-----------|---------|
| 1 | Einsteinhaus Zone korrigieren | known_buildings.py | P0 | 5 Min |
| 2 | Kunstmuseum Override hinzufügen | known_buildings.py | P0 | 10 Min |
| 3 | height_override Support implementieren | service.py | P1 | 30 Min |
| 4 | Höhen-Validierung hinzufügen | service.py | P1 | 30 Min |
| 5 | height_source Feld hinzufügen | building.py | P1 | 15 Min |
| 6 | CLAUDE.md aktualisieren | CLAUDE.md | P2 | 15 Min |
| 7 | Tests schreiben/erweitern | tests/ | P2 | 30 Min |

**Gesamtaufwand:** ~2-3 Stunden

---

## Kontakt bei Fragen

Bei Unklarheiten zur Projektstruktur:
1. Lies `CLAUDE.md` im Root des Projekts
2. Schau in `README.md` für die allgemeine Architektur
3. Die relevanten Dateien sind vermutlich in:
   - `app/services/smart_building/`
   - `app/models/`
   - `tests/`

---

*Dokument erstellt: 30. Dezember 2025*
*Basierend auf: Qualitätsanalyse der SVG-Pipeline*
