# Pipeline-Analyse: SmartBuildingService

> **Datum:** 30.12.2025
> **Ziel:** Jeden Schritt der Datensammlung analysieren und optimieren
> **Basierend auf:** svg_datenqualitaet_vergleich.md (Claude.ai Analyse)

---

## Uebersicht: 10-Schritte Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                 SMARTBUILDINGSERVICE PIPELINE               │
├─────────────────────────────────────────────────────────────┤
│  1. Geocoding          → Adresse → Koordinaten + EGID       │
│  2. GWR-Daten          → EGID → Geschosse, Kategorie        │
│  3. Hoehendaten        → EGID/Koord → Trauf/First-Hoehe     │
│  4. Terrain            → Koordinaten → m ue.M.              │
│  5. Polygon            → EGID → Grundriss-Form              │
│  6. Dach-Analyse       → Hoehen → Dachform, Neigung         │
│  7. Recherche          → known_buildings ODER Claude Haiku  │
│  8. Zonen-Analyse      → Claude Sonnet (bei COMPLEX)        │
│  9. SUVA Zugaenge      → Polygon → Zugangspunkte            │
│ 10. Qualitaetsbewertung→ Alle Daten → Score                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Schritt 1: Geocoding (swisstopo API)

### API-Aufruf

```
GET https://api3.geo.admin.ch/rest/services/api/SearchServer
    ?searchText=Bundesplatz 3, 3011 Bern
    &type=locations
    &origins=address
```

### Response (Beispiel)

```json
{
  "results": [{
    "attrs": {
      "label": "Bundesplatz 3 <b>3011 Bern</b>",
      "x": 600423,
      "y": 199521,
      "featureId": "2242547_0"
    }
  }]
}
```

### Extrahierte Daten

| Feld | Wert | Verwendung |
|------|------|------------|
| x (LV95 E) | 600423 | Koordinaten fuer Terrain, Polygon |
| y (LV95 N) | 199521 | Koordinaten fuer Terrain, Polygon |
| featureId | 2242547 | EGID fuer GWR, Hoehen |

### Bekannte Probleme

- Keine bekannten Probleme
- Erfolgsrate: 100%

---

## Schritt 2: GWR-Daten (swisstopo API)

### API-Aufruf

```
GET https://api3.geo.admin.ch/rest/services/api/MapServer/find
    ?layer=ch.bfs.gebaeude_wohnungs_register
    &searchText=2242547
    &searchField=egid
```

### Response (Beispiel)

```json
{
  "results": [{
    "attributes": {
      "egid": 2242547,
      "strname": "Bundesplatz",
      "deinr": "3",
      "dplz4": 3011,
      "ggdename": "Bern",
      "gkat": 1060,
      "gbauj": 1902,
      "gastw": 4,
      "garea": 3697
    }
  }]
}
```

### Extrahierte Daten

| Feld | Wert | Verwendung |
|------|------|------------|
| gkat | 1060 (Kultur/Bildung) | Komplexitaets-Erkennung |
| gbauj | 1902 | Baustil-Hinweis |
| gastw | 4 | Geschoss-Schaetzung |
| garea | 3697 m² | Groesse |

### GKAT-Codes und Komplexitaet

| Code | Bezeichnung | Komplexitaet |
|------|-------------|--------------|
| 1020 | Einfamilienhaus | SIMPLE |
| 1030 | Mehrfamilienhaus | SIMPLE |
| 1040 | Wohngebaeude mit Nebennutzung | MODERATE |
| 1060 | Bildung/Kultur | COMPLEX |
| 1080 | Gesundheit | COMPLEX |
| 1110 | Kirchen | COMPLEX |

### Bekannte Probleme

- Keine Geschossdaten (gastw) fuer manche Gebaeude
- GKAT nicht immer korrekt (Bundeshaus = 1060 statt spezieller Code)

---

## Schritt 3: Hoehendaten (swissBUILDINGS3D)

### Lookup-Strategie

