# Aktuelle Bugs und Fixes

> **Stand:** 30.12.2025
> **Branch:** `main` (Fixes auf main, dann Feature-Branch)

---

## Kritische Bugs (P0)

### BUG-001: Kunstmuseum Hoehendaten falsch ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P0 (Kritisch)
**Adresse:** Hodlerstrasse 8, 3011 Bern

**Problem:**
```
Erhalten:  7.9m First, 6.7m Traufe
Erwartet:  ~18m (Museumsgebaeude)
```

**Ursache:**
- swissBUILDINGS3D liefert falschen Wert (vermutlich Nebengebaeude)

**Loesung:**
- Kunstmuseum zu `known_buildings.py` hinzugefuegt mit korrekten Hoehenzonen:
  - Altbau: 15-18m
  - Neubau (Stettler): 12-15m
  - Erweiterung: 8-10m

---

## Hohe Prioritaet (P1)

### BUG-002: Unbekannte Gebaeude ohne Namen ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1

**Problem:**
- 6 von 10 Testgebaeuden haben `building_name = N/A`
- Claude-Recherche findet keine Namen

**Betroffene Gebaeude:**
- Hotel Schweizerhof (Bahnhofplatz 11) ✅
- Hauptbahnhof Bern (Bahnhofplatz 10) ✅
- Kornhaus (Kornhausplatz 18) ✅
- Stadttheater (Theaterplatz 7) ✅
- Kunstmuseum (Hodlerstrasse 8) ✅
- Historisches Museum (Helvetiaplatz 5) ✅

**Loesung:**
- Alle 6 Gebaeude zu `known_buildings.py` hinzugefuegt
- ADDRESS_TO_EGID Mappings ergaenzt
- Hoehenzonen definiert:
  - Kunstmuseum: 3 Zonen (Altbau, Neubau, Erweiterung)
  - Kornhaus: 3 Zonen (Arkaden, Hauptbau, Dachreiter)
  - Hauptbahnhof: 3 Zonen (Baldachin, Bahnhofshalle, Bueroturm)
  - Stadttheater: 3 Zonen (Foyer, Zuschauerhaus, Buehnenturm)
  - Historisches Museum: 3 Zonen (Hauptbau, Seitenfluegel, Eckturm)
  - Hotel Schweizerhof: 2 Zonen (Hauptgebaeude, Dachaufbau)

---

### BUG-003: Doppelte API-Calls ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1

**Problem (aus Log):**
```
INFO:httpx: GET .../SearchServer?searchText=Rathausgasse... (4x!)
INFO:httpx: GET .../height?easting=601009... (6x!)
```

**Ursache:**
- Parallele Requests ohne Koordination
- Fehlende Deduplizierung

**Loesung:**
- Request-Deduplizierung in `SmartBuildingService` implementiert:
  - `_address_locks: Dict[str, asyncio.Lock]` - Ein Lock pro Adresse
  - `_get_address_lock()` - Thread-safe Lock-Erstellung
  - Double-Check Pattern nach Lock-Erwerb
- Bei parallelen Anfragen fuer dieselbe Adresse:
  - Erste Anfrage sammelt Daten
  - Folgende Anfragen warten und erhalten Cache-Ergebnis
- Logging erweitert: "waited for other request"

---

### BUG-004: Einsteinhaus langsam (7.8s)

**Status:** Offen
**Prioritaet:** P1

**Problem:**
- Bekanntes Gebaeude, aber 7822ms Response-Zeit
- Andere bekannte Gebaeude: 329-816ms

**Ursache (vermutet):**
- Moeglicherweise Cache-Miss
- Oder On-Demand Hoehendaten-Fetch

**Loesung:**
1. Logging verbessern um Ursache zu identifizieren
2. Cache-Warmup fuer bekannte Gebaeude

---

### BUG-010: Dokumentation sagt "Haiku" aber Code verwendet Sonnet ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1
**Identifiziert durch:** Claude.ai Pipeline-Analyse (30.12.2025)

