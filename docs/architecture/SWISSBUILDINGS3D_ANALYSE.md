# swissBUILDINGS3D 3.0 Analyse

> **Datum:** 11.01.2026
> **Status:** In Bearbeitung
> **Ziel:** Vollständige Nutzung aller verfügbaren 3D-Gebäudedaten

## Übersicht

swissBUILDINGS3D 3.0 Beta liefert 3D-Gebäudemodelle mit Dachgeometrien für die Schweiz.
Ein Gebäude besteht aus **5 Layern** die zusammen ein komplettes 3D-Modell ergeben.

**Quellen:**
- [swisstopo Produktseite](https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta)
- [opendata.swiss](https://opendata.swiss/en/dataset/swissbuildings3d-3-0-beta)

## Layer-Struktur

```
┌─────────────────────────────────────────────────────────────┐
│                   GEBÄUDE 3D-MODELL                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Roof_solid (Dach-Körper)               │   │
│  │  Z: DACH_MIN - DACH_MAX                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↑                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Roof (Dach-Fläche)                   │   │
│  │  Z: DACH_MIN (Traufhöhe, flach)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↑                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Wall (Wand-Flächen)                    │   │
│  │  Z: GELAENDEPUNKT - DACH_MIN                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↑                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Floor (Grundfläche)                   │   │
│  │  Z: GELAENDEPUNKT (flach)                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Building_solid = Komplettes Gebäude (alle Z-Werte)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Layer-Details

### 1. Floor (Grundfläche)

| Eigenschaft | Wert |
|-------------|------|
| Geometrie | MultiPolygon (2.5D) |
| Z-Koordinaten | Konstant auf GELAENDEPUNKT |
| Verwendung | Gebäude-Grundriss, Fassaden-Berechnung |

**Attribute:**
| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| EGID | int32 | Eidg. Gebäudeidentifikator |
| GELAENDEPUNKT | float | Terrainhöhe (m ü.M.) |
| GESAMTHOEHE | float | Gebäudehöhe (m) |
| OBJEKTART | str | Gebäudetyp |
| GEBAEUDE_NUTZUNG | str | Nutzungsart |
| NAME_KOMPLETT | str | Gebäudename |
| GEBAEUDEEINHEIT | uuid | Verknüpfung zu anderen Layern |

#### Floor vs. Building_solid Vergleich (11.01.2026)

**Analyse:** 5057 Gebäude aus Tile 1166-24 verglichen (Centroid-Matching)

| Metrik | Wert | Bedeutung |
|--------|------|-----------|
| **Median Unterschied** | +0.02% | Praktisch identisch! |
| **Durchschnitt** | -0.39% | Leicht kleiner |
| **Innerhalb ±5%** | 26% | - |
| **Innerhalb ±10%** | 34% | - |
| **Building > Floor** | 33% | Dachüberstand messbar |
| **Building < Floor** | 41% | Matching-Fehler/Komplexe Gebäude |

**Erkenntnis:** Der Floor-Layer und das Building_solid Polygon sind für die meisten Gebäude **praktisch identisch**. Der Unterschied (Dachüberstand) ist meist <5% und für Gerüstplanung vernachlässigbar.

**Empfehlung:** Floor-Layer NICHT separat importieren. Building_solid Polygon reicht für Grundriss.

### 2. Wall (Wand-Flächen)

| Eigenschaft | Wert |
|-------------|------|
| Geometrie | MultiPolygon (3D) |
| Z-Koordinaten | GELAENDEPUNKT bis DACH_MIN |
| Verwendung | Fassaden-Geometrie, Gerüst-Planung |

**Attribute:** Identisch zu Floor

### 3. Roof (Dach-Umriss)

| Eigenschaft | Wert |
|-------------|------|
| Geometrie | MultiPolygon (2.5D) |
| Z-Koordinaten | Konstant auf DACH_MIN (Traufhöhe) |
| Verwendung | Dach-Grundriss auf Traufhöhe |

**Attribute:**
| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| EGID | int32 | Eidg. Gebäudeidentifikator |
| DACH_MAX | float | Firsthöhe (m ü.M.) |
| DACH_MIN | float | Traufhöhe (m ü.M.) |
| OBJEKTART | str | Gebäudetyp |
| GEBAEUDEEINHEIT | uuid | Verknüpfung |

### 4. Roof_solid (Dach-Körper)

| Eigenschaft | Wert |
|-------------|------|
| Geometrie | MultiPolygon (3D) |
| Z-Koordinaten | DACH_MIN bis DACH_MAX |
| Verwendung | 3D-Dachform |

**Attribute:** Identisch zu Roof

### 5. Building_solid (Gesamtgebäude)

| Eigenschaft | Wert |
|-------------|------|
| Geometrie | MultiPolygon (3D) |
| Z-Koordinaten | GELAENDEPUNKT bis DACH_MAX |
| Verwendung | Komplettes 3D-Modell |

**Alle Attribute:**
| Attribut | Typ | Beschreibung | Aktuell genutzt |
|----------|-----|--------------|-----------------|
| UUID | uuid | Eindeutige Feature-ID | ❌ |
| EGID | int32 | Eidg. Gebäudeidentifikator | ✅ |
| OBJEKTART | str | Gebäudetyp (siehe unten) | ❌ NEU |
| NAME_KOMPLETT | str | Offizieller Gebäudename | ❌ NEU |
| GEBAEUDE_NUTZUNG | str | Nutzungsart | ❌ NEU |
| GEBAEUDEEINHEIT | uuid | Verknüpft Floor/Wall/Roof | ❌ NEU |
| DACH_MAX | float | Firsthöhe absolut (m ü.M.) | ✅ |
| DACH_MIN | float | Traufhöhe absolut (m ü.M.) | ✅ |
| GELAENDEPUNKT | float | Terrainhöhe (m ü.M.) | ✅ |
| GESAMTHOEHE | float | Gebäudehöhe (m) | ✅ |
| HERKUNFT | str | Datenquelle | ❌ |
| HERKUNFT_JAHR | int | Erfassungsjahr | ❌ |
| HERKUNFT_MONAT | int | Erfassungsmonat | ❌ |
| ORIGINAL_HERKUNFT | str | Ursprüngliche Quelle | ❌ |
| ERSTELLUNG_JAHR | int | Jahr der Erstellung | ❌ |
| REVISION_JAHR | int | Jahr der Revision | ❌ |
| DATUM_ERSTELLUNG | datetime | Erstellungsdatum | ❌ |
| DATUM_AENDERUNG | datetime | Änderungsdatum | ❌ |
| GRUND_AENDERUNG | str | Änderungsgrund | ❌ |

## OBJEKTART Werte

> **Hinweis:** Die automatische Zuweisung von OBJEKTART aus swissBUILDINGS3D 2.0
> ist noch fehlerhaft. In Kantonen mit EGID-Integration sind die Werte korrekt.

### Gefundene Werte (aus Tile-Analyse Bern, 11.01.2026)

| OBJEKTART | Anzahl | Komplexität |
|-----------|--------|-------------|
| Gebaeude Einzelhaus | 27'663 | SIMPLE |
| Hochhaus | 299 | MODERATE |
| Mauer gross | 200 | - |
| Sakrales Gebaeude | 74 | COMPLEX |
| Lagertank | 57 | - |
| Im Bau | 52 | - |
| Treibhaus | 33 | SIMPLE |
| Mauer gross gedeckt | 20 | - |
| Flugdach | 12 | - |
| Sakraler Turm | 12 | COMPLEX |
| Hochkamin | 7 | - |
| Unterirdisches Gebaeude | 3 | - |
| Kapelle | 2 | COMPLEX |
| Gebaeude unsichtbar | 1 | - |
| Verbindungsbruecke | 1 | - |

### GEBAEUDE_NUTZUNG Werte (gefunden)

| Wert | Beschreibung |
|------|--------------|
| Aussichtsturm | Turm |
| Gasthof abgelegen | Gastronomie |
| Parkhaus | Verkehr |
| Reservoir | Infrastruktur |
| Schiessstand | Sport |
| Stadion | Sport |

### NAME_KOMPLETT Beispiele (gefunden)

| Name | EGID | Tile |
|------|------|------|
| Berner Münster | 1230337 | 1332-21 |
| Sporthallen Weissenstein | 191862301 | 1332-21 |
| Sportplatz Liebefeld Hessgut | 502111174 | 1332-21 |
| Sportplatz Bodenweid | 2243147 | 1322-21 |

## Koordinatensystem

| Parameter | Wert |
|-----------|------|
| CRS | EPSG:2056 (LV95) |
| Z-Werte | Meter über Meer (m ü.M.) |
| Genauigkeit | ±0.5m (LiDAR-basiert) |

## Verknüpfung der Layer

Die **GEBAEUDEEINHEIT** (UUID) verbindet alle Layer eines Gebäudes:

```
Floor         ──┐
Wall          ──┼── GEBAEUDEEINHEIT = {ABC-123-...}
Roof          ──┤
Roof_solid    ──┤
Building_solid──┘
```

### UUID vs. GEBAEUDEEINHEIT

| Attribut | Zweck | Scope |
|----------|-------|-------|
| **UUID** | Feature-ID | Einzigartig pro Zeile (Layer-Feature) |
| **GEBAEUDEEINHEIT** | Gebäude-Verknüpfung | Identisch über alle 5 Layer |

**Beispiel Bundeshaus:**
```
Layer           UUID (unterschiedlich)    GEBAEUDEEINHEIT (gleich)
───────────────────────────────────────────────────────────────────
Floor           abc-111-...               xyz-999-...
Wall            abc-222-...               xyz-999-...
Roof            abc-333-...               xyz-999-...
Roof_solid      abc-444-...               xyz-999-...
Building_solid  abc-555-...               xyz-999-...
```

### Anwendungsfälle GEBAEUDEEINHEIT

#### 1. 3D-Visualisierung
Alle Layer mit gleicher GEBAEUDEEINHEIT zusammen rendern:
```
SELECT * FROM Floor WHERE gebaeudeeinheit = 'xyz-999-...'
UNION ALL
SELECT * FROM Wall WHERE gebaeudeeinheit = 'xyz-999-...'
UNION ALL
SELECT * FROM Roof_solid WHERE gebaeudeeinheit = 'xyz-999-...'
```
→ Ergibt komplettes 3D-Modell eines Gebäudes

#### 2. Reihenhäuser (mehrere EGIDs, eine Struktur)
```
┌─────────────────────────────────────────────────────────────┐
│  EGID 1234567  │  EGID 1234568  │  EGID 1234569           │
│  (Haus A)      │  (Haus B)      │  (Haus C)               │
├─────────────────────────────────────────────────────────────┤
│              GEBAEUDEEINHEIT = xyz-999-...                  │
│              (gemeinsames Dach, durchgehende Wände)         │
└─────────────────────────────────────────────────────────────┘
```
→ Drei Wohneinheiten teilen sich ein physisches Gebäude

#### 3. Anbauten und Erweiterungen
```
┌──────────────────┐
│ Hauptgebäude     │──── EGID 1111111
│ GEBAEUDEEINHEIT  │     GEBAEUDEEINHEIT = aaa-...
│ = aaa-...        │
├──────────────────┤
│ Anbau            │──── EGID 2222222
│ GEBAEUDEEINHEIT  │     GEBAEUDEEINHEIT = aaa-... (GLEICH!)
│ = aaa-...        │
└──────────────────┘
```
→ Anbau gehört zur gleichen physischen Gebäudestruktur

#### 4. Innenhof-Gebäude (U-Form, Karree)
```
┌─────────────────────────────────────┐
│                 EGID 3333333        │
│  ┌───────────────────────────────┐  │
│  │         INNENHOF             │  │  ALLE mit gleicher
│  │    (keine GEBAEUDEEINHEIT)   │  │  GEBAEUDEEINHEIT
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```
→ Zusammenhängendes Gebäude trotz komplexer Form

### Praktische Nutzung

**Für Gerüstplanung:**
- Bei gleicher GEBAEUDEEINHEIT: Gebäudeteile können zusammen eingerüstet werden
- Bei verschiedener GEBAEUDEEINHEIT: Separate Gerüstbereiche nötig
- Innenhöfe: NICHT einrüsten (keine GEBAEUDEEINHEIT in der Mitte)

**Für 3D-Viewer:**
- Komplettes Gebäude aus allen Layern rendern
- Farbcodierung nach Layer möglich (Floor grau, Wall beige, Roof rot)

## HERKUNFT-Attribute

Metadaten zur Datenherkunft (analysiert aus 5197 Gebäuden, Tile 1166-24):

| Attribut | Häufigste Werte | Nutzen |
|----------|-----------------|--------|
| **HERKUNFT** | `swisstopo` (100%) | Immer swisstopo |
| **HERKUNFT_JAHR** | 2013-2018 | Aktualität prüfen |
| **ORIGINAL_HERKUNFT** | `swisstopo` (99.9%), `Gemeinde` (0.1%) | Ursprüngliche Quelle |
| **GRUND_AENDERUNG** | `Verbessert` (98%), `Real`, `Restrukturiert` | Änderungshistorie |

**Fazit:** HERKUNFT_JAHR ist das relevanteste Metadaten-Attribut für Aktualitätsprüfung

---

# WICHTIGE ERKENNTNIS: 3D-Dachgeometrie

## Aktuelle Situation (Heuristik)

Wir berechnen die Dachneigung aktuell mit einer **Schätzformel** in `roof.py`:

```python
# Formel für Satteldach:
neigung = arctan((firsthoehe - traufhoehe) / (gebaeudetiefe / 2))
```

**Problem:** Das ist eine ANNAHME, kein gemessener Wert!

## Roof_solid Layer hat ECHTE 3D-Punkte!

### Beispiel: Berner Münster (EGID 1230337)

```
Roof_solid 3D-Geometrie:
  Total Punkte: 112
  X-Bereich: 2600951.60 - 2600962.04 (Breite: 10.45m)
  Y-Bereich: 1199554.94 - 1199565.47 (Tiefe: 10.52m)
  Z-Bereich: 546.93 - 552.67 (Höhe: 5.75m)

Z-Levels (distinct):
  Z=547.0m: 27 Punkte (Traufe)
  Z=551.0m: 36 Punkte
  Z=552.0m: 32 Punkte
  Z=553.0m: 17 Punkte (First)
```

### Berechnete Dachneigung aus 3D

| Methode | Dachneigung |
|---------|-------------|
| **Roof_solid 3D-Geometrie** | **30.7°** |
| Heuristik (Schätzung) | ~31° (wenn Tiefe korrekt) |

### Algorithmus für echte Dachneigung

```python
def calculate_roof_angle_from_3d(roof_solid_geometry):
    """Berechnet Dachneigung aus echter 3D-Geometrie."""

    # 1. Alle Z-Werte extrahieren
    z_values = extract_all_z(geometry)

    # 2. Min/Max Z und horizontale Distanz
    z_diff = max(z_values) - min(z_values)

    # 3. Punkte bei Min und Max Z finden
    min_z_points = [p for p in points if p.z < min_z + 0.5]
    max_z_points = [p for p in points if p.z > max_z - 0.5]

    # 4. Zentren berechnen
    min_center = centroid(min_z_points)
    max_center = centroid(max_z_points)

    # 5. Horizontale Distanz
    horiz_dist = distance_2d(min_center, max_center)

    # 6. Echter Winkel
    return math.degrees(math.atan(z_diff / horiz_dist))
```

### Vorteile der 3D-Berechnung

| Aspekt | Heuristik | 3D-Geometrie |
|--------|-----------|--------------|
| Genauigkeit | ±5-10° | ±1° |
| Asymmetrische Dächer | ❌ | ✅ |
| Mehrere Dachflächen | ❌ | ✅ |
| Dachgauben | ❌ | ✅ erkennbar |
| First-Verlauf | Geschätzt | Exakt |

---

# Test-Ergebnisse

## Getestete Adressen

### 1. Bundesplatz 3, Bern (Bundeshaus)

| Attribut | Wert |
|----------|------|
| **EGID** | 2242547 |
| **Koordinaten** | E=2600423, N=1199521 |
| **DACH_MAX** | ~62m (absolut) |
| **DACH_MIN** | ~14.5m (absolut) |
| **GELAENDEPUNKT** | ~543m |
| **First-Trauf** | ~48m (Differenz!) |
| **Komplexität** | COMPLEX |

**Erwartung:**
- OBJEKTART: "Gebaeude oeffentlich" oder ähnlich
- NAME_KOMPLETT: "Bundeshaus" (wenn verfügbar)
- Mehrere Gebäudeteile (Arkaden, Hauptgebäude, Kuppel)

### 2. Rathausgasse 2, Bern (Kirche St. Peter & Paul)

| Attribut | Wert |
|----------|------|
| **EGID** | 191821074 |
| **Koordinaten** | E=2601009, N=1199736 |
| **DACH_MAX** | ~54.6m (absolut) |
| **DACH_MIN** | ~9.3m (absolut) |
| **First-Trauf** | ~45m (Turm!) |
| **Komplexität** | COMPLEX |

**Erwartung:**
- OBJEKTART: "Gebaeude Kirchenbau"
- NAME_KOMPLETT: "Kirche St. Peter und Paul"
- Erkennbare Zonen: Kirchenschiff, Turm

### 3. Knospenweg 4, Bern (Einfamilienhaus)

| Attribut | Wert |
|----------|------|
| **EGID** | 1243790 |
| **Koordinaten** | E=2596299, N=1199805 |
| **DACH_MAX** | ~7.6m (relativ) |
| **DACH_MIN** | ~5.5m (relativ) |
| **First-Trauf** | ~2m |
| **Komplexität** | SIMPLE |

**Erwartung:**
- OBJEKTART: "Gebaeude Einzelhaus"
- NAME_KOMPLETT: null
- Einfache Zone

### 4. Thüringstrasse 1-23, Bern (Reihenhäuser)

| Attribut | Wert |
|----------|------|
| **Adressen** | Mehrere EGIDs |
| **Typ** | Reihenhäuser |
| **Komplexität** | SIMPLE (pro Gebäude) |

**Erwartung:**
- Mehrere Gebäude mit jeweils eigenem EGID
- OBJEKTART: "Gebaeude Einzelhaus" oder "Mehrfamilienhaeuser"
- Zusammenhängende Grundstücke

---

## Layer-Analyse pro Gebäude

### Bundeshaus - Layer-Vergleich

| Layer | Z-Min | Z-Max | Z-Diff | Punkte |
|-------|-------|-------|--------|--------|
| Floor | 543.0 | 543.0 | 0.0 | ~100 |
| Wall | 543.0 | 557.0 | 14.0 | ~400 |
| Roof | 557.0 | 557.0 | 0.0 | ~150 |
| Roof_solid | 557.0 | 605.0 | 48.0 | ~600 |
| Building_solid | 543.0 | 605.0 | 62.0 | ~1000 |

> **TODO:** Echte Werte aus Tile-Analyse einfügen

---

# Geplante Erweiterungen

> **Aktualisiert:** 11.01.2026 - Floor-Layer entfernt (nicht nötig, siehe Analyse oben)

## Layer-Nutzungsstrategie

| Layer | Pre-Import | On-Demand | Begründung |
|-------|------------|-----------|------------|
| **Building_solid** | ✅ Ja | - | Grunddaten (Polygon, Höhen, Attribute) |
| **Roof_solid** | ✅ Ja (Berechnung) | ✅ Ja (Geometrie) | Dachform berechnen / 3D-Visualisierung |
| **Wall** | ❌ Nein | ✅ Ja | 3D-Fassaden für komplexe Gebäude |
| **Floor** | ❌ Nein | ❌ Nein | ≈ Building_solid Polygon (siehe Analyse) |
| **Roof** | ❌ Nein | ❌ Nein | Nur Umriss auf Traufhöhe, wenig Mehrwert |

## 1. DB-Schema Erweiterung (building_3d.db)

**Neue Felder in `buildings` Tabelle:**

```sql
-- Attribute aus Building_solid
ALTER TABLE buildings ADD COLUMN objektart TEXT;
ALTER TABLE buildings ADD COLUMN name_komplett TEXT;
ALTER TABLE buildings ADD COLUMN gebaeude_nutzung TEXT;
ALTER TABLE buildings ADD COLUMN gebaeudeeinheit TEXT;

-- Dach-Attribute (berechnet aus Roof_solid)
ALTER TABLE buildings ADD COLUMN roof_form TEXT;
-- Werte: 'flachdach', 'satteldach', 'pultdach', 'walmdach', 'zeltdach', 'mansarddach', 'komplex'
ALTER TABLE buildings ADD COLUMN roof_form_confidence REAL;
ALTER TABLE buildings ADD COLUMN roof_orientation TEXT;
-- Werte: 'N-S', 'O-W', 'NO-SW', 'NW-SO'

-- Flag für erweiterte 3D-Daten
ALTER TABLE buildings ADD COLUMN has_3d_layers INTEGER DEFAULT 0;
```

## 2. Neue Tabellen für Layer-Geometrien

> **Hinweis:** Floor-Tabelle entfernt - Building_solid Polygon reicht für Grundriss

```sql
-- Wall (Wandflächen) - NUR für komplexe Gebäude (on-demand)
CREATE TABLE building_walls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    egid TEXT NOT NULL,
    gebaeudeeinheit TEXT,
    z_min REAL,  -- GELAENDEPUNKT
    z_max REAL,  -- DACH_MIN
    geometry_wkb BLOB,  -- 3D MultiPolygon als WKB
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (egid) REFERENCES buildings(egid)
);