```
1. EGID-Lookup in building_heights_detailed
2. Falls nicht gefunden: EGID-Lookup in building_heights (Legacy)
3. Falls nicht gefunden: Koordinaten-Lookup (±50m)
4. Falls nicht gefunden: On-Demand STAC API Fetch
5. Falls nicht gefunden: Schaetzung aus GWR (Geschosse × 3.2m)
```

### Datenbank-Abfrage (Beispiel)

```sql
SELECT traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
FROM building_heights_detailed
WHERE egid = '2242547'
```

### Ergebnis (Beispiel)

| Gebaeude | traufhoehe_m | firsthoehe_m | gebaeudehoehe_m |
|----------|--------------|--------------|-----------------|
| Bundeshaus | 53.2 | 62.6 | 62.6 |
| Einsteinhaus | 22.3 | 26.2 | 26.2 |
| Kunstmuseum | 6.7 | 7.9 | 7.9 |

### KRITISCHE PROBLEME (aus Claude.ai Analyse)

**Problem 1: Einsteinhaus**
```
API:   Traufe 22.3m, First 26.2m
Zone:  12.0m - 16.0m (FALSCH!)
```
→ Zone ist niedriger als API - manueller Fehler in known_buildings.py

**Problem 2: Kunstmuseum**
```
API:   Traufe 6.7m, First 7.9m (FALSCH!)
Zone:  Altbau 15-18m, Neubau 12-15m (KORREKT)
```
→ API misst falsches Gebaeude/Teil - swissBUILDINGS3D Problem

**Problem 3: Inkonsistenz Zone > API-First**
Bei 5 von 10 Gebaeuden ist die maximale Zonenhoehenicht HOEHER als der API-First:
- Bundeshaus: Zone 64m > First 62.6m
- Hotel Schweizerhof: Zone 30m > First 27.2m
- Hauptbahnhof: Zone 40m > First 36.8m

### Empfehlung

1. **Hoehen-Validierung einfuehren:**
   - Wenn Zone > API-First × 1.5 → Warnung
   - Wenn Zone < API-Traufe → Fehler

2. **known_buildings.py als Override:**
   - Manuell definierte Hoehen haben Vorrang
   - API-Hoehen nur als Fallback

---

## Schritt 4: Terrain (swissALTI3D API)

### API-Aufruf

```
GET https://api3.geo.admin.ch/rest/services/height
    ?easting=600423
    &northing=199521
    &sr=2056
```

### Response

```json
{"height": "543.1"}
```

### Verwendung

- Referenzpunkt fuer SVG: +/-0.00 = 543.1 m ue.M.
- Hanglage-Erkennung (bei Terrain-Differenz > 1m)

### Bekannte Probleme

- Keine bekannten Probleme
- Sehr zuverlaessig

---

## Schritt 5: Polygon (geodienste.ch WFS)

### API-Aufruf

```
GET https://geodienste.ch/db/av/deu
    ?SERVICE=WFS
    &VERSION=2.0.0
    &REQUEST=GetFeature
    &TYPENAMES=ms:bodenbedeckung
    &SRSNAME=EPSG:2056
    &BBOX=600373,199471,600473,199571
    &OUTPUTFORMAT=application/json
```

### Response (vereinfacht)

```json
{
  "features": [{
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[600423, 199521], [600450, 199521], ...]]
    },
    "properties": {
      "art": "Gebaeude"
    }
  }]
}
```

### Extrahierte Daten

| Feld | Wert | Verwendung |
|------|------|------------|
| Polygon | 26 Punkte | Grundriss-Form |
| Bounding Box | 80.2m × 71.0m | Vereinfachte Darstellung |
| Umfang | 310.0 m | Fassadenlaengen |

### Bekannte Probleme

- Komplexe Polygone (>20 Punkte) werden vereinfacht
- Keine explizite U-Form/L-Form Erkennung

### Empfehlung: Polygon-Form-Analyse

```python
# Pseudo-Code fuer Form-Erkennung
def detect_building_shape(polygon):
    convex_hull = compute_convex_hull(polygon)
    concavity_ratio = polygon_area / convex_hull_area

    if concavity_ratio > 0.95:
        return "rechteckig"
    elif concavity_ratio > 0.8:
        return "L-Form oder T-Form"
    else:
        return "U-Form oder komplex"
```

