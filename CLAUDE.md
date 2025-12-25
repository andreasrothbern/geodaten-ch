# CLAUDE.md - Projekt-Kontext für Claude Code

## Projekt: Geodaten Schweiz

Dieses Projekt bietet eine API und Web-App für Schweizer Geodaten (Gebäude, Adressen, Grundstücke).

## Architektur

```
geodaten-ch/
├── backend/          # FastAPI + Python 3.11
│   └── app/
│       ├── main.py           # API Endpunkte
│       ├── models/schemas.py # Pydantic Models
│       ├── data/             # SQLite Datenbanken
│       │   └── building_heights.db  # swissBUILDINGS3D Höhen
│       └── services/
│           ├── swisstopo.py  # swisstopo API Adapter
│           ├── geodienste.py # geodienste.ch WFS (Gebäudegeometrie)
│           ├── height_db.py  # Höhendatenbank Service
│           └── cache.py      # SQLite Cache
│   └── scripts/
│       └── import_building_heights.py  # swissBUILDINGS3D Import
│
├── frontend/         # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── SearchForm.tsx
│           ├── BuildingCard.tsx
│           ├── ScaffoldingCard.tsx  # Gerüstbau-Daten
│           └── ApiStatus.tsx
│
└── Deployed on Railway.app
```

## API-Testergebnisse (20.12.2025)

### swisstopo (api3.geo.admin.ch) - EMPFOHLEN ✅
- **Erfolgsrate: 100%** (8/8 Tests)
- **Ø Antwortzeit: 222ms**
- Score: 93.3/100

Funktionierende Endpunkte:
- Adresssuche: 43-48ms
- Feature Search (GWR): 46ms
- Find by EGID: 28ms
- Identify: 89ms

### GWR (madd.bfs.admin.ch)
- Erfolgsrate: 44% (4/9 Tests)
- MADD XML funktioniert
- Address-to-EGID problematisch

### geodienste.ch
- Erfolgsrate: 50% (4/8 Tests)
- WMS funktioniert
- WFS hat Probleme (Status 400)

## Wichtige API-Endpunkte (swisstopo)

```python
# Adresssuche
GET https://api3.geo.admin.ch/rest/services/api/SearchServer
    ?searchText=Bundesplatz 3, Bern
    &type=locations
    &origins=address

# Gebäude per EGID
GET https://api3.geo.admin.ch/rest/services/api/MapServer/find
    ?layer=ch.bfs.gebaeude_wohnungs_register
    &searchText=190365
    &searchField=egid

# Identify an Koordinate
GET https://api3.geo.admin.ch/rest/services/api/MapServer/identify
    ?geometryType=esriGeometryPoint
    &geometry=2600000,1199000
    &layers=all:ch.bfs.gebaeude_wohnungs_register
```

## GWR-Daten (verfügbare Felder)

- `egid` - Eidg. Gebäudeidentifikator
- `strname`, `deinr` - Strasse, Hausnummer
- `dplz4`, `ggdename` - PLZ, Ort
- `gdekt` - Kanton
- `gbauj` - Baujahr
- `gkat` - Gebäudekategorie (1020=EFH, 1030=MFH)
- `gastw` - Anzahl Geschosse
- `ganzwhg` - Anzahl Wohnungen
- `garea` - Gebäudefläche m²
- `gwaerzh1` - Heizungsart
- `genh1` - Energieträger Heizung

## Gerüstbau-Features

### API-Endpunkte

```python
# Gerüstbau-Daten per Adresse
GET /api/v1/scaffolding?address=Bundesplatz 3, 3011 Bern

# Gerüstbau-Daten per EGID
GET /api/v1/scaffolding/by-egid/2242547

# Höhendatenbank-Statistiken
GET /api/v1/heights/stats
```

## Building Context System (NEU)

Ermöglicht die Analyse komplexer Gebäude mit mehreren Höhenzonen.

### API-Endpunkte

```python
# Kontext abrufen (mit optionaler Auto-Erstellung)
GET /api/v1/building/context/{egid}?create_if_missing=true&analyze_if_complex=true

# Claude-Analyse für komplexes Gebäude triggern
POST /api/v1/building/context/{egid}/analyze
Body: {"include_orthofoto": false, "force_reanalyze": false}

# Kontext manuell aktualisieren
PUT /api/v1/building/context/{egid}
Body: {"zones": [...], "validated": true}

# Kontext löschen (Reset)
DELETE /api/v1/building/context/{egid}
```