**Problem:**
- Dokumentation (CLAUDE.md, README.md, etc.) sagte "Claude Haiku fuer Recherche"
- Code verwendet ueberall `claude-sonnet-4-20250514`

**Loesung:**
- Dokumentation korrigiert: Sonnet ueberall
- Korrigierte Dateien:
  - CLAUDE.md (mehrere Stellen)
  - .claude/rules/smart-building.md
  - backend/app/main.py (Docstrings)
  - backend/app/services/claude_svg_zones.py
  - backend/app/services/prompts/research_service.py
  - docs/tests/README.md
- Kosten aktualisiert: ~$0.03-0.05 pro Recherche (statt ~$0.01-0.02)

---

### BUG-011: Hoehen-Validierung fehlt (Schritt 3/8) ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1
**Identifiziert durch:** Claude.ai Pipeline-Analyse (30.12.2025)

**Problem:**
- Keine Plausibilitaetspruefung bei Hoehendaten
- swissBUILDINGS3D kann falsche Werte liefern (z.B. Kunstmuseum 7.9m statt 18m)
- Fehler werden erst bei SVG-Generierung sichtbar

**Beispiele:**
```
Kunstmuseum:  API 7.9m, Real 18m (Nebengebaeude gemessen)
Einsteinhaus: Zone 16m, API 26m (Zone war falsch definiert)
```

**Loesung:**
```python
# In SmartBuildingService, nach Schritt 3 (Hoehendaten)
def _validate_heights(self, bundle: BuildingDataBundle) -> List[str]:
    warnings = []

    # 1. Minimalhoehe nach GKAT
    min_heights = {1020: 6, 1030: 9, 1060: 12, 1110: 15}
    min_h = min_heights.get(bundle.gkat, 6)
    if bundle.firsthoehe_m and bundle.firsthoehe_m < min_h:
        warnings.append(f"Firsthoehe {bundle.firsthoehe_m}m unplausibel fuer GKAT {bundle.gkat}")

    # 2. Geschoss-Plausibilitaet
    if bundle.geschosse and bundle.firsthoehe_m:
        expected_min = bundle.geschosse * 2.5
        expected_max = bundle.geschosse * 4.0
        if not (expected_min <= bundle.firsthoehe_m <= expected_max):
            warnings.append(f"Hoehe {bundle.firsthoehe_m}m passt nicht zu {bundle.geschosse} Geschossen")

    return warnings
```

---

### BUG-012: Zone/API-Konsistenz Warnung fehlt ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1
**Identifiziert durch:** Claude.ai Datenqualitaets-Analyse (30.12.2025)

**Problem:**
- Bei 5 von 10 Testgebaeuden ist max. Zonenhoehe > API-Firsthoehe
- Keine Warnung wenn Zone-Daten inkonsistent mit API-Daten
- Kann zu falschen SVG-Darstellungen fuehren

**Beispiele:**
```
Bundeshaus:        Zone 64m > First 62.6m (OK - Kuppel)
Hotel Schweizerhof: Zone 30m > First 27.2m (OK - Dachaufbau)
Einsteinhaus:      Zone 16m < Traufe 22.3m (FEHLER - war falsch!)
```

**Loesung:**
```python
# In SmartBuildingService, nach Schritt 8 (Zonen-Analyse)
def _validate_zone_consistency(self, bundle: BuildingDataBundle) -> List[str]:
    warnings = []

    for zone in bundle.zones:
        # Zone unter Traufhoehe = definitiv falsch
        if zone.firsthoehe_m < bundle.traufhoehe_m:
            warnings.append(
                f"Zone '{zone.name}' ({zone.firsthoehe_m}m) unter Traufhoehe ({bundle.traufhoehe_m}m)!"
            )

        # Zone deutlich ueber First = moeglich (Turm), aber warnen
        if zone.firsthoehe_m > bundle.firsthoehe_m * 1.5:
            warnings.append(
                f"Zone '{zone.name}' ({zone.firsthoehe_m}m) deutlich ueber API-First ({bundle.firsthoehe_m}m)"
            )

    return warnings
```