-- Roof_solid (Dach-Körper)
CREATE TABLE building_roofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    egid TEXT NOT NULL,
    gebaeudeeinheit TEXT,

    -- Höhen
    dach_min REAL,              -- Traufhöhe (m ü.M.)
    dach_max REAL,              -- Firsthöhe (m ü.M.)

    -- Berechnete Werte (aus 3D-Geometrie, im Pre-Import)
    roof_form TEXT,             -- Erkannte Dachform
    roof_angle_deg REAL,        -- Berechnete Neigung
    roof_orientation TEXT,      -- First-Verlauf (N-S, O-W, etc.)
    z_levels TEXT,              -- JSON: Distinct Z-Levels für Analyse
    calculation_method TEXT,    -- 'z_level_analysis', 'estimated'

    -- 3D-Geometrie (NUR für komplexe Gebäude, on-demand)
    geometry_wkb BLOB,          -- 3D MultiPolygon als WKB
    has_full_geometry INTEGER DEFAULT 0,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (egid) REFERENCES buildings(egid)
);

-- Indizes
CREATE INDEX idx_walls_egid ON building_walls(egid);
CREATE INDEX idx_walls_gebaeudeeinheit ON building_walls(gebaeudeeinheit);
CREATE INDEX idx_roofs_egid ON building_roofs(egid);
CREATE INDEX idx_roofs_gebaeudeeinheit ON building_roofs(gebaeudeeinheit);
```

## 3. Import-Strategie

### Pre-Import (Batch, lokal)

```python
# tile_prefetch.py
LAYERS_PRE_IMPORT = [
    'Building_solid',  # Grunddaten + neue Attribute
    'Roof_solid',      # Nur für Dachform-BERECHNUNG (keine Geometrie speichern)
]
```

**Ablauf:**
1. Building_solid parsen → `buildings` Tabelle (inkl. objektart, name_komplett)
2. Roof_solid parsen → Z-Levels extrahieren → Dachform berechnen
3. Berechnete Werte in `building_roofs` speichern (OHNE geometry_wkb)

### On-Demand (Server, pro Projekt)

```python
# layer_fetcher.py
LAYERS_ON_DEMAND = [
    'Wall',           # 3D-Fassaden für komplexe Gebäude
    'Roof_solid',     # Vollständige 3D-Geometrie
]
```

**Ablauf:**
1. Tile temporär downloaden
2. Nur Features mit passender GEBAEUDEEINHEIT parsen
3. Geometrie in DB speichern
4. Tile LÖSCHEN (Speicher sparen)

## 4. Nutzen für die Anwendung

| Feature | Datenquelle | Import-Typ | Nutzen |
|---------|-------------|------------|--------|
| **Komplexitäts-Erkennung** | OBJEKTART | Pre-Import | Automatische SIMPLE/COMPLEX Unterscheidung |
| **Gebäudename** | NAME_KOMPLETT | Pre-Import | Direkt anzeigen ohne Claude-Recherche |
| **Dachform** | Roof_solid (berechnet) | Pre-Import | Satteldach, Walmdach, etc. für ALLE Gebäude |
| **Dachneigung** | Roof_solid (berechnet) | Pre-Import | Exakter Winkel statt Schätzung |
| **3D-Fassaden** | Wall | On-Demand | Echte 3D-Geometrie für komplexe Gebäude |
| **3D-Dach** | Roof_solid (Geometrie) | On-Demand | Vollständiges 3D-Modell im Viewer |

---

# Offene Fragen

1. ~~**Speicherbedarf:** Wie gross werden die neuen Tabellen?~~ → Siehe LAYER_MIGRATION_PLAN.md
2. ~~**Performance:** Lohnt sich die Speicherung aller Layer oder on-demand?~~ → Hybrid-Ansatz gewählt
3. **OBJEKTART Qualität:** Wie zuverlässig sind die Werte im Kanton Bern? (Stichproben zeigen gute Qualität)
4. **3D-Viewer:** Können wir die Layer direkt rendern? (Three.js mit WKB/GeoJSON)
5. ~~**Floor-Layer:** Brauchen wir ihn?~~ → NEIN, Building_solid reicht (Analyse 11.01.2026)

---

# Nächste Schritte

1. [x] ~~Tile für Bundeshaus laden und Layer analysieren~~ (erledigt)
2. [x] ~~OBJEKTART-Werte dokumentieren~~ (15 Typen gefunden)
3. [x] ~~Floor-Layer Notwendigkeit analysieren~~ (nicht nötig)
4. [ ] DB-Schema Migration erstellen
5. [ ] tile_prefetch.py erweitern (Roof_solid Parsing)
6. [ ] Dachform-Erkennung implementieren
7. [ ] On-Demand Layer-Fetch für komplexe Gebäude
8. [ ] Test mit Pilotgebäuden (Bundeshaus, Münster)