### Zonen-Typen

| Typ | Beschreibung | Beispiel |
|-----|--------------|----------|
| `hauptgebaeude` | Hauptbaukörper | Wohnhaus, Bürogebäude |
| `anbau` | Seitenflügel, Erweiterungen | Westflügel, Neubau |
| `turm` | Türme, Treppenhäuser | Kirchturm, Treppenturm |
| `kuppel` | Kuppeln | Bundeshaus-Kuppel |
| `arkade` | Arkaden, Laubengänge | Bundeshaus-Arkaden |
| `vordach` | Vordächer, Überdachungen | Eingangsbereich |
| `treppenhaus` | Aussenliegende Treppenhäuser | Fluchttreppe |
| `garage` | Garagen, Carports | Tiefgaragen-Aufbau |

### Komplexitäts-Erkennung

Das System erkennt automatisch die Gebäudekomplexität:

```python
# Einfach (auto-context, 1 Zone)
- Polygon ≤6 Ecken
- Fläche <300m²
- Konvexe Form
- Kategorie: Wohnen

# Komplex (Claude-Analyse, mehrere Zonen)
- Polygon >12 Ecken
- Fläche >1000m²
- Konkave Form (Einbuchtungen)
- Kategorie: Öffentlich, Kirche, Industrie
```

### Datenbankstruktur

```sql
-- building_contexts.db
CREATE TABLE building_contexts (
    egid TEXT PRIMARY KEY,
    context_json TEXT,           -- BuildingContext als JSON
    source TEXT,                 -- 'auto', 'claude', 'manual'
    confidence REAL,
    validated INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
```

### Kosten (Claude API)
- Pro Analyse: ~$0.01-0.02
- Mit Orthofoto: ~$0.05-0.10
- Caching: Einmal analysiert = gespeichert

### Datenquellen für Höhen (Fallback-Kette)

```
┌─────────────────────────────────────────────────────────────┐
│                    LOOKUP STRATEGIE                         │
├─────────────────────────────────────────────────────────────┤
│  1. Manuell eingegeben (Trauf-/Firsthöhe)                   │
│     ↓ falls nicht gesetzt                                   │
│  2. EGID-Lookup (building_heights_detailed)                 │
│     → Trauf-/Firsthöhe aus swissBUILDINGS3D per EGID       │
│     ↓ falls nicht gefunden                                  │
│  3. EGID-Legacy (building_heights)                          │
│     → Gesamthöhe aus swissBUILDINGS3D per EGID             │
│     ↓ falls nicht gefunden                                  │
│  4. Koordinaten-Lookup (building_heights_by_coord)          │
│     → Höhe per LV95-Koordinaten (±25m Toleranz)            │
│     → Für Gebäude ohne EGID in swissBUILDINGS3D            │
│     ↓ falls nicht gefunden                                  │
│  5. Geschätzt aus GWR-Daten                                 │
│     → Geschosse × Geschosshöhe + Dachhöhe                  │
│     ↓ falls keine Geschossdaten                             │
│  6. Standard nach Kategorie                                 │
│     → EFH: 8m, MFH: 12m, etc.                              │
└─────────────────────────────────────────────────────────────┘
```

**Wichtig:** Koordinaten-Lookup (Stufe 4) wurde hinzugefügt, weil swissBUILDINGS3D nicht bei allen Gebäuden eine EGID enthält.

### swissBUILDINGS3D Import

```bash
# Daten von swisstopo herunterladen:
# https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta

# Import ausführen
cd backend
python scripts/import_building_heights.py daten.gml --canton BE
```

## Douglas-Peucker Polygon-Vereinfachung

Die App verwendet den Douglas-Peucker Algorithmus zur Reduktion der Fassadensegmente.
Implementiert in `backend/app/services/geodienste.py`.

### Aktuelle Parameter

```python
# In geodienste.py (GeodiensteService Klasse)
SIMPLIFY_EPSILON = 0.3          # Meter - Toleranz für Punktreduktion
COLLINEAR_ANGLE_TOLERANCE = 8.0  # Grad - für kollineare Segmente
MIN_SIDE_LENGTH = 1.0            # Meter - minimale Seitenlänge
```

### Empfehlungen nach Gebäudegrösse