---

## Schritt 6: Dach-Analyse (berechnet)

### Berechnung

```python
# In app/services/roof.py
neigung_grad = arctan((firsthoehe - traufhoehe) / (gebaeudetiefe / 2)) × (180/π)
```

### Dachformen

| Neigung | Dachform |
|---------|----------|
| < 5° | Flachdach |
| 5-15° | Pultdach |
| 15-45° | Satteldach |
| 15-45° (quadratisch) | Walmdach |
| > 60° | Mansarddach |

### Probleme

- Bei Kuppeln (Bundeshaus): Dachform = "kuppel" wird erkannt
- Bei komplexen Daechern: Konfidenz niedrig

---

## Schritt 7: Recherche (known_buildings ODER Claude Haiku)

### Variante A: known_buildings.py (kostenlos, sofort)

```python
# In app/services/smart_building/known_buildings.py

KNOWN_BUILDINGS = {
    "2242547": {  # Bundeshaus
        "egid": "2242547",
        "building_name": "Bundeshaus",
        "building_type": "Parlamentsgebaeude",
        "architectural_style": "Neorenaissance / Historismus",
        "construction_year": 1902,
        "building_shape": "U-Form mit Ehrenhof",
        "building_shape_description": "Das Gebäude hat eine U-Form...",
        "special_features": ["Kuppel", "Arkaden", "Ehrenhof", "Skulpturen"],
        "svg_hints": {
            "grundriss": "U-Form zeichnen! Ehrenhof in der Mitte...",
            "ansicht": "Kuppel zentral, Arkaden im Erdgeschoss...",
            "schnitt": "Zeige alle 3 Hoehenzonen..."
        },
        "zones": [
            {"name": "Arkaden", "type": "arkade", "traufe": 6.0, "first": 6.0},
            {"name": "Hauptgebaeude", "type": "hauptgebaeude", "traufe": 25.0, "first": 30.0},
            {"name": "Kuppel", "type": "kuppel", "traufe": 30.0, "first": 64.0}
        ]
    }
}
```

### Variante B: Claude Haiku Recherche (~$0.01-0.02)

**Prompt:**

```
Recherchiere das Gebaeude an folgender Adresse:
- Adresse: Marktgasse 10, 3011 Bern
- EGID: 12345
- GWR-Kategorie: 1030 (Mehrfamilienhaus)
- Baujahr: 1890

Bestimme:
1. Gebaeudenname (falls bekannt)
2. Gebaeudetyp
3. Baustil
4. Besondere architektonische Merkmale
5. Turm-Konfiguration (falls vorhanden)

Antworte im JSON-Format.
```

**Response:**

```json
{
  "building_name": null,
  "building_type": "Wohnhaus",
  "architectural_style": "Gruenderzeit",
  "special_features": [],
  "tower_config": null
}
```

### Priorisierung

1. **Bekannte Gebaeude** (known_buildings.py) → Sofort, kostenlos
2. **Kirchen** (GKAT 1110) → Spezielle Kirchen-Zonen
3. **Claude Haiku** → Nur wenn unbekannt und GKAT != 1020/1030

---

## Schritt 8: Zonen-Analyse (Claude Sonnet bei COMPLEX)

### Wann wird Claude Sonnet aufgerufen?

```python
# In app/services/smart_building/service.py
def _needs_zones_analysis(bundle) -> bool:
    # Extreme Hoehendifferenz
    if bundle.firsthoehe_m - bundle.traufhoehe_m > 15:
        return True
    # Komplexe GWR-Kategorie
    if bundle.gkat in [1040, 1060, 1080, 1110, 1130]:
        return True
    # Grosses Gebaeude
    if bundle.area_m2 > 1000:
        return True
    # Komplexes Polygon
    if len(bundle.polygon) > 12:
        return True
    return False
```

### Claude Sonnet Prompt (~$0.05-0.15)

