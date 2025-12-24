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

### Vergleichstabelle

| Feature | App (aktuell) | Claude.ai Ziel | Status |
|---------|---------------|----------------|--------|
| **Gebäudegeometrie** | 1 Polygon aus geodienste.ch | Mehrere Polygone pro Gebäudeteil | ❌ |
| **Höhendaten** | 1 globale Höhe (SwissBuildings3D) | Höhenzonen pro Gebäudeteil | ❌ |
| **Höhe pro Fassade** | ✅ Implementiert (traufhoehe_m) | Individuelle Höhen | ✅ Basis |
| **Semantische Elemente** | Keine | Kuppel, Türme, Arkaden, Ehrenhof | ❌ |
| **Gerüstzonen** | Rechteck um ganzes Polygon | Separate Zonen pro Fassade/Höhe | ❌ |
| **Ständerpositionen** | Keine | Punkte alle 2.5-3m (Feldlänge) | ❌ |
| **Verankerungen** | Nur an Polygon-Ecken | Entlang Fassade alle 4m h/v | ⚠️ Teilweise |
| **Zugänge (Z1-Z4)** | Keine | Gelbe Markierungen | ❌ |
| **Masslinien** | Nur Umfang/Fläche | Mit Pfeilen, Beschriftung | ⚠️ Einfach |
| **Lagenbeschriftung** | Nur in Schnitt | In Ansicht nummeriert | ⚠️ Teilweise |
| **Gebäudebeschriftung** | Nur Adresse | Zonen-Namen (BH West, etc.) | ❌ |
| **Dachform (Ansicht)** | Einfaches Dreieck/Rechteck | Giebel, Kuppel, Laterne | ❌ |
| **Material-Details** | Keine | Säulen, Beläge, Kupfer-Gradient | ❌ |
| **Titelblock** | Optional (professional mode) | Vollständig | ✅ Vorhanden |
| **Fusszeile** | Optional (professional mode) | Vollständig | ✅ Vorhanden |
| **Legende** | Einfach | Detailliert mit allen Elementen | ⚠️ Einfach |
| **Nordpfeil** | ✅ Vorhanden | ✅ | ✅ |
| **Massstab** | ✅ Vorhanden | ✅ | ✅ |

### Was fehlt für professionelle Grafik

**Daten-Ebene (Backend):**
1. **Höhenzonen-Erkennung**: Welche Fassaden bilden eine Zone?
2. **Gebäudeteil-Klassifikation**: Hauptbau, Seitenflügel, Turm, Kuppel
3. **Ständer-Berechnung**: Position alle 2.5-3m basierend auf Feldlängen
4. **Verankerungs-Raster**: Alle 4m horizontal und vertikal

**Grafik-Ebene (SVG Generator):**
1. **Mehrere Gerüstzonen** statt einer Bounding Box
2. **Ständer-Punkte** entlang der Gerüstkante
3. **Verankerungs-Linien** von Fassade nach aussen
4. **Zugangs-Markierungen** (gelbe Rechtecke)
5. **Detaillierte Ansicht**: Ständer, Riegel, Beläge als separate Linien

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

## Status (Stand: 24.12.2025)

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
- [ ] Gerüstkonfiguration → Berechnung (Arbeitstyp, Gerüstart, Breitenklasse)
- [ ] Lokale Höhen pro Fassade (Höhenzonen)
- [ ] Custom Domain

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