| Gebäudetyp | EPSILON | ANGLE_TOL | Bemerkung |
|------------|---------|-----------|-----------|
| EFH (10×12m) | 0.3–0.5 | 5–8° | Wenig Vereinfachung nötig |
| MFH/Gewerbe | 0.5–1.0 | 8–10° | Standard |
| Grossprojekt (>50m) | 1.0–2.0 | 8–12° | Starke Vereinfachung |

### Algorithmus-Ablauf

1. **Douglas-Peucker**: Finde Punkt mit max. Abstand zur Verbindungslinie. Wenn > EPSILON → rekursiv teilen
2. **Kollineare Punkte entfernen**: Punkte mit Winkel ≈ 180° (Toleranz ANGLE_TOL) werden entfernt
3. **Kurze Segmente zusammenfassen**: Segmente < MIN_SIDE_LENGTH werden vereint

## NPK 114 Konstanten

Ausmass-Berechnung gemäss NPK 114 D/2012. Implementiert in `backend/app/services/npk114_calculator.py`.

```python
# Zuschläge
FASSADENABSTAND_LF = 0.30        # m - Abstand Gebäude zu Gerüst
GERUESTGANGBREITE_LG = 0.70      # m - für W09
STIRNSEITIGER_ABSCHLUSS_LS = 1.00 # m - beidseitig (= LF + LG)
HOEHENZUSCHLAG = 1.00            # m - über Arbeitshöhe

# Mindestmasse
MIN_AUSMASSLAENGE = 2.5          # m
MIN_AUSMASSHOEHE = 4.0           # m

# Formeln
# LA = LS + L + LS (beidseitiger Abschluss)
# HA = H + Höhenzuschlag
# A = LA × HA
# Giebel: H_mittel = H_Traufe + (H_Giebel × 0.5)
```

## Layher Blitz 70 System

Material-Schätzung implementiert in `backend/app/services/layher_catalog.py`.

### Feldlängen (m)
`3.07, 2.57, 2.07, 1.57, 1.09, 0.73`

### Rahmenhöhen (m)
`2.00, 1.50, 1.00, 0.50`

### Richtwerte
| Parameter | Wert |
|-----------|------|
| Gewicht | 18–22 kg/m² Gerüstfläche |
| Lastklasse | 3 (200 kg/m²) |
| Breitenklasse | W09 (0.90 m) |
| Verankerung | alle 4 m horizontal, alle 4 m vertikal |

### Feldlängen-Verhältnis (Slider in UI)

Der Slider steuert das Verhältnis zwischen 2.57m und 3.07m Feldern:
- **0%**: Nur 2.57m Felder (mehr Flexibilität, mehr Teile)
- **100%**: Nur 3.07m Felder (weniger Teile, weniger Flexibilität)
- **Standard: 50%**: Ausgewogenes Verhältnis

## Höhenzonen bei komplexen Gebäuden

⚠️ **Problem**: SwissBuildings3D liefert oft nur einen globalen Höhenwert, der nicht repräsentativ ist.

**Beispiel Bundeshaus Bern:**
- SwissBuildings3D Traufhöhe: 14.5m → Dies ist der Arkaden-Wert!
- Tatsächliche Parlamentsfassade: 22–25m Traufe

### Empfohlene Strategie

1. **Z-Koordinaten der Polygonpunkte nutzen** (falls verfügbar)
2. **Lokale Höhen pro Fassade** statt globaler Höhe
3. **Fallback-Werte nach Gebäudeteil**:

| Gebäudeteil | Traufhöhe | Gerüsthöhe |
|-------------|-----------|------------|
| Standard (West/Ost) | 18.0 m | 19.0 m |
| Hauptfassaden | 25.0 m | 26.0 m |
| Türme | – | 36.0 m |
| Kuppeln | – | Spezialgerüst |

## SVG-Visualisierung: Aktuell vs. Ziel

**Referenz:** `lawil/claude_ai_bundeshaus/` - Von Claude.ai handgefertigte SVGs für Bundeshaus

### Vergleichstabelle (Stand 25.12.2025)