---

### BUG-009: Einsteinhaus Zone-Hoehe falsch ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1
**Identifiziert durch:** Claude.ai Datenqualitaets-Analyse

**Problem:**
```
API-Hoehen:   Traufe 22.3m, First 26.2m
Zone (ALT):   12.0m - 16.0m (FALSCH!)
```

**Ursache:**
- Manuell definierte Zone in known_buildings.py war falsch
- Zone war niedriger als API-Traufhoehe

**Loesung:**
- Zone korrigiert auf 22.0m - 26.0m (passend zu API)
- Kommentar hinzugefuegt zur Dokumentation

---

## Mittlere Prioritaet (P2)

### BUG-005: Stadttheater Hoehen + Dachform ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P2

**Problem 1 (Hoehen):**
```
Erhalten:  15-17m
Erwartet:  ~25m (Theater mit Buehnenturm)
```

**Problem 2 (Dachform - P2 aus Claude.ai Analyse):**
```
roof_type: "kuppel" (falsch)
Erwartet:  "walmdach"
```

**Loesung:**
- Stadttheater zu `known_buildings.py` hinzugefuegt (BUG-002)
- Korrekte Zonen: Foyer 12m, Zuschauerhaus 22m, Buehnenturm 32m
- roof_type korrigiert: "walmdach" (Commit c219246)

---

### BUG-006: Nur 1-2 Zonen bei komplexen Gebaeuden

**Status:** Offen
**Prioritaet:** P2

**Problem:**
- Unbekannte komplexe Gebaeude erhalten nur 1-2 Zonen
- Sollten 3-4 Zonen haben

**Betroffene Gebaeude:**
- Hauptbahnhof: 1 Zone (sollte 3+)
- Historisches Museum: 1 Zone (sollte 3+)

**Loesung:**
- Claude-Analyse verbessern
- Oder: zu `known_buildings.py` hinzufuegen

---

### FEATURE-001: Grundrissform-Erkennung (U/L/H-Form)

**Status:** Geplant
**Prioritaet:** P2
**Identifiziert durch:** Claude.ai Pipeline-Analyse (30.12.2025)

**Problem:**
- SVG-Prompts enthalten keine Grundrissform
- Bundeshaus: U-Form mit Ehrenhof fehlt im Prompt
- Claude muss Form aus Polygon-Koordinaten erraten

**Auswirkung:**
- Grundriss-SVGs zeigen nicht korrekt U-Form, Ehrenhof, etc.
- Qualitaet der SVGs bei komplexen Gebaeuden eingeschraenkt

**Loesung:**
```python
# In SmartBuildingService oder neuer polygon_analyzer.py
def analyze_polygon_shape(polygon: List[Tuple[float, float]]) -> Dict:
    """Analysiert Polygon-Form fuer SVG-Generierung."""

    # 1. Konvexitaet pruefen
    hull = compute_convex_hull(polygon)
    convexity_ratio = polygon_area(polygon) / polygon_area(hull)

    # 2. Form-Erkennung
    if convexity_ratio > 0.95:
        shape = "rechteckig"
    elif convexity_ratio > 0.7:
        shape = detect_u_l_h_form(polygon, hull)
    else:
        shape = "komplex"

    # 3. Ehrenhof-Erkennung
    courtyard = detect_courtyard(polygon)

    return {
        "building_shape": shape,
        "convexity_ratio": convexity_ratio,
        "has_courtyard": courtyard is not None,
        "courtyard_position": courtyard,
    }
```

**Bezug zu ML-Roadmap:**
- Polygon-Form ist guter Praediktor fuer Gebaeudetyp
- Kann als Feature fuer ML-Modell verwendet werden

---