```
Analysiere die Hoehenzonen fuer das folgende Gebaeude:

Gebaeude: Bundeshaus
Typ: Parlamentsgebaeude
Baustil: Neorenaissance / Historismus
Traufhoehe (API): 53.2m
Firsthoehe (API): 62.6m
Grundflaeche: 3697 m²

Bestimme die architektonischen Zonen mit ihren Hoehen.
Typische Zonen: hauptgebaeude, arkade, kuppel, turm, anbau

Antworte im JSON-Format:
{
  "zones": [
    {"name": "...", "type": "...", "traufe": X.X, "first": Y.Y, "sonderkonstruktion": bool}
  ],
  "complexity": "simple|moderate|complex"
}
```

### Probleme bei Claude Sonnet

1. **Keine Validierung gegen API-Hoehen**
   - Claude kann Zonen-Hoehen erfinden
   - Empfehlung: Validierung einfuehren

2. **Inkonsistenz bei wiederholten Aufrufen**
   - Gleiches Gebaeude → unterschiedliche Zonen
   - Empfehlung: Cache verwenden (24h TTL)

---

## Schritt 9: SUVA Zugaenge (berechnet)

### Algorithmus

```python
# In app/services/smart_building/service.py
def _calculate_access_points(polygon, perimeter_m):
    """SUVA: Max. 50m Fluchtweg"""
    max_distance = 50.0
    access_points = []

    # Ecken erhalten immer Zugang
    for corner in get_corners(polygon):
        access_points.append(corner)

    # Zusaetzliche Zugaenge alle 50m
    current_distance = 0
    for edge in polygon_edges(polygon):
        while current_distance + edge.length > max_distance:
            # Zugang einfuegen
            ...
```

### Ausgabe

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | N | 93% | Ecke (Ende) |
| Z2 | N | 7% | Ecke (Start) |
| Z3 | O | 42% | Automatisch verteilt |

### Bekannte Probleme

- SUVA-Warnung bei Bundeshaus (77.8m > 50m) trotz 7 Zugaengen
- Ursache: Komplexes Polygon, Berechnung nicht optimal

---

## Schritt 10: Qualitaetsbewertung (berechnet)

### Scoring

```python
def calculate_quality_score(bundle):
    score = 0

    # Hoehendaten
    if bundle.height_source == "swissBUILDINGS3D":
        score += 30
    elif bundle.height_source == "estimated":
        score += 10

    # Polygon
    if bundle.polygon:
        score += 20

    # Recherche
    if bundle.building_name:
        score += 20

    # Zonen
    if len(bundle.zones) >= 2:
        score += 30

    return score  # Max 100
```

### Kategorien

| Score | Qualitaet | Bedeutung |
|-------|-----------|-----------|
| 80-100 | HIGH | Alle Daten vorhanden |
| 50-79 | MEDIUM | Teilweise geschaetzt |
| 0-49 | LOW | Viele Daten fehlen |

---

## Zusammenfassung: Wo sind die Probleme?

### Kritische Probleme (P0)

| Schritt | Problem | Impact |
|---------|---------|--------|
| 3. Hoehendaten | Kunstmuseum: API = 7.9m, Real = 18m | SVG falsch |
| 7. Recherche | Einsteinhaus: Zone 16m < API 22m | SVG falsch |

### Mittlere Probleme (P1)

| Schritt | Problem | Impact |
|---------|---------|--------|
| 5. Polygon | Keine U-Form/L-Form Erkennung | Grundriss rechteckig |
| 8. Zonen | Keine Validierung gegen API | Inkonsistente Hoehen |

### Niedrige Probleme (P2)

| Schritt | Problem | Impact |
|---------|---------|--------|
| 9. SUVA | Warnung bei komplexen Polygonen | Kosmetisch |
| 6. Dach | Konfidenz niedrig bei Kuppeln | Minimal |

---

## Naechste Schritte

1. **Einsteinhaus Zone korrigieren** (5 Min)
2. **Kunstmuseum: Manuellen Override** (5 Min)
3. **Hoehen-Validierung implementieren** (2 Std)
4. **Polygon-Form-Analyse** (4 Std)

---

*Generiert: 30.12.2025*
*Basierend auf: svg_datenqualitaet_vergleich.md*