| Feature | App (aktuell) | Claude.ai Ziel | Status |
|---------|---------------|----------------|--------|
| **Gebäudegeometrie** | 1 Polygon aus geodienste.ch | Mehrere Polygone pro Gebäudeteil | ⚠️ Zonen erkannt |
| **Höhendaten** | Mehrere Zonen (Claude-Analyse) | Höhenzonen pro Gebäudeteil | ✅ |
| **Höhe pro Fassade** | ✅ Implementiert (traufhoehe_m) | Individuelle Höhen | ✅ |
| **Semantische Elemente** | Arkade, Hauptfassade, Kuppel | Kuppel, Türme, Arkaden, Ehrenhof | ✅ Basis |
| **Gerüstzonen** | Farbcodiert im Grundriss | Separate Zonen pro Fassade/Höhe | ✅ |
| **Ständerpositionen** | Rote Punkte alle 2.57m | Punkte alle 2.5-3m (Feldlänge) | ✅ |
| **Verankerungen** | Ecken + alle 4m dazwischen | Entlang Fassade alle 4m h/v | ✅ |
| **Zugänge (Z1-Zn)** | Gelbe Rechtecke (SUVA-konform) | Gelbe Markierungen | ✅ |
| **Masslinien** | Nur Umfang/Fläche | Mit Pfeilen, Beschriftung | ⚠️ |
| **Lagenbeschriftung** | Nur in Schnitt | In Ansicht nummeriert | ⚠️ |
| **Gebäudebeschriftung** | Zonen-Namen im Grundriss | Zonen-Namen (BH West, etc.) | ✅ |
| **Dachform (Ansicht)** | Einfaches Dreieck/Rechteck | Giebel, Kuppel, Laterne | ❌ |
| **Material-Details** | Keine | Säulen, Beläge, Kupfer-Gradient | ❌ |
| **Titelblock** | Professional mode | Vollständig | ✅ |
| **Fusszeile** | Professional mode | Vollständig | ✅ |
| **Legende** | Einfach | Detailliert mit allen Elementen | ⚠️ |
| **Nordpfeil** | ✅ Vorhanden | ✅ | ✅ |
| **Massstab** | ✅ Vorhanden | ✅ | ✅ |
| **Schraffur-Pattern** | Professional mode | Gebäude schraffiert | ✅ |

### Was fehlt für professionelle Grafik (Claude.ai Niveau)

**Implementiert ✅:**
1. ~~Höhenzonen-Erkennung~~ → Claude-Analyse bei Höhendifferenz >15m
2. ~~Gebäudeteil-Klassifikation~~ → Arkade, Hauptfassade, Kuppel
3. ~~Ständer-Berechnung~~ → Alle 2.57m (Layher Blitz 70)
4. ~~Verankerungs-Raster~~ → Ecken + alle 4m
5. ~~Ständer-Punkte~~ → Rote Punkte im SVG
6. ~~Zugangs-Markierungen~~ → Gelbe Rechtecke (Z1, Z2, etc.)

**Noch offen ❌:**
1. **Innenhöfe/Ehrenhof** als Ausschnitt im Polygon markieren
2. **Masslinien mit Pfeilen** statt nur Text-Labels
3. **Separate Gebäudepolygone** bei U/L-Form (aktuell: 1 Polygon mit Zonen)
4. **Ansicht-SVG**: Kuppel, Giebel, Säulen-Details
5. **Detaillierte Legende** mit allen Symbolen

### Dateien zum Vergleich

```
lawil/
├── claude_ai_bundeshaus/           # Handgefertigte Referenz-SVGs
│   ├── anhang_a_grundriss.svg      # Grundriss mit Höhenzonen
│   ├── anhang_b_ansicht.svg        # Ansicht mit Kuppel, Säulen
│   ├── anhang_c_schnitt.svg        # Schnitt durch Parlament
│   ├── anhang_d_gerustkarte.svg    # Feldaufteilung
│   └── PROJEKT_KONTEXT.md          # Projektdokumentation
│
└── geodaten-ch/                    # App-generierte SVGs
    └── backend/app/services/
        └── svg_generator.py        # Automatische Generierung
```

---

## ⚠️ KRITISCHE ANALYSE: SVG-Qualität (Stand 25.12.2025)

### Das Problem

Die automatisch generierten SVGs erreichen **NICHT** die Qualität der Claude.ai Referenz-SVGs.
Trotz umfangreicher Datensammlung (Polygon, Höhen, Zonen, GWR) ist das Ergebnis "schematisch" statt "architektonisch".

### Was wir haben (Daten)