## Niedrige Prioritaet (P3)

### BUG-007: Encoding teilweise inkonsistent

**Status:** Beobachten
**Prioritaet:** P3

**Problem:**
- UTF-8 in manchen Logs kaputt
- ASCII-Ersetzungen nicht ueberall konsistent

**Loesung:**
- Encoding in allen Services vereinheitlichen
- ASCII-only fuer Prompts (bereits implementiert)

---

## Gefixt (Erledigt)

### BUG-001: Kunstmuseum Hoehendaten ✅

**Status:** Gefixt (30.12.2025)

**Loesung:**
- Kunstmuseum zu `known_buildings.py` hinzugefuegt
- Korrekte Hoehenzonen: Altbau 18m, Neubau 15m, Erweiterung 10m

---

### BUG-002: 6 Berner Gebaeude ✅

**Status:** Gefixt (30.12.2025)

**Loesung:**
- Alle 6 Gebaeude mit korrekten Zonen hinzugefuegt
- ADDRESS_TO_EGID Mappings ergaenzt

---

### BUG-003: Doppelte API-Calls ✅

**Status:** Gefixt (30.12.2025)

**Loesung:**
- Request-Deduplizierung mit asyncio.Lock pro Adresse
- Double-Check Pattern nach Lock-Erwerb

---

### BUG-005: Stadttheater Dachform ✅

**Status:** Gefixt (30.12.2025)
**Commit:** c219246

**Problem:**
- roof_type war "kuppel" (falsch)
- Identifiziert in Claude.ai Batch-Test Analyse

**Loesung:**
- roof_type auf "walmdach" korrigiert
- Stadttheater wurde mit BUG-002 bereits hinzugefuegt

---

### BUG-008: ConnectTimeout ohne Retry ✅

**Status:** Gefixt (30.12.2025)
**Commit:** 316bd35

**Problem:**
- swisstopo/geodienste.ch Timeout fuehrte zu 500 Error
- Keine Retry-Logik

**Loesung:**
- 3x Retry mit exponential backoff
- Timeout erhoeht auf 30s
- Logging fuer Retry-Versuche

---

## Bug-Fix Workflow

```bash
# 1. Bug auf main fixen (kleine Fixes)
git checkout main
# ... fix ...
git commit -m "fix: BUG-001 Kunstmuseum Hoehendaten"
git push

# 2. Groessere Features auf Branch
git checkout -b feature/ml-learning-system
# ... implement ...
git push -u origin feature/ml-learning-system
# PR erstellen
```

---

## Priorisierte Reihenfolge

### P1 (Kritisch - als naechstes fixen)
1. **BUG-004** - Einsteinhaus langsam (Performance)

### P2 (Wichtig - nach P1)
2. **BUG-006** - Zonen bei Unbekannten (UX)
3. **FEATURE-001** - Grundrissform-Erkennung (U/L/H)

### P3 (Kosmetik)
4. **BUG-007** - Encoding (Kosmetik)

### Erledigt ✅
- ~~**BUG-001** - Kunstmuseum Hoehen~~ ✅
- ~~**BUG-002** - 6 Gebaeude zu known_buildings.py~~ ✅
- ~~**BUG-003** - Doppelte API-Calls~~ ✅
- ~~**BUG-005** - Stadttheater Hoehen + Dachform~~ ✅
- ~~**BUG-008** - ConnectTimeout ohne Retry~~ ✅
- ~~**BUG-009** - Einsteinhaus Zone-Hoehe~~ ✅
- ~~**BUG-010** - Dokumentation Haiku→Sonnet~~ ✅
- ~~**BUG-011** - Hoehen-Validierung~~ ✅
- ~~**BUG-012** - Zone/API-Konsistenz Warnung~~ ✅

---

*Dokument erstellt: 30.12.2025*
*Letzte Aktualisierung: 30.12.2025 - Claude.ai Pipeline-Analyse Bugs hinzugefuegt*