| Datenquelle | Was wir bekommen | Qualität |
|-------------|------------------|----------|
| geodienste.ch | Polygon mit 26-175 Punkten | ✅ Gut |
| swissBUILDINGS3D | Trauf-/First-/Gebäudehöhe | ✅ Gut |
| GWR (swisstopo) | Geschosse, Kategorie, Baujahr | ✅ Gut |
| Claude API | Zonen-Analyse (Arkade, Hauptgebäude, Kuppel) | ✅ Gut |

**Fazit Daten:** Wir haben alle nötigen Informationen.

### Was wir produzieren (SVG)

| Element | Unsere Implementierung | Claude.ai Referenz |
|---------|------------------------|-------------------|
| Arkaden | Rechteck + 1 Bogen | Säulenreihe mit Bögen, Schatten |
| Kuppel | Ellipse (oval) | Detaillierte Kuppelform mit Laterne |
| Fenster | Kleine Rechtecke (Raster) | Architektonisch korrekte Anordnung |
| Proportionen | Berechnet aus Zonen-Breite | Visuell ausbalanciert |
| Gerüst | Linien + Rechtecke | Detaillierte Ständer, Riegel, Beläge |
| Gesamteindruck | **Technisches Diagramm** | **Architekturzeichnung** |

### Warum der Unterschied?

#### 1. Regelbasiert vs. Kontextverständnis

**Unser Code:**
```python
if zone_type == 'arkade':
    # Zeichne Rechteck + Bögen
    svg += f'<rect x="{x}" y="{y}" ...>'
    for i in range(num_arches):
        svg += f'<path d="M ... Q ..." />'  # Bogen
```

**Claude.ai (interaktiv):**
- Versteht "Bundeshaus" als historisches Parlamentsgebäude
- Weiss wie Arkaden in der Schweizer Neorenaissance aussehen
- Passt Proportionen visuell an
- Iteriert basierend auf Feedback

#### 2. One-Shot vs. Iterativ

| Ansatz | Prozess | Ergebnis |
|--------|---------|----------|
| **Claude API** | 1 Prompt → 1 Antwort | "Gut genug" beim ersten Versuch |
| **Claude.ai Chat** | Prompt → Feedback → Anpassung → Feedback → ... | Verfeinert bis perfekt |

#### 3. SVG-Generierung ist schwer

Selbst wenn wir Claude API bitten "generiere SVG wie Referenz":
- Claude hat keinen visuellen Feedback-Loop
- Kann das Ergebnis nicht "sehen"
- Muss alles in einem Durchgang richtig machen

### Mögliche Lösungsansätze

#### Option A: Akzeptieren (Status Quo)
- Schematische SVGs für Funktionalität (Gerüstplanung)
- Für Präsentationen: Manuell mit Claude.ai erstellen
- **Aufwand:** Keiner
- **Qualität:** ⭐⭐ (funktional, nicht schön)

#### Option B: Template-basiert
- Vorgefertigte SVG-Templates für Gebäudetypen (EFH, MFH, Kirche, etc.)
- Parameter einsetzen (Höhe, Breite, Zonen)
- **Aufwand:** Hoch (viele Templates nötig)
- **Qualität:** ⭐⭐⭐ (besser, aber starr)

#### Option C: Multi-Step Claude API
1. Claude generiert SVG
2. Wir rendern es (headless browser)
3. Screenshot zurück an Claude: "Verbessere das"
4. Iteration bis gut
- **Aufwand:** Sehr hoch (Infrastruktur, Kosten)
- **Qualität:** ⭐⭐⭐⭐ (potenziell gut)

#### Option D: Hybrid-Workflow
- App sammelt alle Daten + generiert JSON-Export
- User öffnet Claude.ai manuell
- Kopiert JSON rein: "Erstelle SVG für dieses Gebäude"
- Claude.ai generiert hochwertige SVG
- **Aufwand:** Mittel (Export-Funktion)
- **Qualität:** ⭐⭐⭐⭐⭐ (wie Referenz)

### Empfehlung

**Für PoC:** Option A (Status Quo)
- Die schematischen SVGs zeigen, dass die Daten korrekt sind
- Die Zonen-Erkennung funktioniert
- Für Gerüstplanung reicht die Qualität

**Für Produktion:** Option D (Hybrid)
- Export-Button: "Daten für Claude.ai exportieren"
- Generiert strukturierten Prompt mit allen Daten
- User kann in Claude.ai hochwertige SVGs erstellen

### Verfügbare Daten für Claude.ai Prompt

Wenn wir Option D implementieren, hätten wir:

```json
{
  "gebaeude": {
    "adresse": "Bundesplatz 3, 3011 Bern",
    "egid": 1017961,
    "polygon": [[2600450.2, 1199800.5], ...],  // 26 Punkte
    "umfang_m": 285.4,
    "flaeche_m2": 4200
  },
  "hoehen": {
    "traufhoehe_m": 14.53,
    "firsthoehe_m": 62.57,
    "geschosse": 4
  },
  "zonen": [
    {"name": "Arkaden/Erdgeschoss", "typ": "arkade", "hoehe_m": 14.5},
    {"name": "Hauptgebäude", "typ": "hauptgebaeude", "hoehe_m": 28.0},
    {"name": "Kuppel/Turm", "typ": "kuppel", "hoehe_m": 30.0, "spezialgeruest": true}
  ],
  "geruest": {
    "system": "Layher Blitz 70",
    "breitenklasse": "W09",
    "feldlaengen_m": [3.07, 2.57, 2.07, 1.57],
    "gesamtflaeche_m2": 1850
  }
}
```

Dies ist **deutlich mehr Information** als Claude.ai ursprünglich hatte, als die Referenz-SVGs erstellt wurden.

## Neue Features (Stand 24.12.2025)

### URL-Parameter für Adresse

Die App kann mit vorausgefüllter Adresse aufgerufen werden:
```
https://[app-url]/?address=Bundesplatz%203,%203011%20Bern
```

### Compact-Modus für Grundriss-SVG

Im Gerüstbau-Tab wird das SVG im Compact-Modus gerendert:
- Keine "Gebäudedaten"-Box
- Kleinere Margins → mehr Platz für Polygon
- Kompaktere Fassaden-Labels

## Deployment

**Plattform:** Railway.app
- Backend: FastAPI Container (acceptable-trust-production.up.railway.app)
- Frontend: Nginx mit Vite Build (cooperative-commitment-production.up.railway.app)

### Railway Volume (WICHTIG für Datenpersistenz)

Ein Railway Volume ist konfiguriert unter `/app/data` für persistente SQLite-Datenbanken.
Ohne Volume gehen on-demand importierte Höhendaten bei jedem Deployment verloren!

**Volume einrichten (falls nicht vorhanden):**
```bash
npx @railway/cli login
cd backend
npx @railway/cli link
npx @railway/cli volume add --mount-path /app/data
```

**Datenpersistenz-Übersicht:**

| Daten | Speicherung | Bei Deployment |
|-------|-------------|----------------|
| GWR-Daten (EGID, Geschosse) | Live von swisstopo API | Kein Problem - wird neu abgefragt |
| Gebäudegeometrie (Polygon) | Live von geodienste.ch | Kein Problem - wird neu abgefragt |
| **Gemessene Höhen** | SQLite in Volume | ✅ Bleibt erhalten (mit Volume) |
| Layher-Katalog | SQLite in Volume | ✅ Bleibt erhalten |

## Status (Stand: 25.12.2025)

### Fertig ✅
- [x] Backend + Frontend Deployment
- [x] swissBUILDINGS3D On-Demand Import via STAC API
- [x] Railway Volume für persistente Daten
- [x] SVG-Visualisierungen (Schnitt, Ansicht, Grundriss)
- [x] Fassaden-Auswahl mit interaktivem Grundriss
- [x] NPK 114 Ausmass-Berechnung
- [x] Material-Schätzung (Layher Blitz 70)
- [x] Koordinaten-basierter Höhen-Lookup (für Gebäude ohne EGID)
- [x] Douglas-Peucker Polygon-Vereinfachung
- [x] URL-Parameter für Adresse (?address=...)
- [x] Compact-Modus für Grundriss-SVG
- [x] **Building Context System** (POC - poc_bundeshaus_mvp Branch)
  - Pydantic Models (BuildingZone, BuildingContext)
  - SQLite Speicherung (building_contexts.db)
  - Komplexitäts-Erkennung (simple/moderate/complex)
  - Auto-Context für einfache Gebäude
  - Claude API Integration für komplexe Gebäude
  - API Endpoints (GET/POST/PUT/DELETE)
  - Frontend TypeScript Types
  - **Mehrzonenerkennung** bei extremer Höhendifferenz (>15m)
  - **Frontend Zonen-Editor** mit Bearbeitung
- [x] **Gerüstbau-SVG Features** (poc_bundeshaus_mvp Branch)
  - Ständerpositionen (alle 2.57m, Layher Blitz 70)
  - Verankerungen (Ecken + alle 4m)
  - Zugänge (Z1-Zn) nach SUVA-Vorschriften (max 50m)
  - Zonen-Farbcodierung im Grundriss
  - Professional-Mode mit Schraffur

### In Arbeit 🔨
- [ ] SVG-Visualisierung: Qualität wie Claude.ai Referenz-SVGs
  - Separate Gebäudeteile statt 1 Polygon
  - Ehrenhof/Innenhöfe markieren
  - Masslinien mit Pfeilen
  - Detaillierte Legende

### Geplant 🔜
- [ ] swissALTI3D (Terrain) Integration
- [ ] DXF-Export
- [ ] Custom Domain
- [ ] Tests: Zonen-Erkennung (L/U-Form, Anbauten)

## ACHTUNG: Technische Schulden

### Höhendatenbank - Drei Tabellen

Es gibt **drei** SQLite-Tabellen für Höhendaten in `building_heights.db`:

1. **`building_heights`** (Legacy, EGID-basiert)
   - Felder: `egid`, `height_m`, `height_type`, `source`
   - Einfache Struktur, nur eine Höhe pro Gebäude
   - **Status:** Wird noch unterstützt als Fallback

2. **`building_heights_detailed`** (EGID-basiert)
   - Felder: `egid`, `traufhoehe_m`, `firsthoehe_m`, `gebaeudehoehe_m`, `dach_max_m`, `dach_min_m`, `terrain_m`, `source`
   - Detaillierte Struktur für Gerüstbau
   - **Status:** Primäre Tabelle für EGID-Lookups

3. **`building_heights_by_coord`** (Koordinaten-basiert, NEU)
   - Felder: `lv95_e`, `lv95_n`, `uuid`, `traufhoehe_m`, `firsthoehe_m`, `gebaeudehoehe_m`, ...
   - Für Gebäude ohne EGID in swissBUILDINGS3D
   - **Status:** Fallback wenn EGID-Lookup fehlschlägt

**Lookup-Reihenfolge in `geodienste.py`:**
1. `building_heights_detailed` (per EGID)
2. `building_heights` (per EGID, Legacy)
3. `building_heights_by_coord` (per Koordinaten ±25m)

**TODO (optional):** Legacy-Tabelle `building_heights` kann entfernt werden, sobald alle Daten in `_detailed` migriert sind.

### Debug-Code (Stand 23.12.2025)

Debug-Code aus Backend entfernt:
- ✅ `_height_debug` aus API Response entfernt (`geodienste.py`)
- ✅ Debug-Prints aus `height_fetcher.py` entfernt
- `[DEBUG]` Console-Logs im Frontend (`App.tsx`) können optional entfernt werden

### 3D-Viewer-URL Format (Stand 23.12.2025)

**Entscheidung:** LV95-Format mit `sr=2056` verwenden.

```
https://map.geo.admin.ch/#/map?lang=de&sr=2056&center={E},{N}&z=13&bgLayer=ch.swisstopo.pixelkarte-farbe&3d
```

**Getestete Alternativen (funktionieren NICHT zuverlässig):**

| Format | Problem |
|--------|---------|
| `camera=lon,lat,height,pitch` | Ungültiges Format laut map.geo.admin.ch |
| `center=...&z=20&3d=true` | z=20 ungültig (max z=13), `3d=true` statt `3d` |
| `camera=lon,lat,elevation,pitch,,&3d` | Browser-abhängige Probleme, Koordinaten werden verfälscht |

**Warum LV95 (`sr=2056`):**
- Zuverlässig in allen Browsern (getestet normal + Inkognito)
- Offizielle Schweizer Koordinaten (EPSG:2056)
- Zoom z=13 ist Maximum laut docs.geo.admin.ch
- `&3d` aktiviert 3D-Modus (nicht `&3d=true`)

**Nachteil:** Keine Kontrolle über Kamera-Winkel (immer Draufsicht). Das `camera`-Format würde schräge Ansichten erlauben, funktioniert aber nicht zuverlässig.

## Lokale Entwicklung

```bash
# Backend (Terminal 1)
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
